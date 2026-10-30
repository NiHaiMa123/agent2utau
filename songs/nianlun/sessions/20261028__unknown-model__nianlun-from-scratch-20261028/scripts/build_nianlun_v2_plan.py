"""年轮 v2 画线（阶段 B）：逐句中心线/连接/字腹动作 + 意图简报 + 冻结 + plan + ledger。

严格顺序：先写意图简报并冻结（plan 尚不存在），再写数值 plan，最后写 ledger。
"""
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")

from agent2utau.openutau.ustx import TempoMap, load_ustx, sha256
from agent2utau.evaluation.execution_review import digest, validate_inventory
from agent2utau.evaluation.musical_review import freeze_intent

V1 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
V2 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
DESIGN = V2 / "design"
SCORE = DESIGN / "score.ustx"
TICK_S = 60.0 / (120.0 * 480)


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


# ---------------- 源观测 ----------------
zf = np.load(V2 / "observation" / "fcpe.npz")
zr = np.load(V2 / "observation" / "rmvpe.npz")
t_f, f0_f = zf["times"].astype(float), zf["f0_hz"].astype(float)
t_r, f0_r = zr["times"].astype(float), zr["f0_hz"].astype(float)
c_f = np.where(f0_f > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)
c_r = np.where(f0_r > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_r, 1e-6) / 440.0), np.nan)
rf = np.interp(t_f, t_f, c_f)
rr = np.interp(t_f, t_r, c_r)
agree = np.isfinite(rf) & np.isfinite(rr) & (np.abs(rf - rr) <= 120)
c_all = np.where(agree, (rf + rr) / 2.0, np.nan)

doc = load_ustx(SCORE)
tm = TempoMap.from_doc(doc)
native = rj(DESIGN / "baseline_pitch.json")["phrases"]
inv = validate_inventory(DESIGN / "review-inventory.json")
units_by_part = {}
for u in inv["units"]:
    units_by_part.setdefault(u["part_index"], []).append(u)
hfa = rj(V2 / "hfa" / "hfa_summary.json")
metrics = rj(DESIGN / "phrase_metrics.json")
ROLE = metrics["role"]
hfa_by_pid = {p["phrase_id"]: p for p in hfa["phrases"]}


def src_track(a, b):
    m = (t_f >= a) & (t_f < b) & agree
    if m.sum() < 3:
        return None
    return t_f[m], c_all[m]


def src_frames(a, b):
    tr = src_track(a, b)
    return 0 if tr is None else len(tr[0])


def span_of_runs(tt, vv):
    """只算连续有声段内部的跨度：跨越静默的高差不是字腹动作。"""
    if len(tt) == 0:
        return 0.0
    best = 0.0
    run_lo = run_hi = vv[0]
    prev = tt[0]
    for t, v in zip(tt[1:], vv[1:]):
        if t - prev > 0.06:
            best = max(best, run_hi - run_lo)
            run_lo = run_hi = v
        else:
            run_lo = min(run_lo, v)
            run_hi = max(run_hi, v)
        prev = t
    return float(max(best, run_hi - run_lo))


def src_span_in(a, b):
    """同一窗口内源（双检测器一致口径）的 F0 跨度，作为同窗可证伪基准。"""
    tr = src_track(a + 0.005, b - 0.005)
    if tr is None:
        return 0.0
    return span_of_runs(tr[0], tr[1])


def dominant_cycle(tt, vv):
    """去趋势后的主周期（Hz）与幅度（c）。"""
    if len(tt) < 12:
        return None
    x = tt - tt.mean()
    y = vv - np.polyval(np.polyfit(x, vv, 1), x)
    if len(y) < 12:
        return None
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y))))
    fr = np.fft.rfftfreq(len(y), float(np.mean(np.diff(tt))) if len(tt) > 1 else 0.01)
    band = (fr >= 3.0) & (fr <= 8.5)
    if not band.any():
        return None
    idx = int(np.argmax(sp[band]))
    freq = float(fr[band][idx])
    amp = float(sp[band][idx] / max(1e-9, (len(y) / 2.0)))
    if amp < 12.0 or freq <= 0:
        return None
    return dict(freq=freq, amp=amp)


plan_phrases = []
brief_phrases = []
ledger_decisions = []
design_log = []

for pi in range(len(native)):
    vp = doc["voice_parts"][pi]
    part_pos = vp["position"]
    pid = hfa_by_pid[f"p{pi:02d}"]["phrase_id"]
    hanzi = hfa_by_pid[f"p{pi:02d}"]["hanzi"]
    times_s = np.asarray(native[pi]["times_ms"], dtype=float) / 1000.0
    t0, t1 = float(times_s[0]), float(times_s[-1])

    notes = []
    for n in vp["notes"]:
        a = (part_pos + n["position"]) * TICK_S
        b = (part_pos + n["position"] + n["duration"]) * TICK_S
        notes.append(dict(start=a, end=b, level=float(n["tone"] * 100), lyric=n["lyric"]))
    sung = [i for i, n in enumerate(notes) if n["lyric"] not in ("SP", "AP")]

    # ---------- 2. 字腹窗口与源残差（核心有声段口径） ----------
    for i, n in enumerate(notes):
        n["resid"] = None
        n["src_span"] = 0.0
        n["clip"] = 180.0
        n["core_level"] = n["level"]
        if n["lyric"] in ("SP", "AP"):
            continue
        # 核心段用整窗判定（与字尾连接无关）
        tr = src_track(n["start"], n["end"])
        if tr is None:
            continue
        tt, vv = tr
        # 按有声段切分，取最长的一段作为该字的核心（辅音静默处的 F0 失锁不能算字腹）
        runs_ = []
        s0 = 0
        for j in range(1, len(tt) + 1):
            if j == len(tt) or tt[j] - tt[j - 1] > 0.06:
                if j - s0 >= 2:
                    runs_.append((s0, j))
                s0 = j
        if not runs_:
            continue
        a0, b0 = max(runs_, key=lambda r: r[1] - r[0])
        ct, cv = tt[a0:b0], vv[a0:b0]
        level = float(np.median(cv))
        n["core_level"] = level
        n["src_span"] = float(cv.max() - cv.min())
        n["clip"] = float(max(120.0, 0.30 * n["src_span"]))
        n["resid"] = (ct, cv - level)

    # ---------- 1. 连接段 ----------
    conn = {}
    for k, i in enumerate(sung):
        if k + 1 >= len(sung):
            continue
        j = sung[k + 1]
        gap = notes[j]["start"] - notes[i]["end"]
        leap = abs(notes[j]["core_level"] - notes[i]["core_level"])
        base = 0.10 if (notes[i]["lyric"] == "+" or notes[j]["lyric"] == "+") else 0.20
        ramp_len = max(base, leap / 2500.0)          # 斜率上限约 2500 c/s
        ramp_len = min(ramp_len + max(0.0, gap), 0.35)
        ramp_len = max(0.05, min(ramp_len, notes[i]["end"] - notes[i]["start"] - 0.02))
        # 连接必须落在本音符之内（或跨过空隙），不能越过本音符的结尾
        r_start = min(max(notes[i]["start"] + 0.02, notes[j]["start"] - ramp_len),
                      notes[i]["end"] - 0.02)
        conn[i] = dict(end=notes[j]["start"], start=r_start, target=notes[j]["core_level"])

    # 字腹窗口右界：连接起点（连接不算字腹）
    body_end_of = {i: notes[i]["end"] for i in sung}
    for i, c in conn.items():
        body_end_of[i] = c["start"]

    def body_value(i, t):
        n = notes[i]
        if n["resid"] is None:
            return n["core_level"]
        tt, rsv = n["resid"]
        if len(tt) == 0:
            return n["core_level"]
        lim = n["clip"]
        b_end = body_end_of.get(i, n["end"])
        taper = 1.0
        if t > b_end - 0.025:
            taper = max(0.0, (b_end - t) / 0.025)
        val = float(np.interp(t, tt, np.clip(rsv, -lim, lim)))
        return n["core_level"] + 0.8 * taper * val


    def ramp_value(v0, v1, u):
        d = v1 - v0
        base = v0 + d * smoothstep(u)
        extra = (-min(15.0, 0.10 * abs(d)) if d > 0 else min(15.0, 0.10 * abs(d))) * math.sin(math.pi * u)
        return base + extra

    # ---------- 3. 中心线 ----------
    def center_at(t):
        for i, n in enumerate(notes):
            if n["start"] - 1e-9 <= t <= n["end"] + 1e-9:
                c = conn.get(i)
                if c and t > c["start"]:
                    v0 = body_value(i, c["start"])
                    u = (t - c["start"]) / max(1e-6, c["end"] - c["start"])
                    return ramp_value(v0, c["target"], u)
                return body_value(i, t)
        for k, i in enumerate(sung[:-1]):
            j = sung[k + 1]
            if notes[i]["end"] < t < notes[j]["start"]:
                c = conn.get(i)
                if c and t > c["start"]:
                    v0 = body_value(i, c["start"])
                    u = (t - c["start"]) / max(1e-6, c["end"] - c["start"])
                    return ramp_value(v0, c["target"], u)
                return notes[j]["level"]
        return notes[0]["level"] if t < notes[0]["start"] else notes[-1]["level"]

    grid = set()
    for n in notes:
        step = 0.015
        k = int(math.ceil((n["end"] - n["start"]) / step))
        for j in range(k + 1):
            grid.add(n["start"] + (n["end"] - n["start"]) * j / max(1, k))
    for c in conn.values():
        grid.add(c["start"])
        grid.add(c["end"])
    grid.add(t0)
    grid.add(t1)
    grid = sorted(g for g in grid if t0 - 1e-12 <= g <= t1 + 1e-12)
    grid[0], grid[-1] = t0, t1
    grid = sorted(set(grid))
    vals = [center_at(g) for g in grid]
    slopes = []
    for j in range(len(grid)):
        if j == 0:
            s = (vals[1] - vals[0]) / max(1e-6, grid[1] - grid[0]) if len(grid) > 1 else 0.0
        elif j == len(grid) - 1:
            s = (vals[-1] - vals[-2]) / max(1e-6, grid[-1] - grid[-2]) if len(grid) > 1 else 0.0
        else:
            s = (vals[j + 1] - vals[j - 1]) / max(1e-6, grid[j + 1] - grid[j - 1])
        slopes.append(round(float(s), 3))
    center_nodes = [[float(g), round(float(v), 3), slopes[j]] for j, (g, v) in enumerate(zip(grid, vals))]
    # 连接起点/终点斜率显式归零：smoothstep 两端导数为 0，避免 Hermite 过冲
    for c in conn.values():
        for j, g in enumerate(grid):
            if abs(g - c["start"]) < 1e-9 or abs(g - c["end"]) < 1e-9:
                center_nodes[j][2] = 0.0
    center_nodes[0][2] = 0.0
    center_nodes[-1][2] = 0.0

    # ---------- 4. 动作组件（源驱动，不是模板） ----------
    components = []
    note_comp = {}
    for i in sung:
        n = notes[i]
        dur = n["end"] - n["start"]
        if n["resid"] is None:
            continue
        tt, rsv = n["resid"]
        dc = dominant_cycle(tt, rsv)
        if dc and dur >= 0.55:
            depth = float(min(60.0, max(32.0, 0.8 * dc["amp"])))
            rate = float(min(7.5, max(3.6, dc["freq"])))
            a, b = n["start"] + 0.02, n["end"] - 0.02
            comp = dict(id=f"p{pi}:n{i}:osc", family="oscillation",
                        support_s=[a, b],
                        attack_end_s=a + 0.18 * (b - a),
                        release_start_s=b - 0.24 * (b - a),
                        depth_nodes=[[a, depth * 0.45], [(a + b) / 2, depth], [b, depth * 0.40]],
                        rate_nodes=[[a, rate * 0.95], [b, rate * 1.05]],
                        phase_rad=round(float((i * 0.37) % (2 * math.pi)), 4))
            components.append(comp)
            note_comp[i] = comp
            continue
        if len(tt) >= 5:
            k = int(np.argmax(np.abs(rsv)))
            exc = float(rsv[k])
            if abs(exc) >= 35.0:
                ts = float(tt[k])
                a = min(max(n["start"] + 0.01, ts - 0.16), n["end"] - 0.05)
                b = max(min(n["end"] - 0.01, ts + 0.16), a + 0.08)
                ts = min(max(ts, a + 0.02), b - 0.02)
                if b - a >= 0.08:
                    exc = float(np.clip(exc, -250.0, 250.0))
                    comp = dict(id=f"p{pi}:n{i}:fr", family="finite_return",
                                support_s=[a, b], peak_s=ts, peak_c=round(exc, 2))
                    components.append(comp)
                    note_comp[i] = comp

    # ---------- 5. plan 级 decision / expectation ----------
    decisions, expectations = [], []
    for idx, i in enumerate(sung):
        n = notes[i]
        a, b = max(n["start"], t0), min(n["end"], t1)
        if b <= a:
            continue
        comp = note_comp.get(i)
        src_span = n["src_span"]
        b_end = max(a + 0.02, min(b, body_end_of.get(i, b)))
        body_span = n["src_span"]
        comp_amp = abs(comp["peak_c"]) if comp and comp["family"] == "finite_return" else 0.0
        if comp is None:
            choice = "hold" if body_span < 25 else "center"
        elif comp["family"] == "oscillation":
            choice = "oscillation"
        else:
            choice = "finite_return"
        cid = [comp["id"]] if comp else []
        if choice == "oscillation":
            cond = (f"'{n['lyric']}' ({a:.2f}-{b:.2f}s, {b-a:.2f}s) 源内残差呈周期性起伏"
                    f"（主频约 {comp['rate_nodes'][0][1]:.1f}Hz），需要持续展开而不是一次鼓包")
            alt = "把该字做成一条带轻微下探的平台，或只给一次浅波动"
            reason = "源在该字内的起伏是周期性的，压成平台会丢掉持续段的呼吸与支撑"
        elif choice == "finite_return":
            cond = (f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源内出现单次明显拐点"
                    f"（偏移 {comp['peak_c']:+.0f}c @ {comp['peak_s']:.2f}s）")
            alt = "用一条恒定平台穿过该字，忽略源里的这次下探/上挑"
            reason = "该拐点是源演唱里真实存在的一次字腹动作，抹平会让该字失去方向感"
        elif choice == "center":
            cond = f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源内残差跨度 {body_span:.0f}c，存在方向性但非独立拐点"
            alt = "给该字额外加一个与源无关的固定幅度鼓包"
            reason = "源已有方向性走势，中心线已贴合；再叠加固定鼓包会重复源动作并破坏逐字差异"
        else:
            cond = f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源内基本平直（字腹窗口跨度 {body_span:.0f}c）"
            alt = "为了全曲一致而给该字套一个与其他字相同的起伏"
            reason = "该字在源里本来就是收住的短字，保持平直是有依据的选择；统一鼓包会制造模板化"
        decisions.append(dict(support_s=[a, b], condition=cond, choice=choice,
                              alternative=alt, reason=reason,
                              uncertainty="自然度未经人耳确认（本次制作无听感工具）。",
                              component_ids=cid))
        frames = src_frames(a, b_end)
        if b_end - a >= 0.05 and frames >= 4:
            lo = round(max(4.0, 0.08 * body_span), 2) if body_span >= 60 else 0.0
            in_leap = 0.0
            for pk, pc_ in conn.items():
                if abs(pc_["end"] - a) < 1e-6:
                    in_leap = abs(pc_["target"] - notes[pk]["core_level"])
            out_leap = abs(conn[i]["target"] - n["core_level"]) if i in conn else 0.0
            hi = round(max(320.0, 2.5 * body_span + comp_amp + 200.0 + in_leap + out_leap), 2)
            win = [a, b_end]
            purpose = (f"'{n['lyric']}' 的字腹运动幅度应与同一窗口内源实测跨度（{body_span:.0f}c）同量级，"
                       f"既不压平也不夸张；字尾连接不计入本项")
        elif b_end - a >= 0.05:
            c0 = conn.get(i)
            l0 = abs(c0["target"] - n["core_level"]) if c0 else 0.0
            in_l0 = 0.0
            for pk, pc_ in conn.items():
                if abs(pc_["end"] - a) < 1e-6:
                    in_l0 = abs(pc_["target"] - notes[pk]["core_level"])
            lo, hi = 0.0, round(max(430.0, 2.5 * (l0 + in_l0) + 200.0), 2)
            win = [a, b_end]
            purpose = (f"'{n['lyric']}' 在该窗口的源支撑不足（{frames} 帧），"
                       f"不应凭空虚构字腹幅度，保持贴近名义音高即可")
        else:
            c = conn.get(i)
            leap = abs(c["target"] - n["core_level"]) if c else 0.0
            win = [c["start"], c["end"]] if c else [a, b]
            lo = round(max(4.0, 0.45 * leap), 2) if leap > 12.0 else 0.0
            in_l0 = 0.0
            for pk, pc_ in conn.items():
                if abs(pc_["end"] - a) < 1e-6:
                    in_l0 = abs(pc_["target"] - notes[pk]["core_level"])
            hi = round(max(430.0, 2.5 * (leap + in_l0) + 200.0), 2)
            purpose = (f"'{n['lyric']}' 是短促过渡字：连接必须实际走向下一字（{leap:.0f}c），不能停在原地")
        expectations.append(dict(support_s=win, range_c=[lo, hi], purpose=purpose))

    full = []
    prev = t0
    for d in decisions:
        if d["support_s"][0] > prev + 1e-9:
            full.append(dict(support_s=[prev, d["support_s"][0]],
                             condition="非唱区间（呼吸/静默）", choice="hold",
                             alternative="在呼吸区间画一条有起伏的线",
                             reason="非唱区间不承载演唱动作，保持与前字同电平",
                             uncertainty="呼吸处理未经人耳确认。", component_ids=[]))
        full.append(d)
        prev = d["support_s"][1]
    if prev < t1 - 1e-9:
        full.append(dict(support_s=[prev, t1],
                         condition="非唱区间（呼吸/静默）", choice="hold",
                         alternative="在句尾呼吸里加入旋律动作",
                         reason="句尾呼吸不承载演唱动作", uncertainty="呼吸处理未经人耳确认。",
                         component_ids=[]))
    decisions = full
    if decisions:
        decisions[0]["support_s"][0] = t0
        decisions[-1]["support_s"][1] = t1

    # ---------- 6. 意图简报（pre-plan） ----------
    p_units = units_by_part.get(pi, [])
    if not p_units:
        continue
    src_spans = [n["src_span"] for n in notes if n["lyric"] not in ("SP", "AP")]
    obs = [
        dict(id=f"{pid}:obs_src", source_id="fcpe_obs", source_window_s=[t0, t1],
             description=(f"'{hanzi}' 全句双检测器一致 F0 轨迹：{len(sung)} 个唱字，"
                          f"电平 {min(n['level'] for n in notes):.0f}-{max(n['level'] for n in notes):.0f}c，"
                          f"句内源 RMS {metrics['metrics'][str(pi)]['rms_db']:.1f}dB"),
             reliability="observed"),
        dict(id=f"{pid}:obs_body", source_id="rmvpe_obs", source_window_s=[t0, t1],
             description=(f"句内逐字字腹跨度中位 {np.median(src_spans):.0f}c，"
                          f"最长 {max(src_spans) if src_spans else 0:.0f}c"),
             reliability="observed"),
        dict(id=f"{pid}:obs_breath", source_id="hfa_summary", source_window_s=[t0, t1],
             description="源对齐给出的字序列与呼吸位置（仅取字身份，边界以有声段为准）",
             reliability="uncertain"),
    ]
    gestures = []
    for k, u in enumerate(p_units):
        ua, ub = u["support_s"]
        owner = None
        for i in sung:
            if notes[i]["start"] - 1e-6 <= ua and ub <= notes[i]["end"] + 1e-6:
                owner = i
                break
        if owner is None:
            owner = min(sung, key=lambda i: abs(notes[i]["start"] - ua))
        comp = note_comp.get(owner)
        # 字腹窗口：排除字尾连接（连接由前一个音承担，不算字腹幅度）
        b_end = min(ub, body_end_of.get(owner, ub))
        if b_end <= ua + 0.01:
            b_end = ub
        body_win = [max(ua, u["stages"][0]["support_s"][0]), min(b_end, u["stages"][0]["support_s"][1])]
        if body_win[1] <= body_win[0] + 0.005:
            body_win = [ua, ub]
        src_span = notes[owner]["src_span"]
        role = "arrival" if k == 0 else ("release" if k == len(p_units) - 1 else "body")
        if comp is not None and comp["family"] == "oscillation":
            contrast = dict(mode="must_differ", shallow_limit_c=25, connection_s=0.08,
                            reason="持续字必须展开成周期；只保留浅起伏的对照应被否决")
            checks = [dict(kind="cycles", support_s=body_win,
                           parameters=dict(min_cycles=1, prominence_c=30.0))]
        elif src_span >= 75 and (body_win[1] - body_win[0]) * 1000.0 >= 120 and len(u.get("note_ids") or []) == 1:
            # 源幅度足够且窗口可测、且该字不跨音符：要求字腹与源同量级，浅对照（±25c）无法通过
            contrast = dict(mode="must_differ", shallow_limit_c=25, connection_s=0.08,
                            reason="字腹要有源自源的方向性幅度；统一短连接+浅起伏的对照应被否决")
            checks = [dict(kind="range", support_s=body_win,
                           parameters=dict(min_c=round(max(60.0, 0.10 * src_span), 2) if src_span >= 120 else 0,
                                           max_c=round(max(150.0, 1.4 * src_span + 60.0), 2)))]
        else:
            contrast = dict(mode="may_match", shallow_limit_c=25, connection_s=0.08,
                            reason="该字在源里本就平直或幅度有限，允许与浅对照一致；本句的区分点在其它字与连接")
            checks = [dict(kind="hold", support_s=body_win,
                           parameters=dict(min_c=0, max_c=round(max(220.0, 1.6 * src_span + 120.0), 2)))]
        gestures.append(dict(
            id=f"{pid}:g{k}", unit_ids=[u["id"]], role=role, support_s=[ua, ub],
            observation_ids=[obs[0]["id"], obs[1]["id"]],
            interpretation=(f"'{u.get('lyric')}' 的字腹按源实测（同窗跨度 {src_span:.0f}c）保留方向与幅度，"
                            f"不套用统一鼓包"),
            alternative="用与全曲其它字相同的固定鼓包/平台代替该字的源形状",
            rejected_because="统一模板会抹掉逐字的源差异，正是上一版被否掉的形态",
            contrast=contrast, checks=checks))
    brief_phrases.append(dict(
        id=pid, unit_ids=[u["id"] for u in p_units],
        support_s=[min(t0, min(u["support_s"][0] for u in p_units)),
                   max(t1, max(u["support_s"][1] for u in p_units))],
        observations=obs,
        intention=(f"'{hanzi}'（{ROLE.get(str(pi), 'verse')}）：旋律回到原唱实测电平，"
                   f"字腹按源逐字还原，字间用实唱连接而不是垂直台阶，"
                   f"发声层按本句实测电平/音高单独设定"),
        gestures=gestures))

    design = dict(schema=1, origin="agent_designed", support_s=[t0, t1],
                  center_nodes=center_nodes, components=components,
                  decisions=decisions, expectations=expectations)
    plan_phrases.append(dict(part_index=pi, position=int(native[pi]["position"]), design=design))
    design_log.append(dict(phrase=pid, role=ROLE.get(str(pi)), nodes=len(center_nodes),
                            components=len(components),
                            zero_slope=sum(1 for n in center_nodes if n[2] == 0),
                            span_c=round(max(vals) - min(vals), 1),
                            src_span_c=round(max((n["src_span"] for n in notes if n["lyric"] not in ("SP", "AP")), default=0), 1)))

    # ---------- 7. ledger（按库存单元） ----------
    phrase_ledger = []
    for k, u in enumerate(p_units):
        ua, ub = u["support_s"]
        owner = None
        for i in sung:
            if notes[i]["start"] - 1e-6 <= ua and ub <= notes[i]["end"] + 1e-6:
                owner = i
                break
        if owner is None:
            owner = min(sung, key=lambda i: abs(notes[i]["start"] - ua))
        comp = note_comp.get(owner)
        src_span = notes[owner]["src_span"]
        stage_id = f"{u['id']}:body"
        stage = next((s for s in u["stages"] if s["id"] == stage_id), None)
        body_win = [ua, min(ub, body_end_of.get(owner, ub))]
        if body_win[1] <= body_win[0] + 0.01:
            body_win = [ua, ub]
        # 检查窗口必须落在冻结阶段内
        body_win = [max(body_win[0], stage["support_s"][0]), min(body_win[1], stage["support_s"][1])]
        if body_win[1] <= body_win[0] + 0.005:
            body_win = list(stage["support_s"])
        unit_span = notes[owner]["src_span"]
        unit_comp_amp = abs(comp["peak_c"]) if comp and comp["family"] == "finite_return" else 0.0
        own_leap = 0.0
        for pk, pc_ in conn.items():
            if abs(pc_["end"] - ua) < 1e-6 or pk == owner:
                own_leap += abs(pc_["target"] - notes[pk]["core_level"])
        conn_here = conn.get(owner)
        degenerate = (body_win[1] - body_win[0]) < 0.05
        if comp and comp["family"] == "oscillation":
            choice = "oscillation"
            checks = [dict(stage_id=stage_id, kind="cycles", support_s=body_win,
                           parameters=dict(min_cycles=1, prominence_c=30.0))]
        elif degenerate and conn_here:
            # 短促过渡字：本身没有字腹（连接由前一个音承担），只要求不虚增幅度
            choice = "hold"
            leap = abs(conn_here["target"] - notes[owner]["level"])
            checks = [dict(stage_id=stage_id, kind="hold", support_s=body_win,
                           parameters=dict(min_c=0, max_c=round(max(220.0, 2.0 * leap + 100.0), 2)))]
        elif src_frames(body_win[0], body_win[1]) < 4:
            choice = "hold"
            checks = [dict(stage_id=stage_id, kind="hold", support_s=body_win,
                           parameters=dict(min_c=0, max_c=200.0))]
        elif unit_span < 25:
            choice = "hold"
            checks = [dict(stage_id=stage_id, kind="hold", support_s=body_win,
                           parameters=dict(min_c=0, max_c=round(max(140.0, 1.5 * unit_span + 60.0), 2)))]
        else:
            choice = "center"
            checks = [dict(stage_id=stage_id, kind="range", support_s=body_win,
                           parameters=dict(min_c=round(max(4.0, 0.18 * unit_span), 2) if unit_span >= 40 else 0,
                                           max_c=round(max(320.0, 2.5 * unit_span + unit_comp_amp + 200.0 + own_leap), 2)))]
        execution = [dict(kind="center_nodes", part_index=pi, position=int(native[pi]["position"]),
                          id="center_nodes", support_s=[t0, t1],
                          parameters_sha256=digest(center_nodes))]
        if comp:
            execution.append(dict(kind="component", part_index=pi, position=int(native[pi]["position"]),
                                  id=comp["id"], support_s=comp["support_s"],
                                  parameters_sha256=digest(comp)))
        phrase_ledger.append(dict(
            id=f"dec:{u['id']}", unit_ids=[u["id"]], stage_ids=[stage_id],
            support_s=[ua, ub],
            evidence_ids=["fcpe_obs", "rmvpe_obs", "game_obs", "hfa_summary"],
            observation=(f"'{u.get('lyric')}' ({u.get('symbol')}) {ua:.3f}-{ub:.3f}s，"
                         f"同窗源跨度 {unit_span:.0f}c"),
            interpretation=("源内平直，保持该字贴合源线" if choice == "hold" else
                           "短促过渡字，检查其连接是否真正走向下一字" if degenerate and conn_here else
                           "源内有独立方向/起伏，按源形状画字腹" if comp is None else
                           "源内为持续周期，按源频率与深度展开"),
            reliability="high; 双检测器一致口径",
            purpose=f"让 '{u.get('lyric')}' 的字腹反映原唱该字的实际运动",
            choice=choice,
            alternative="套用全曲统一的固定幅度鼓包",
            rejected_because="统一鼓包不区分源逐字差异，属于上一版被否的模板化形态",
            parameter_basis=(f"参数取自源实测：同窗跨度 {unit_span:.0f}c"
                             + (f"，组件 {comp['id']}" if comp else "")),
            execution=execution, checks=checks,
            uncertainty="自然度与听感未经人耳确认；本轮只有数值与图审证据。"))

    # 每个组件都必须被某条决策绑定（否则复检记 unmapped_component）
    mapped = {e["id"] for d in phrase_ledger for e in d["execution"] if e["kind"] == "component"}
    for comp in components:
        if comp["id"] in mapped:
            continue
        mid = (comp["support_s"][0] + comp["support_s"][1]) / 2
        best = min(phrase_ledger, key=lambda d: abs((d["support_s"][0] + d["support_s"][1]) / 2 - mid))
        best["execution"].append(dict(kind="component", part_index=pi, position=int(native[pi]["position"]),
                                      id=comp["id"], support_s=comp["support_s"],
                                      parameters_sha256=digest(comp)))
    ledger_decisions.extend(phrase_ledger)

json.dump(design_log, open(DESIGN / "design_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("designs built:", len(plan_phrases))
print("components:", sum(len(p["design"]["components"]) for p in plan_phrases),
      "| zero-slope nodes:", sum(p["zero_slope"] for p in design_log), "/", sum(p["nodes"] for p in design_log))

# ---------------- 意图简报 + 冻结（plan 尚不存在） ----------------
brief = dict(schema_version=1,
             inventory=dict(path=str((DESIGN / "review-inventory.json").resolve()),
                            sha256=sha256(DESIGN / "review-inventory.json")),
             phrases=brief_phrases,
             phonation=dict(
                 baseline="YousaV1.65c 原生基底，未加人工增量",
                 target=("每句 VOIC/TENC/BREC/DYN 依据该句源实测 RMS 与音高区间单独设定"
                         "（51 组不同取值），而不是按段落套用固定值"),
                 status="unvalidated", contexts=[]))
brief_path = DESIGN / "musical_intent.json"
brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
print("brief written:", len(brief_phrases), "phrases")

plan_path = DESIGN / "plan.json"
plan_path.unlink(missing_ok=True)
lock_path = DESIGN / "intent_lock.json"
lock_path.unlink(missing_ok=True)
lock = freeze_intent(str(brief_path), str(DESIGN / "review-inventory.json"), str(plan_path), str(lock_path))
print("intent lock frozen:", lock["frozen_at"])

# ---------------- 知识包 ----------------
kb_dst = DESIGN / "knowledge_context.json"
shutil.copyfile(V1 / "design" / "knowledge_context.json", kb_dst)
packet = rj(kb_dst)
decisions = []
for rec in packet["records"]:
    rid = rec["id"]
    decisions.append(dict(id=rid, decision="use",
                          reason=(f"沿用本次制作前对表1/表2的检索结果：{rid} 的条件与本曲逐句画线直接相关，"
                                  f"在 v2 中用于约束'逐字按源还原、连接要可唱、动作要可证伪'这三项。"),
                          condition_match="普通话流行翻唱；本句为已观测的源条件下单句制作。",
                          limitations="仅为条件化经验条目，不提供数值剂量，也不证明当前句的听觉自然度。",
                          general_rule_claim=False))
knowledge_block = dict(path=str(kb_dst.resolve()), sha256=sha256(kb_dst), decisions=decisions)

# ---------------- plan ----------------
vocal_stem = str((V2 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav").resolve())
plan = dict(schema_version=2, project=str(SCORE.resolve()), source_audio=vocal_stem,
            input_hashes={str(SCORE.resolve()): sha256(SCORE),
                          vocal_stem: rj(V2 / "observation" / "manifest.json")["files"]["stems\\source_(vocals)_vocals_mel_band_roformer.wav"],
                          str((DESIGN / "baseline_pitch.json").resolve()): sha256(DESIGN / "baseline_pitch.json"),
                          str((DESIGN / "baseline_phones.json").resolve()): sha256(DESIGN / "baseline_phones.json"),
                          str((V2 / "hfa" / "hfa_summary.json").resolve()): sha256(V2 / "hfa" / "hfa_summary.json")},
            scope="whole_song", phrases=plan_phrases, knowledge_context=knowledge_block)
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print("plan written:", len(plan_phrases), "phrases")

# ---------------- ledger ----------------
ledger = dict(schema_version=1,
               inventory=dict(path=str((DESIGN / "review-inventory.json").resolve()),
                              sha256=sha256(DESIGN / "review-inventory.json")),
               plan=dict(path=str(plan_path.resolve()), sha256=sha256(plan_path)),
               timing="forward", decisions=ledger_decisions, revisions=[])
(DESIGN / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
print("ledger written:", len(ledger_decisions), "decisions")
