"""逐句审查 年轮 from-scratch 设计：源事实 vs 设计事实。只读审计。

只读当前 run 的实际文件，不改工程/音频/计划。
输出: songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028/reports/audit_nianlun_phrases.json + 终端表
"""
import json
import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")

RUN = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
OUT = pathlib.Path(r"E:\project\agent2utau\scratch\audit_nianlun_phrases.json")
TICK_MS = 1.0416666666666667  # 480 ticks/beat @120bpm


def rj(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


plan = rj(RUN / "design/plan.json")
ledger = rj(RUN / "design/ledger.json")
intent = rj(RUN / "design/musical_intent.json")
inventory = rj(RUN / "design/inventory.json")
hfa = rj(RUN / "hfa/hfa_summary.json")
game = rj(RUN / "observation/game.json")
pitch = rj(RUN / "compiled/pitch.json")
project = yaml.safe_load((RUN / "compiled/project.ustx").read_text(encoding="utf-8"))

# ---------- 源 F0 (FCPE) ----------
z = np.load(RUN / "observation/fcpe.npz", allow_pickle=True)
f0 = z["f0_hz"].astype(np.float64)
voiced = z["voiced"].astype(bool)
times = z["times"].astype(np.float64)
with np.errstate(divide="ignore", invalid="ignore"):
    cents = np.where(f0 > 0, 1200.0 * np.log2(f0 / 440.0), np.nan)
# FCPE 以 A4(440Hz)=0；USTX 绝对音高以 C-1=0（MIDI n -> n*100）。A4=6900
cents = cents + 6900.0
src_ok = voiced & np.isfinite(cents)

# 顺序映射: plan.phrases[i] <-> voice_parts[i] <-> pitch.phrases[i]
parts = {}
final_by_pos = {}
for i, vp in enumerate(project["voice_parts"]):
    parts[i] = vp
for i, p_ in enumerate(pitch["phrases"]):
    final_by_pos[i] = p_
units = inventory["units"]
units_by_part = defaultdict(list)
for u in units:
    units_by_part[u["part_index"]].append(u)
hfa_by_phrase = {p["phrase_id"]: p for p in hfa["phrases"]}
decisions = {d["id"]: d for d in ledger["decisions"]}
game_notes = game["notes"]


def src_win(a, b):
    m = src_ok & (times >= a) & (times < b)
    if m.sum() < 3:
        return None
    c = cents[m]
    return dict(n=int(m.sum()), median=float(np.median(c)), span=float(c.max() - c.min()))


def des_win(ft, fc, a, b):
    m = (ft >= a) & (ft < b)
    if m.sum() < 2:
        return None
    v = fc[m]
    return dict(n=int(m.sum()), median=float(np.median(v)), span=float(v.max() - v.min()))


phrases = []
for ph in plan["phrases"]:
    pi, pos = ph["part_index"], ph["position"]
    d = ph["design"]
    a, b = d["support_s"]
    fp = final_by_pos.get(pi)
    ft = np.array(fp["times_ms"]) / 1000.0 if fp else np.array([])
    fc = np.array(fp["final_cents"]) if fp else np.array([])
    vp = parts.get(pi, {})
    notes = vp.get("notes", [])
    part_pos = vp.get("position", 0)

    nodes = np.asarray(d["center_nodes"], float)
    zero_slope = int(np.count_nonzero(nodes[:, 2] == 0)) if len(nodes) else 0
    comps = d.get("components", [])
    fam = Counter(c["family"] for c in comps)
    peaks = [c.get("peak_c") for c in comps if c.get("family") == "finite_return"]
    osc = [c for c in comps if c.get("family") == "oscillation"]

    # 每音符: 设计线 vs 源线
    note_rows = []
    for n in notes:
        ns = (part_pos + n["position"]) * TICK_MS / 1000.0
        ne = (part_pos + n["position"] + n["duration"]) * TICK_MS / 1000.0
        sv = src_win(ns, ne)
        dv = des_win(ft, fc, ns, ne)
        if not dv:
            continue
        note_rows.append(dict(
            lyric=n["lyric"], tone=n.get("tone"),
            dur_s=round(n["duration"] * TICK_MS / 1000.0, 3),
            des_median=round(dv["median"], 1), des_span=round(dv["span"], 1),
            src_median=round(sv["median"], 1) if sv else None,
            src_span=round(sv["span"], 1) if sv else None,
            dev_c=round(dv["median"] - sv["median"], 1) if sv else None,
        ))

    # 每元音单元: 源字腹跨度 vs 设计字腹跨度
    unit_rows = []
    for u in units_by_part[pi]:
        ua, ub = u["support_s"]
        sv = src_win(ua, ub)
        dv = des_win(ft, fc, ua, ub)
        dec = decisions.get(f"dec:{u['id']}")
        unit_rows.append(dict(
            id=u["id"], lyric=u.get("lyric"), sym=u.get("symbol"),
            support_s=[round(ua, 3), round(ub, 3)],
            src_span=round(sv["span"], 1) if sv else None,
            des_span=round(dv["span"], 1) if dv else None,
            choice=(dec or {}).get("choice"),
            check_kinds=[c["kind"] for c in (dec or {}).get("checks", [])],
            n_comp=len([c for c in comps if ua - 1e-6 <= c["support_s"][0] and c["support_s"][1] <= ub + 1e-6]),
        ))

    singing = [r for r in note_rows if r["lyric"] not in ("SP", "AP", "+")]
    devs = [abs(r["dev_c"]) for r in singing if r["dev_c"] is not None]

    # 字腹对比: 源元音跨度 vs 设计元音跨度
    flattened = [u for u in unit_rows
                 if u["src_span"] and u["des_span"] is not None
                 and u["src_span"] > 80 and u["des_span"] < 0.5 * u["src_span"]]
    near_flat = [u for u in unit_rows
                 if u["des_span"] is not None and u["des_span"] < 20]
    des_spans = [u["des_span"] for u in unit_rows if u["des_span"] is not None]

    # 呼吸: 工程 SP/AP vs HFA SP/AP
    eng_breath = [n["lyric"] for n in notes if n["lyric"] in ("SP", "AP")]
    hfa_p = hfa_by_phrase.get(f"p{pi:02d}", {})
    hfa_breath = [w["mark"] for w in hfa_p.get("words", []) if w["mark"] in ("SP", "AP")]

    # 中心节点位置: 落在音符边界(平台) 还是音符内部
    note_bounds = set()
    for n in notes:
        note_bounds.add(round((part_pos + n["position"]) * TICK_MS / 1000.0, 4))
    inside = sum(1 for t, _, _ in nodes if round(float(t), 4) not in note_bounds)

    phrases.append(dict(
        part_index=pi, position=pos, support_s=[a, b],
        n_nodes=int(len(nodes)), zero_slope=zero_slope,
        nodes_inside_notes=int(inside),
        n_components=len(comps), families=dict(fam),
        peak_c_set=sorted({round(p, 1) for p in peaks}),
        n_osc=len(osc),
        n_notes=len(notes), n_singing=len(singing),
        eng_breath=eng_breath, hfa_breath=hfa_breath,
        n_flattened=len(flattened),
        flattened=[f'{u["id"]}/{u["lyric"]}' for u in flattened],
        n_nearflat=len(near_flat),
        des_span_median=round(float(np.median(des_spans)), 1) if des_spans else None,
        notes=note_rows, units=unit_rows,
        src=src_win(a, b), des=des_win(ft, fc, a, b),
        dev_mean=round(float(np.mean(devs)), 1) if devs else None,
        dev_max=round(float(np.max(devs)), 1) if devs else None,
        dev_over50=int(sum(1 for d_ in devs if d_ > 50)),
        dev_over100=int(sum(1 for d_ in devs if d_ > 100)),
        hfa_marks=[w["mark"] for w in hfa_p.get("words", [])][:4],
    ))

# ---------- 全曲汇总 ----------
all_units = [u for p in phrases for u in p["units"]]
all_notes = [n for p in phrases for n in p["notes"]]
sing = [n for n in all_notes if n["lyric"] not in ("SP", "AP", "+")]
devs = [n["dev_c"] for n in sing if n["dev_c"] is not None]
span_ratio = [(u["des_span"] / u["src_span"]) for u in all_units
              if u["src_span"] and u["des_span"] is not None and u["src_span"] > 20]

choice_counter = Counter(u["choice"] for u in all_units)
check_kind_counter = Counter(k for u in all_units for k in u["check_kinds"])
comp_peak_counter = Counter(p for p in phrases for p in p["peak_c_set"])

# 结构重复签名 (与 evaluation/musical_review.py 同口径)
sig = defaultdict(list)
for p in phrases:
    for c in p["peak_c_set"]:
        pass
for ph in plan["phrases"]:
    d = ph["design"]
    a0, b0 = d["support_s"]
    for c in d.get("components", []):
        a, b = c["support_s"]
        if c["family"] == "finite_return":
            key = ("finite_return", round((c["peak_s"] - a) / (b - a) * 10), int(np.sign(c["peak_c"])))
        elif c["family"] == "oscillation":
            key = ("oscillation", round((c["attack_end_s"] - a) / (b - a) * 10),
                   round((c["release_start_s"] - a) / (b - a) * 10))
        else:
            key = (c["family"], "unsupported")
        sig[key].append(f"p{ph['part_index']:02d}:{c['id']}")
repeated = {str(k): (len(v), v[:4]) for k, v in sig.items() if len(v) > 1}

# 发声/动态控制统计
expr_counts = Counter()
nonempty_phoneme_expr = 0
for vp in project["voice_parts"]:
    for n in vp["notes"]:
        pe = n.get("phoneme_expressions") or []
        for e in pe:
            expr_counts[e.get("key") or e.get("name")] += 1
        if pe:
            nonempty_phoneme_expr += 1
        for e in (n.get("phoneme_overrides") or []):
            expr_counts["override:" + str(e.get("key"))] += 1
track_expr = [(t.get("track_name"), t.get("track_expressions")) for t in project["tracks"]]
proj_expressions = {k: v for k, v in (project.get("expressions") or {}).items()}

# 歌词/呼吸
lyric_counter = Counter(n["lyric"] for n in all_notes)

summary = dict(
    n_phrases=len(phrases),
    n_units=len(all_units),
    n_notes=len(all_notes),
    n_singing=len(sing),
    dev_abs_median=round(float(np.median([abs(d) for d in devs])), 1) if devs else None,
    dev_abs_p90=round(float(np.percentile([abs(d) for d in devs], 90)), 1) if devs else None,
    dev_over50=int(sum(1 for d in devs if abs(d) > 50)),
    dev_over100=int(sum(1 for d in devs if abs(d) > 100)),
    total_singing=len(sing),
    span_ratio_median=round(float(np.median(span_ratio)), 3) if span_ratio else None,
    span_ratio_lt_0_5=int(sum(1 for r in span_ratio if r < 0.5)),
    span_ratio_n=len(span_ratio),
    n_flattened_total=sum(p["n_flattened"] for p in phrases),
    n_nearflat_total=sum(p["n_nearflat"] for p in phrases),
    zero_slope_total=sum(p["zero_slope"] for p in phrases),
    nodes_total=sum(p["n_nodes"] for p in phrases),
    nodes_inside_notes_total=sum(p["nodes_inside_notes"] for p in phrases),
    eng_breath_total=sum(len(p["eng_breath"]) for p in phrases),
    hfa_breath_total=sum(len(p["hfa_breath"]) for p in phrases),
    choice_counter=dict(choice_counter),
    check_kind_counter=dict(check_kind_counter),
    comp_peak_values=dict(comp_peak_counter),
    repeated_signatures=repeated,
    phoneme_expression_notes=nonempty_phoneme_expr,
    phoneme_expression_keys=dict(expr_counts),
    track_expressions=track_expr,
    project_expressions=list(proj_expressions.keys()),
    lyric_counter={k: v for k, v in lyric_counter.most_common(12)},
)

json.dump(dict(summary=summary, phrases=phrases), open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("== 全曲汇总 ==")
print(json.dumps(summary, ensure_ascii=False, indent=1)[:4000])
print("\n逐句表: part | 节点(z=零斜率/内=音符内) | 组件 | 唱字 | dev均值/最大 >50/>100 | 源跨度/设计跨度 | 字腹压平 | 中位字腹跨度 | 工程呼吸/HFA")
for p in phrases:
    s = p["src"] or {}
    dd = p["des"] or {}
    print(f"p{p['part_index']:02d} {p['support_s'][0]:6.1f}-{p['support_s'][1]:6.1f} | "
          f"n{p['n_nodes']:3d} z{p['zero_slope']:3d} in{p['nodes_inside_notes']:3d} | "
          f"c{p['n_components']:3d} | s{p['n_singing']:3d} | "
          f"{str(p['dev_mean']):>7s}/{str(p['dev_max']):>7s} {p['dev_over50']:3d}/{p['dev_over100']:3d} | "
          f"{str(round(s.get('span', 0), 0)):>6s}/{str(round(dd.get('span', 0), 0)):>6s} | "
          f"flat{p['n_flattened']:3d} | {str(p['des_span_median']):>6s} | "
          f"{','.join(p['eng_breath']) or '-':>7s}/{','.join(p['hfa_breath']) or '-'}")
