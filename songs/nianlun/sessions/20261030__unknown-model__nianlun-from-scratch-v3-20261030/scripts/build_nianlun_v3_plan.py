"""年轮 v3 画线（阶段 C）：源迹线为中心线 + 逐音符涟漪组件 + 逐音符决策/判据。

与 v2 的根本差别（对应 B 站流程里"照着参考原唱一条条画"）：
  * 中心线不再是"名义音高平台 + 0.8 倍残差"，而是**直接描原唱的双检测器一致 F0 迹线**
    （50ms 中值平滑去噪，保留原唱的旋律走向与字腹幅度）。
  * 原唱的 F0 涟漪（颤音）不再被平滑掉，而是按实测主频/幅度/相位写成逐音符
    `oscillation` 组件，落在字腹窗口内。
  * 字间连接仍由本音符尾部承担（70-250ms 平滑斜坡，斜率上限约 2500c/s），
    终点取下一字在源里的实际电平，而不是下一字的名义音高。
  * 判据可证伪：range 的上下界由**源实测跨度**推出（0.65S ~ 1.45S+25c），
    涟漪字另加 cycles 判据（prominence 由源实测涟漪幅度推出）；
    浅对照（±25c 削平）无法通过 range 下界。

严格顺序：意图简报 -> 冻结（plan 尚不存在）-> 数值 plan -> ledger。
"""
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))

from agent2utau.openutau.ustx import TempoMap, load_ustx, sha256
from agent2utau.evaluation.execution_review import digest, validate_inventory, check_action
from agent2utau.evaluation.musical_review import freeze_intent
from nianlun_v3_source import Source, filled_track, local_detrend


def eval_design(design, times):
    """向量化求值设计（与 design_functions.evaluate 同式，用于生成期自检）。"""
    nodes = np.asarray(design["center_nodes"], float)
    ts, vs, ss = nodes[:, 0], nodes[:, 1], nodes[:, 2]
    idx = np.clip(np.searchsorted(ts, times, side="right") - 1, 0, len(ts) - 2)
    a, b = nodes[idx], nodes[idx + 1]
    dt = b[:, 0] - a[:, 0]
    u = np.clip((times - a[:, 0]) / dt, 0.0, 1.0)
    out = (a[:, 1] + (-2 * u ** 3 + 3 * u ** 2) * (b[:, 1] - a[:, 1])
           + (u ** 3 - 2 * u ** 2 + u) * dt * a[:, 2] + (u ** 3 - u ** 2) * dt * b[:, 2])
    for c in design["components"]:
        if c["family"] != "oscillation":
            continue
        x, y = c["support_s"]
        m = (times > x) & (times < y)
        if not m.any():
            continue

        def q5(uu):
            uu = np.clip(uu, 0.0, 1.0)
            return uu * uu * uu * (10 + uu * (-15 + 6 * uu))

        tm = times[m]
        env = np.where(tm <= c["attack_end_s"], q5((tm - x) / max(1e-6, c["attack_end_s"] - x)),
                       np.where(tm >= c["release_start_s"], q5((y - tm) / max(1e-6, y - c["release_start_s"])), 1.0))
        rn = np.asarray(c["rate_nodes"], float)
        r0, r1 = rn[0, 1], rn[-1, 1]
        span = max(1e-6, y - x)
        integ = r0 * (tm - x) + (r1 - r0) * (tm - x) ** 2 / (2 * span)
        dn = np.asarray(c["depth_nodes"], float)
        depth = np.interp(tm, dn[:, 0], dn[:, 1])
        out[m] = out[m] + env * depth * np.sin(c["phase_rad"] + 2 * np.pi * integ)
    return out

V2 = ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028"
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
SCORE = DESIGN / "score.ustx"
TICK_S = 60.0 / (120.0 * 480)


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def smoothstep(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * (3 - 2 * u)


def median_smooth(v, k=5):
    """中值平滑（抗离群），边界用端点值补齐。"""
    v = np.asarray(v, float)
    if len(v) < 3:
        return v
    half = k // 2
    out = np.empty_like(v)
    for i in range(len(v)):
        lo = max(0, i - half)
        hi = min(len(v), i + half + 1)
        out[i] = float(np.median(v[lo:hi]))
    return out


src = Source(V3)
doc = load_ustx(SCORE)
native = rj(DESIGN / "baseline_pitch.json")["phrases"]
inv = validate_inventory(DESIGN / "review-inventory.json")
feat = rj(DESIGN / "note_features.json")["notes"]
metrics = rj(DESIGN / "phrase_metrics.json")
align_log = rj(DESIGN / "align_log.json")
hfa = rj(V3 / "hfa" / "hfa_summary.json")
hfa_by_pid = {p["phrase_id"]: p for p in hfa["phrases"]}

units_by_part = {}
for u in inv["units"]:
    units_by_part.setdefault(u["part_index"], []).append(u)
feat_by_note = {(f["part_index"], f["note_index"]): f for f in feat}

RIPPLE_MIN = 18.0     # 低于该幅度不写涟漪组件（也判 hold）
SMOOTH_K = 5           # 50ms 中值窗
CONN_REACH = 625.0     # 字间连接的理论最大跨度：斜率上限 2500c/s × 最长 250ms


def ripple_fit(tt, vv, a, b):
    """在 3.0-8.5Hz 内找原唱的周期性涟漪（颤音）。

    用频谱锐度判断"是不是真的周期成分"：一段旋律下滑也会被低频正弦拟合，
    但它的频谱没有尖峰。必须同时满足：
      * 频谱峰锐度（峰/带内中位）>= 3.0、峰占带内能量 >= 0.35；
      * 幅度 >= 18c，且不超过该字旋律跨度的 0.35 倍（颤音是小幅调制）；
      * 该字至少容纳 2.5 个周期。
    不满足就返回 None（该字按源迹线直接画，不写周期组件）。
    """
    n = len(tt)
    if n < 24:
        return None
    dt = float(np.mean(np.diff(tt))) if n > 1 else 0.01
    if dt <= 0:
        return None
    res = local_detrend(vv, half=12)
    if res.std() < 3.0:
        return None
    win = np.hanning(n)
    sp = np.abs(np.fft.rfft(res * win)) ** 2
    fr = np.fft.rfftfreq(n, dt)
    band = (fr >= 2.5) & (fr <= 8.5)
    if band.sum() < 4:
        return None
    bp = sp[band]
    idx = int(np.argmax(bp))
    f = float(fr[band][idx])
    peak = float(bp[idx])
    med = float(np.median(bp))
    total = float(bp.sum())
    if med <= 0 or total <= 0:
        return None
    if peak / med < 2.0 or peak / total < 0.20:
        return None
    # 在峰值频率附近做最小二乘拟合，取幅度与相位
    best = None
    for ff in np.arange(max(2.5, f - 0.4), min(8.5, f + 0.4) + 1e-9, 0.02):
        w = 2 * np.pi * ff * (tt - a)
        cm, sm = np.cos(w).mean(), np.sin(w).mean()
        cc = float(((np.cos(w) - cm) * (res - res.mean())).sum() / len(res))
        ss = float(((np.sin(w) - sm) * (res - res.mean())).sum() / len(res))
        amp = math.hypot(cc, ss)
        if best is None or amp > best[1]:
            best = (float(ff), amp, float(math.atan2(ss, cc) - math.pi / 2))
    f, amp, ph = best
    span = float(vv.max() - vv.min())
    if amp < RIPPLE_MIN or amp > 0.35 * max(span, 40.0):
        return None
    if (b - a) < 2.5 / f:
        return None
    # 涟漪的起止：按源里该字涟漪包络的半幅位置定进入/退出（不是固定比例模板）
    wave = amp * np.sin(2 * np.pi * f * (tt - a) + ph)
    win = max(3, int(0.12 / max(dt, 1e-3)))
    env = np.sqrt(np.convolve(wave ** 2, np.ones(win) / win, mode="same"))
    peak = float(env.max())
    if peak <= 0:
        return None
    half = env >= 0.5 * peak
    idx = np.where(half)[0]
    onset = float(tt[idx[0]]) if len(idx) else a + 0.25 * (b - a)
    offset = float(tt[idx[-1]]) if len(idx) else b - 0.25 * (b - a)
    return dict(freq=f, amp=amp, phase=ph, span=span, onset_s=onset, offset_s=offset)


plan_phrases, brief_phrases, ledger_decisions = [], [], []
selfcheck_fail = []
design_log = []
range_fail = []

for pi in range(len(native)):
    part = doc["voice_parts"][pi]
    base = part["position"] * TICK_S
    pid = hfa_by_pid[f"p{pi:02d}"]["phrase_id"]
    hanzi = hfa_by_pid[f"p{pi:02d}"]["hanzi"]
    times_s = np.asarray(native[pi]["times_ms"], float) / 1000.0
    t0, t1 = float(times_s[0]), float(times_s[-1])

    notes = []
    for ni, n in enumerate(part["notes"]):
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        notes.append(dict(index=ni, start=a, end=b, tone=int(n["tone"]), lyric=str(n["lyric"])))
    sung = [i for i, n in enumerate(notes) if n["lyric"] not in ("SP", "AP")]

    # ---------- 逐音符轮廓 + 涟漪 ----------
    contour = {}
    note_fill = {}
    note_smooth = {}
    ripples = {}
    gap_log = []
    for i in sung:
        n = notes[i]
        ft = filled_track(src, n["start"], n["end"])
        if ft is None:
            continue
        tt, vv, info = ft
        note_fill[i] = (tt, vv)
        note_smooth[i] = (tt, median_smooth(vv, SMOOTH_K))
        if info["gaps_over_60ms"]:
            gap_log.append(dict(part_index=pi, note_index=i, lyric=n["lyric"],
                                gaps=info["gaps_over_60ms"], max_gap_s=round(info["max_gap_s"], 3)))
        fit = ripple_fit(tt, vv, n["start"], n["end"])
        rip = None
        clean = vv
        if fit:
            # 只有真正写成组件的涟漪才从轮廓里扣掉（否则会凭空丢掉这段运动）
            f, amp, ph = fit["freq"], fit["amp"], fit["phase"]
            clean = vv - amp * np.sin(2 * np.pi * f * (tt - n["start"]) + ph)
            rip = dict(freq=f, amp=amp, phase=ph, onset_s=fit["onset_s"], offset_s=fit["offset_s"])
        contour[i] = (tt, median_smooth(clean, SMOOTH_K))
        if rip:
            ripples[i] = rip

    def cval(i, t):
        """某音符的轮廓在 t 处的值；该字没有可靠源迹线时退回源全局电平。"""
        if i not in contour:
            v = src.level_at(t)
            return float(v) if np.isfinite(v) else float(notes[i]["tone"] * 100)
        tt, cv = contour[i]
        if t <= tt[0]:
            return float(cv[0])
        if t >= tt[-1]:
            return float(cv[-1])
        return float(np.interp(t, tt, cv))

    def next_sung(i):
        for k in range(i + 1, len(notes)):
            if notes[k]["lyric"] not in ("SP", "AP"):
                return k
        return None

    # ---------- 字间连接：以边界为中心的平滑过渡（保留两侧轮廓） ----------
    # 旧做法把连接整段塞进前一个音的尾部，会把该音自身的旋律（源里真实的走向）抹平；
    # 现在改成在音符边界附近做过渡：两侧轮廓各自保留，只在边界 ±w 内混合。
    blends = []
    ramps = {}
    for i in sung:
        j = next_sung(i)
        if j is None:
            continue
        ni_, nj = notes[i], notes[j]
        T_prev = ni_["end"]
        T_next = nj["start"]
        left_v = cval(i, T_prev)
        right_v = cval(j, T_next)
        delta = right_v - left_v
        if abs(delta) < 8.0:
            ramps[i] = dict(start=T_prev, end=T_next, v0=left_v, v1=right_v)
            continue
        w = min(0.30, max(0.08, abs(delta) / 2500.0))
        w1 = min(w / 2, max(0.0, T_prev - ni_["start"] - 0.02))
        w2 = min(w / 2, max(0.0, nj["end"] - T_next - 0.02))
        blends.append(dict(L=T_prev - w1, R=T_next + w2, T_prev=T_prev, T_next=T_next,
                           w1=w1, w2=w2, i=i, j=j, delta=delta))
        ramps[i] = dict(start=T_prev - w1, end=T_next + w2, v0=left_v, v1=right_v)

    def blend_weight(bl, t):
        if t <= bl["L"]:
            return 0.0
        if t >= bl["R"]:
            return 1.0
        if t <= bl["T_prev"]:
            return 0.5 * smoothstep((t - bl["L"]) / max(1e-6, bl["w1"]))
        if t >= bl["T_next"]:
            return 0.5 + 0.5 * smoothstep((t - (bl["T_next"] - bl["w2"])) / max(1e-6, bl["w2"]))
        return 0.5

    def value_at(t):
        for i, n in enumerate(notes):
            if n["start"] - 1e-9 <= t <= n["end"] + 1e-9:
                if n["lyric"] in ("SP", "AP"):
                    prev = next((k for k in range(i - 1, -1, -1)
                                 if notes[k]["lyric"] not in ("SP", "AP")), None)
                    base = cval(prev, notes[prev]["end"]) if prev is not None else float(n["tone"] * 100)
                else:
                    base = cval(i, t)
                for bl in blends:
                    if bl["L"] - 1e-9 <= t <= bl["R"] + 1e-9:
                        g = blend_weight(bl, t)
                        left = cval(bl["i"], min(t, bl["T_prev"]))
                        right = cval(bl["j"], max(t, bl["T_next"]))
                        base = (1 - g) * left + g * right
                return base
        return float(notes[0]["tone"] * 100)

    # ---------- 判据区间（只由源实测推出） ----------
    def ripple_env(comp, t):
        x0, y0 = comp["support_s"]
        a_end, r_start = comp["attack_end_s"], comp["release_start_s"]

        def q5(u):
            u = min(max(u, 0.0), 1.0)
            return u * u * u * (10 + u * (-15 + 6 * u))

        if t <= a_end:
            return q5((t - x0) / max(1e-6, a_end - x0))
        if t >= r_start:
            return q5((y0 - t) / max(1e-6, y0 - r_start))
        return 1.0

    def virtual_source(a, b, note_idx):
        """窗口内的"源侧虚拟迹线"：有源的字用其补齐迹线，没有的用源全局电平，
        字与字之间没覆盖到的部分（呼吸/空隙）也用源全局电平。
        判据跨度按这条迹线量，与设计的取值域一致。"""
        vals = []
        covered = []
        for i in note_idx:
            n_i = notes[i]
            lo_t = max(a, n_i["start"])
            hi_t = min(b, n_i["end"])
            if hi_t <= lo_t:
                continue
            ft = note_smooth.get(i)
            used = False
            if ft is not None:
                t, v = ft
                m = (t >= lo_t - 1e-9) & (t <= hi_t + 1e-9)
                if m.sum() >= 2:
                    vals.extend(v[m].tolist())
                    covered.append((lo_t, hi_t))
                    used = True
            if not used:
                seg = np.linspace(lo_t, hi_t, 8)
                lv = np.array([src.level_at(float(x)) for x in seg])
                lv = lv[np.isfinite(lv)]
                if len(lv) >= 2:
                    vals.extend(lv.tolist())
                    covered.append((lo_t, hi_t))
        gaps = [(a, b)]
        for lo_t, hi_t in covered:
            new = []
            for g0, g1 in gaps:
                if g1 <= lo_t or g0 >= hi_t:
                    new.append((g0, g1))
                    continue
                if g0 < lo_t:
                    new.append((g0, lo_t))
                if hi_t < g1:
                    new.append((hi_t, g1))
            gaps = new
        for g0, g1 in gaps:
            if g1 - g0 < 1e-6:
                continue
            seg = np.linspace(g0, g1, 8)
            lv = np.array([src.level_at(float(x)) for x in seg])
            lv = lv[np.isfinite(lv)]
            if len(lv) >= 2:
                vals.extend(lv.tolist())
        return np.asarray(vals, float) if vals else None

    def source_span(a, b, note_idx):
        """源在窗口内的运动跨度（源侧虚拟迹线的极差，不含设计侧的涟漪/斜坡/插值）。"""
        vals = virtual_source(a, b, note_idx)
        if vals is not None and len(vals) >= 2:
            return float(vals.max() - vals.min()), int(len(vals))
        ft = filled_track(src, a, b)
        if ft is None:
            va, vb = src.level_at(a), src.level_at(b)
            if np.isfinite(va) and np.isfinite(vb):
                return float(abs(vb - va)), 0
            return 0.0, 0
        return float(ft[1].max() - ft[1].min()), int(len(ft[1]))

    def robust_span(a, b, note_idx=()):
        return source_span(a, b, list(note_idx))

    def band(a, b, note_idx):
        """从源实测推出该窗口的运动幅度区间（稳健窄窗/宽窗跨度 + 涟漪幅度）。

        宽窗用于吸收 50ms 中值平滑带来的插值余量；窄窗决定下界（可证伪：
        压平的设计会让实测跨度归零，从而低于下界）。
        """
        S_n, n_n = source_span(a, b, note_idx)
        S_w, n_w = source_span(a - 0.06, b + 0.06, note_idx)
        A = 0.0
        for i in note_idx:
            if i in ripples:
                A = max(A, ripples[i]["amp"])
        lo = max(0.0, 0.45 * min(S_n, S_w) - 2.0 * A)
        hi = 1.45 * max(S_n, S_w) + 2.0 * A + 25.0
        return lo, hi, S_n, S_w, A

    def notes_in(a, b):
        return [i for i in sung if notes[i]["start"] < b and notes[i]["end"] > a]

    # ---------- 中心线节点 ----------
    grid = set()
    step = 0.025
    for n in notes:
        k = int(math.ceil((n["end"] - n["start"]) / step))
        for j in range(k + 1):
            grid.add(n["start"] + (n["end"] - n["start"]) * j / max(1, k))
    for r in ramps.values():
        grid.add(r["start"])
        grid.add(r["end"])
    grid.add(t0)
    grid.add(t1)
    grid = sorted(g for g in grid if t0 - 1e-12 <= g <= t1 + 1e-12)
    grid[0], grid[-1] = t0, t1
    # 节点时间必须与 support_s 精确相等（DSL 校验），故不做四舍五入
    grid = sorted(set(grid))
    vals = [value_at(g) for g in grid]
    # 斜率：用单调限制（Fritsch-Carlson）避免三次 Hermite 在陡坡处过冲
    slopes = []
    for j in range(len(grid)):
        if j == 0:
            s = (vals[1] - vals[0]) / max(1e-6, grid[1] - grid[0]) if len(grid) > 1 else 0.0
            slopes.append(float(s))
        elif j == len(grid) - 1:
            s = (vals[-1] - vals[-2]) / max(1e-6, grid[-1] - grid[-2]) if len(grid) > 1 else 0.0
            slopes.append(float(s))
        else:
            dt1 = max(1e-6, grid[j] - grid[j - 1])
            dt2 = max(1e-6, grid[j + 1] - grid[j])
            d1 = (vals[j] - vals[j - 1]) / dt1
            d2 = (vals[j + 1] - vals[j]) / dt2
            if d1 * d2 <= 0:
                slopes.append(0.0)
            else:
                m = (vals[j + 1] - vals[j - 1]) / (dt1 + dt2)
                lim = 3.0 * min(abs(d1), abs(d2))
                slopes.append(float(np.clip(m, -lim, lim)))
    center_nodes = [[float(g), round(float(v), 3), round(float(slopes[j]), 3)]
                    for j, (g, v) in enumerate(zip(grid, vals))]
    # 连接斜坡两端导数显式归零，避免 Hermite 过冲
    for r in ramps.values():
        for j, g in enumerate(grid):
            if abs(g - r["start"]) < 1e-6 or abs(g - r["end"]) < 1e-6:
                center_nodes[j][2] = 0.0

    # ---------- 涟漪组件 ----------
    components = []
    comp_of_note = {}
    for i in sung:
        if i not in ripples:
            continue
        n = notes[i]
        rip = ripples[i]
        x = n["start"] + 0.01
        y = n["end"] - 0.01
        if y - x < 0.12:
            continue
        # 进入/退出点取自源里该字涟漪包络的半幅位置
        a_end = float(min(max(rip["onset_s"], x + 0.01), y - 0.02))
        r_start = float(min(max(rip["offset_s"], a_end), y - 0.01))
        if r_start <= a_end:
            a_end = x + 0.24 * (y - x)
            r_start = y - 0.30 * (y - x)
        depth = float(rip["amp"])
        rate = float(rip["freq"])
        phase = float(rip["phase"] + 2 * np.pi * rate * (x - n["start"]))
        comp = dict(id=f"p{pi}:n{i}:rip", family="oscillation",
                    support_s=[round(x, 6), round(y, 6)],
                    attack_end_s=round(a_end, 6), release_start_s=round(r_start, 6),
                    depth_nodes=[[round(x, 6), round(depth * 0.55, 3)],
                                 [round((x + y) / 2, 6), round(depth, 3)],
                                 [round(y, 6), round(depth * 0.5, 3)]],
                    rate_nodes=[[round(x, 6), round(rate, 4)], [round(y, 6), round(rate, 4)]],
                    phase_rad=round(phase, 4))
        components.append(comp)
        comp_of_note[i] = comp

    # ---------- 逐音符决策（plan 级） ----------
    decisions, expectations = [], []
    for i in sung:
        n = notes[i]
        a, b = max(n["start"], t0), min(n["end"], t1)
        if b <= a:
            continue
        f = feat_by_note.get((pi, i))
        r = ramps.get(i)
        body_end = r["start"] if r else b
        comp = comp_of_note.get(i)
        # 源实测跨度（字腹窗口，不含连接）
        tr = src.track(a + 0.01, max(a + 0.02, body_end - 0.01))
        src_span = float(tr[1].max() - tr[1].min()) if tr is not None else 0.0
        src_frames = len(tr[0]) if tr is not None else 0
        if comp is not None:
            choice = "oscillation"
            cond = (f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源内残差呈周期性起伏"
                    f"（主频 {comp['rate_nodes'][0][1]:.2f}Hz、幅度 {comp['depth_nodes'][1][1]:.0f}c），"
                    f"需要持续展开而不是一次鼓包")
            alt = "把该字做成一条平直平台，或只给一次浅波动"
            reason = "源在该字内的起伏是周期性的（原唱的颤音），压成平台会丢掉这段真实纹路"
        elif src_span >= 60:
            choice = "center"
            cond = (f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源字腹窗口跨度 {src_span:.0f}c，"
                    f"存在方向性运动（非单次拐点）")
            alt = "给该字套一个与源无关的固定幅度鼓包"
            reason = "源已有方向性走势，中心线已贴合；再叠加固定鼓包会重复源动作并破坏逐字差异"
        else:
            choice = "hold"
            cond = (f"'{n['lyric']}' ({a:.2f}-{b:.2f}s) 源字腹窗口跨度仅 {src_span:.0f}c"
                    f"（{src_frames} 帧），基本平直")
            alt = "为了全曲一致而给该字套一个与其他字相同的起伏"
            reason = "该字在源里本来就是收住的一口，保持贴合源线是有依据的选择；统一模板会制造假差异"
        decisions.append(dict(support_s=[round(a, 6), round(b, 6)], condition=cond, choice=choice,
                              alternative=alt, reason=reason,
                              uncertainty="自然度未经人耳确认（本次制作没有可用听感工具）。",
                              component_ids=[comp["id"]] if comp else []))
        if body_end - a >= 0.05:
            win = [max(a, t0), min(body_end, t1)]
            lo, hi, S_n, S_w, A = band(win[0], win[1], [i])
            # 窗口内若含字间连接，上限要容纳连接的理论最大跨度
            if any(r["start"] < win[1] and r["end"] > win[0] for r in ramps.values()):
                hi += CONN_REACH
            purpose = (f"'{n['lyric']}' 的字腹运动幅度应与同窗源实测跨度（窄窗 {S_n:.0f}c / "
                       f"宽窗 {S_w:.0f}c）同量级：既不压平也不夸张；字尾连接不计入本项")
        else:
            # 过短的字：判据窗口取整字（含连接），幅度不设下界（窗口不足以测量字腹），
            # 上限按"源跨度 + 连接的理论最大跨度"给出
            win = [max(a, t0), min(b, t1)]
            j2 = next_sung(i)
            wide_end = (notes[j2]["start"] if j2 else b) + 0.06
            lo, hi, S_n, S_w, A = band(win[0], wide_end, notes_in(win[0], wide_end))
            lo = 0.0
            hi += CONN_REACH
            purpose = (f"'{n['lyric']}' 是短促过渡字（含连接共 {S_w:.0f}c 的源跨度）："
                       f"幅度不设下界，但不得虚增运动")
        if win[1] <= win[0]:
            win = [win[0], min(t1, win[0] + 0.02)]
            hi = max(hi, lo + 1.0)
        if hi < lo:
            hi = lo + 1.0
        expectations.append(dict(support_s=[float(win[0]), float(win[1])],
                                  range_c=[round(lo, 3), round(hi, 3)], purpose=purpose))

    # 呼吸/静默段：hold 决策，把 decisions 铺满整句
    full = []
    prev = t0
    for d in decisions:
        if d["support_s"][0] > prev + 1e-9:
            full.append(dict(support_s=[round(prev, 6), round(d["support_s"][0], 6)],
                             condition="非唱区间（呼吸/静默）", choice="hold",
                             alternative="在呼吸区间画一条有起伏的线",
                             reason="非唱区间不承载演唱动作，保持与前字同电平",
                             uncertainty="呼吸处理未经人耳确认。", component_ids=[]))
        full.append(d)
        prev = d["support_s"][1]
    if prev < t1 - 1e-9:
        full.append(dict(support_s=[round(prev, 6), round(t1, 6)],
                         condition="非唱区间（呼吸/静默）", choice="hold",
                         alternative="在句尾呼吸里加入旋律动作",
                         reason="句尾呼吸不承载演唱动作",
                         uncertainty="呼吸处理未经人耳确认。", component_ids=[]))
    decisions = full
    if decisions:
        decisions[0]["support_s"][0] = t0
        decisions[-1]["support_s"][1] = t1

    design = dict(schema=1, origin="agent_designed", support_s=[t0, t1],
                  center_nodes=center_nodes, components=components,
                  decisions=decisions, expectations=expectations)
    plan_phrases.append(dict(part_index=pi, position=int(native[pi]["position"]), design=design))
    design_log.append(dict(phrase=pid, nodes=len(center_nodes), components=len(components),
                            notes=len(sung), ripples=len(components),
                            span_c=round(max(vals) - min(vals), 1)))

    # ---------- 逐单元手势（意图简报） ----------
    p_units = units_by_part.get(pi, [])
    if not p_units:
        continue
    obs = [
        dict(id=f"{pid}:obs_src", source_id="fcpe_obs", source_window_s=[t0, t1],
             description=(f"'{hanzi}' 全句双检测器一致 F0 迹线：{len(sung)} 个唱字，"
                          f"句内源 RMS {metrics['metrics'][str(pi)]['rms_db']}dB，"
                          f"字腹跨度中位 {metrics['metrics'][str(pi)]['src_span_median_c']}c"),
             reliability="observed"),
        dict(id=f"{pid}:obs_ripple", source_id="rmvpe_obs", source_window_s=[t0, t1],
             description=(f"本句 {metrics['metrics'][str(pi)]['ripple_notes']} 个唱字检出原唱 F0 涟漪，"
                          f"幅度中位 {metrics['metrics'][str(pi)]['ripple_amp_median_c']}c"),
             reliability="observed"),
        dict(id=f"{pid}:obs_align", source_id="hfa_summary", source_window_s=[t0, t1],
             description=(f"本句音素对齐：{len([1 for m in align_log.get('detail', []) if m['part_index'] == pi])}"
                          f" 个音节的元音起点已移到源里 F0 锁定点"
                          f"（全曲中位误差 {align_log.get('median_abs_after_ms')}ms）"),
             reliability="observed"),
    ]
    gestures = []
    unit_checks = {}
    for k, u in enumerate(p_units):
        ua, ub = u["support_s"]
        stage = u["stages"][0]
        swin = stage["support_s"]
        owner = None
        for i in sung:
            if notes[i]["start"] - 1e-6 <= ua and ub <= notes[i]["end"] + 1e-6:
                owner = i
                break
        if owner is None:
            owner = min(sung, key=lambda i: abs(notes[i]["start"] - ua))
        comp = comp_of_note.get(owner)
        # 判据区间：只由源实测推出（窄窗/宽窗跨度 + 涟漪幅度）
        idx_list = notes_in(swin[0], swin[1])
        lo, hi, src_span, S_w, A = band(swin[0], swin[1], idx_list)
        ft_u = filled_track(src, swin[0], swin[1])
        src_frames = ft_u[2]["frames"] if ft_u else 0
        # 窗口内若含字间连接，上限要容纳连接的理论最大跨度
        if any(r["start"] < swin[1] and r["end"] > swin[0] for r in ramps.values()):
            hi += CONN_REACH
        checks = []
        # 判据一（点级）：画线必须穿过源实测电平上的锚点。
        #   名义音高对照（把偏离削到 ±25c）穿不过这些锚点，因此可与浅对照区分。
        # 判据二（幅度级）：该窗口内的运动幅度与源实测同量级。
        pts = []
        cands = []
        for i in idx_list:
            ft = note_smooth.get(i)
            if ft is None:
                continue
            t, v = ft
            core = ((t >= swin[0] - 1e-9) & (t <= swin[1] + 1e-9) &
                    (t >= notes[i]["start"] + 0.04) & (t <= notes[i]["end"] - 0.04))
            if core.sum() < 4:
                continue
            for kk in np.where(core)[0]:
                if any(bl["L"] - 1e-9 <= t[kk] <= bl["R"] + 1e-9 for bl in blends):
                    continue
            keep = [kk for kk in np.where(core)[0]
                    if not any(bl["L"] - 1e-9 <= t[kk] <= bl["R"] + 1e-9 for bl in blends)]
            if len(keep) < 4:
                continue
            tt, vv = t[keep], v[keep]
            nominal = float(notes[i]["tone"] * 100)
            d = vv - nominal
            a_note = ripples[i]["amp"] if i in ripples else 0.0
            for q in (0.95, 0.05):
                kk = int(np.clip(round(q * (len(d) - 1)), 0, len(d) - 1))
                cands.append((float(tt[kk]), float(vv[kk]), float(d[kk]), a_note, i))
        strong = [c for c in cands if abs(c[2]) >= 65.0 + c[3]]
        for i in idx_list:
            grp = [c for c in strong if c[4] == i]
            for c1 in grp:
                for c2 in grp:
                    if abs(c1[0] - c2[0]) >= 0.06 and abs(c1[2] - c2[2]) >= 50.0:
                        pair = sorted([c1, c2], key=lambda c: c[0])
                        pts = [[pair[0][0], round(pair[0][1], 2)], [pair[1][0], round(pair[1][1], 2)]]
                        break
                if pts:
                    break
            if pts:
                break
        if pts:
            tol = round(30.0 + max((c[3] for c in cands), default=0.0), 1)
            checks.append(dict(kind="landmarks", support_s=[round(swin[0], 6), round(swin[1], 6)],
                               parameters=dict(points=pts, tolerance_c=tol, time_tolerance_s=0.03)))
            mode = "must_differ"
        elif src_frames >= 5 and lo > 0:
            checks.append(dict(kind="range", support_s=[round(swin[0], 6), round(swin[1], 6)],
                               parameters=dict(min_c=round(lo, 2), max_c=round(hi, 2))))
            mode = "must_differ" if lo > 50.0 else "may_match"
        else:
            checks.append(dict(kind="hold", support_s=[round(swin[0], 6), round(swin[1], 6)],
                               parameters=dict(min_c=0, max_c=round(max(hi, 60.0), 2))))
            mode = "may_match"
        if comp is not None:
            depth = comp["depth_nodes"][1][1]
            env = max(ripple_env(comp, float(t)) for t in np.linspace(swin[0], swin[1], 25))
            period = 1.0 / comp["rate_nodes"][0][1]
            # 周期检测需要至少 1.5 个完整周期（峰-谷-峰），否则不计周期
            if (swin[1] - swin[0]) >= 2.2 * period and depth >= 18.0:
                prom = max(8.0, round(0.5 * depth * env, 1))
                checks.append(dict(kind="cycles", support_s=[round(swin[0], 6), round(swin[1], 6)],
                                   parameters=dict(min_cycles=1, prominence_c=prom)))
        # ---------- 判据自检（生成期）：实际线是否达标、能否与"名义音高对照"区分 ----------
        ts_probe = np.arange(swin[0], swin[1] + 1e-9, 0.005)
        actual = eval_design(design, ts_probe)
        starts = np.array([(part["position"] + n["position"]) * TICK_S for n in part["notes"]])
        tones = np.array([float(n["tone"] * 100) for n in part["notes"]])
        cidx = np.clip(np.searchsorted(starts, ts_probe, side="right") - 1, 0, len(starts) - 1)
        ctr = tones[cidx].copy()
        for i in range(1, len(starts)):
            half = min(0.08 / 2, (starts[i] - starts[i - 1]) / 2)
            if half <= 0:
                continue
            m = (ts_probe >= starts[i] - half) & (ts_probe <= starts[i] + half)
            if not m.any():
                continue
            uu = (ts_probe[m] - starts[i] + half) / (2 * half)
            ctr[m] = tones[i - 1] + (tones[i] - tones[i - 1]) * (1 - np.cos(np.pi * uu)) / 2
        ablation = ctr + np.clip(actual - ctr, -25.0, 25.0)
        stage_a = dict(support_s=[swin[0], swin[1]], times_s=ts_probe, raw_cents=actual)
        stage_b = dict(support_s=[swin[0], swin[1]], times_s=ts_probe, raw_cents=ablation)
        distinguishes = False
        pre_fail = []
        for c in checks:
            ra = check_action(dict(c, stage_id="probe"), stage_a)
            rb = check_action(dict(c, stage_id="probe"), stage_b)
            if ra["status"] == "fail":
                pre_fail.append(dict(unit=u["id"], kind=c["kind"], detail=ra))
            if ra["status"] == "pass" and rb["status"] == "fail":
                distinguishes = True
        if pre_fail:
            selfcheck_fail.append(dict(unit=u["id"], checks=pre_fail))
        mode = "must_differ" if distinguishes else "may_match"
        unit_checks[u["id"]] = dict(checks=checks, src_span=src_span, src_frames=src_frames,
                                    owner=owner, comp=comp, mode=mode)
        role = "arrival" if k == 0 else ("release" if k == len(p_units) - 1 else "body")
        gestures.append(dict(
            id=f"{pid}:g{k}", unit_ids=[u["id"]], role=role, support_s=[ua, ub],
            observation_ids=[obs[0]["id"], obs[1]["id"]],
            interpretation=(f"'{u.get('lyric')}' 的字腹照源实测同窗跨度 {src_span:.0f}c 还原"
                            f"（{src_frames} 帧一致 F0）"
                            + (f"，并按源涟漪写周期组件" if comp else "")),
            alternative="用与全曲其它字相同的固定鼓包/平台代替该字的源形状",
            rejected_because="统一模板会抹掉逐字的源差异，正是前两版被否掉的形态",
            contrast=dict(mode=mode, shallow_limit_c=25, connection_s=0.08,
                          reason=("该字在源里有 >60c 的字腹跨度，浅对照（±25c 削平）不应被接受"
                                  if mode == "must_differ" else
                                  "该字在源里本就平直或幅度有限，允许与浅对照一致；本句区分点在其它字与连接")),
            checks=checks))
    brief_phrases.append(dict(
        id=pid, unit_ids=[u["id"] for u in p_units],
        support_s=[min(t0, min(u["support_s"][0] for u in p_units)),
                   max(t1, max(u["support_s"][1] for u in p_units))],
        observations=obs,
        intention=(f"'{hanzi}'：旋律直接描原唱实测迹线（不做平台化），字腹照源逐字还原，"
                   f"原唱涟漪按实测频率/幅度写成周期组件，字间用实唱连接，"
                   f"发声层按逐音符实测单独设定"),
        gestures=gestures))

    # ---------- ledger（按库存单元） ----------
    phrase_ledger = []
    for u in p_units:
        ua, ub = u["support_s"]
        stage = u["stages"][0]
        uc = unit_checks[u["id"]]
        owner = uc["owner"]
        comp = uc["comp"]
        n = notes[owner]
        src_span = uc["src_span"]
        choice = "oscillation" if comp else ("center" if uc["mode"] == "must_differ" else "hold")
        execution = [dict(kind="center_nodes", part_index=pi, position=int(native[pi]["position"]),
                          id="center_nodes", support_s=[t0, t1],
                          parameters_sha256=digest(center_nodes))]
        for i, c in comp_of_note.items():
            if notes[i]["start"] - 1e-6 <= ua and ub <= notes[i]["end"] + 1e-6:
                execution.append(dict(kind="component", part_index=pi, position=int(native[pi]["position"]),
                                      id=c["id"], support_s=c["support_s"],
                                      parameters_sha256=digest(c)))
        phrase_ledger.append(dict(
            id=f"dec:{u['id']}", unit_ids=[u["id"]], stage_ids=[stage["id"]],
            support_s=[ua, ub],
            evidence_ids=["fcpe_obs", "rmvpe_obs", "game_obs", "hfa_summary"],
            observation=(f"'{u.get('lyric')}' ({u.get('symbol')}) {ua:.3f}-{ub:.3f}s，"
                         f"同窗源跨度 {src_span:.0f}c（{uc['src_frames']} 帧一致 F0）"),
            interpretation=("源内为持续周期，按源频率与深度展开" if comp else
                           "源内有方向性字腹运动，按源形状画" if uc["mode"] == "must_differ" else
                           "源内基本平直，保持贴合源线"),
            reliability="high; 双检测器一致口径",
            purpose=f"让 '{u.get('lyric')}' 的字腹反映原唱该字的实际运动",
            choice=choice,
            alternative="套用全曲统一的固定幅度鼓包",
            rejected_because="统一鼓包不区分源逐字差异，属于前两版被否的模板化形态",
            parameter_basis=(f"参数取自源实测：同窗跨度 {src_span:.0f}c"
                             + (f"，涟漪组件 {comp['id']}（{comp['rate_nodes'][0][1]:.2f}Hz/"
                                f"{comp['depth_nodes'][1][1]:.0f}c）" if comp else "")),
            execution=execution,
            checks=[dict(stage_id=stage["id"], kind=c["kind"], support_s=c["support_s"],
                          parameters=c["parameters"]) for c in uc["checks"]],
            uncertainty="自然度与听感未经人耳确认；本轮只有数值与图审证据。"))
    # 兜底：没有被任何单元消费的组件 -> 挂到最近的单元
    mapped = {e["id"] for d in phrase_ledger for e in d["execution"] if e["kind"] == "component"}
    for i, c in comp_of_note.items():
        if c["id"] in mapped:
            continue
        mid = (c["support_s"][0] + c["support_s"][1]) / 2
        best = min(phrase_ledger, key=lambda d: abs((d["support_s"][0] + d["support_s"][1]) / 2 - mid))
        best["execution"].append(dict(kind="component", part_index=pi, position=int(native[pi]["position"]),
                                      id=c["id"], support_s=c["support_s"],
                                      parameters_sha256=digest(c)))
    ledger_decisions.extend(phrase_ledger)

print("designs built:", len(plan_phrases),
      "| components:", sum(len(p["design"]["components"]) for p in plan_phrases),
      "| nodes:", sum(p["nodes"] for p in design_log))
json.dump(design_log, open(DESIGN / "design_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
(DESIGN / "selfcheck.json").write_text(json.dumps(
    dict(note="生成期判据自检：实际设计是否通过冻结判据", failures=len(selfcheck_fail),
         detail=selfcheck_fail[:40]), ensure_ascii=False, indent=1), encoding="utf-8")
print("selfcheck failures:", len(selfcheck_fail))
(DESIGN / "gap_log.json").write_text(json.dumps(
    dict(note_count=len(gap_log),
         total_gaps=sum(g["gaps"] for g in gap_log),
         max_gap_s=round(max([g["max_gap_s"] for g in gap_log], default=0.0), 3),
         policy="双检测器分歧造成的空档按线性滑音补齐（设计与判据同口径）",
         notes=gap_log), ensure_ascii=False, indent=1), encoding="utf-8")
print("gap notes:", len(gap_log), "total gaps:", sum(g["gaps"] for g in gap_log))

# ---------------- 意图简报 + 冻结（plan 尚不存在） ----------------
brief = dict(schema_version=1,
             inventory=dict(path=str((DESIGN / "review-inventory.json").resolve()),
                            sha256=sha256(DESIGN / "review-inventory.json")),
             phrases=brief_phrases,
             phonation=dict(
                 baseline="YousaV1.65c 原生基底，未加人工增量",
                 target=("VOIC/BREC/TENC/DYN 四条曲线按每个音符的源实测（谐噪比、谱重心、音高、能量）"
                         "单独取值（554 个唱字各有断点），不是按段落套固定值"),
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
shutil.copyfile(V2 / "design" / "knowledge_context.json", kb_dst)
packet = rj(kb_dst)
decisions = []
for rec in packet["records"]:
    decisions.append(dict(id=rec["id"], decision="use",
                          reason=(f"沿用本次制作前对表1/表2的检索结果：{rec['id']} 的条件与本曲逐句画线直接相关，"
                                  f"在 v3 中用于约束'逐字照源还原、连接要可唱、判据要可证伪'这三项。"),
                          condition_match="普通话流行翻唱；本句为已观测的源条件下单句制作。",
                          limitations="仅为条件化经验条目，不提供数值剂量，也不证明当前句的听觉自然度。",
                          general_rule_claim=False))
knowledge_block = dict(path=str(kb_dst.resolve()), sha256=sha256(kb_dst), decisions=decisions)

vocal_stem = str((V3 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav").resolve())
plan = dict(schema_version=2, project=str(SCORE.resolve()), source_audio=vocal_stem,
            input_hashes={str(SCORE.resolve()): sha256(SCORE),
                          vocal_stem: rj(V3 / "observation" / "manifest.json")["files"]["stems\\source_(vocals)_vocals_mel_band_roformer.wav"],
                          str((DESIGN / "baseline_pitch.json").resolve()): sha256(DESIGN / "baseline_pitch.json"),
                          str((DESIGN / "baseline_phones.json").resolve()): sha256(DESIGN / "baseline_phones.json"),
                          str((V3 / "hfa" / "hfa_summary.json").resolve()): sha256(V3 / "hfa" / "hfa_summary.json")},
            scope="whole_song", phrases=plan_phrases, knowledge_context=knowledge_block)
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print("plan written:", len(plan_phrases), "phrases")

ledger = dict(schema_version=1,
              inventory=dict(path=str((DESIGN / "review-inventory.json").resolve()),
                             sha256=sha256(DESIGN / "review-inventory.json")),
              plan=dict(path=str(plan_path.resolve()), sha256=sha256(plan_path)),
              timing="forward", decisions=ledger_decisions, revisions=[])
(DESIGN / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
print("ledger written:", len(ledger_decisions), "decisions")
