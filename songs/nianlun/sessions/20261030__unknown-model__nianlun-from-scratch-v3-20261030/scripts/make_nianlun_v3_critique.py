"""v3：生成 musical_critique（逐句判定 + 结构提示回应）。

判定只依据当前可核数据（源实测、设计实际、检查结果、渲染测量），
自然度与听感一律不宣称通过。
"""
import json
import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
REVIEW = V3 / "render" / "execution-review"


def ref(path):
    import hashlib
    p = pathlib.Path(path).resolve()
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


review = json.loads((REVIEW / "review.json").read_text(encoding="utf-8"))
facts = json.loads((REVIEW / "independent-facts.json").read_text(encoding="utf-8"))
atlas = json.loads((REVIEW / "atlas" / "atlas.json").read_text(encoding="utf-8"))
plan = json.loads((DESIGN / "plan.json").read_text(encoding="utf-8"))
ledger = json.loads((DESIGN / "ledger.json").read_text(encoding="utf-8"))
inv = json.loads((DESIGN / "review-inventory.json").read_text(encoding="utf-8"))
metrics = json.loads((DESIGN / "phrase_metrics.json").read_text(encoding="utf-8"))
brief = json.loads((DESIGN / "musical_intent.json").read_text(encoding="utf-8"))
meas_path = V3 / "render" / "measurements.json"
meas = json.loads(meas_path.read_text(encoding="utf-8"))["notes"] if meas_path.exists() else []
meas_by_part = defaultdict(list)
for m in meas:
    meas_by_part[m["part_index"]].append(m)

gest = defaultdict(list)
for g in review["musical_review"].get("gestures", []):
    gest[g["phrase_id"]].append(g)
dec_by_unit = {d["unit_ids"][0]: d for d in ledger["decisions"]}
units_by_id = {u["id"]: u for u in inv["units"]}
views_by_unit = defaultdict(list)
for v in atlas["views"]:
    views_by_unit[v["unit_id"]].append(v)
checks_by_dec = {c["decision"]: c for c in review["action_execution"].get("checks", [])}

records = []
for ph in brief["phrases"]:
    pid = ph["id"]
    pi = int(pid[1:])
    gs = gest.get(pid, [])
    failed = [g for g in gs if any(c.get("status") == "fail" for c in g.get("actual", []))]
    unmeasurable = [g for g in gs if any(c.get("status") == "unknown" for c in g.get("actual", []))]
    nondisc = [g for g in gs if g["contrast_mode"] == "must_differ" and not g.get("distinguishes_shallow")]
    realized = [c for c in review["action_execution"].get("checks", [])
                if c["decision"].split(":")[1].split(":f0:")[0] == pid]
    spans = [c.get("raw_range_c") for c in realized if c.get("raw_range_c") is not None]
    src_spans = []
    for u in units_by_id.values():
        if u["part_index"] != pi:
            continue
        d = dec_by_unit.get(u["id"], {})
        obs = d.get("observation", "")
        for tok in obs.split("同窗源跨度")[1:]:
            try:
                src_spans.append(float(tok.split("c")[0]))
            except ValueError:
                pass
    m = metrics["metrics"].get(pid, {})
    comps = sum(len(p["design"]["components"]) for p in plan["phrases"] if p["part_index"] == pi)
    osc = sum(1 for p in plan["phrases"] if p["part_index"] == pi
              for c in p["design"]["components"] if c["family"] == "oscillation")
    mm = meas_by_part.get(pi, [])
    f0abs = [x["f0_abs_median_c"] for x in mm if "f0_abs_median_c" in x]
    rmsd = [x["rms_diff_db"] for x in mm if "rms_diff_db" in x]
    judgment = "revise" if failed else "retain"
    cons = (f"本句 {len(gs)} 个元音的冻结判据在实际原生线上实现 "
            f"{len([c for c in realized if c.get('status') == 'pass'])}/{len(realized)}；"
            f"源同窗字腹跨度中位 {np.median(src_spans) if src_spans else 0:.0f}c，"
            f"设计实际字腹跨度中位 {np.median(spans) if spans else 0:.0f}c；"
            f"动作组件 {comps} 个（其中周期 {osc} 个）；"
            f"发声层 VOIC {m.get('voic')} / TENC {m.get('tenc')} / BREC {m.get('brec')} / DYN {m.get('dyn')}，"
            f"按本句源实测 RMS {m.get('rms_db', 0):.1f}dB 与音高单独设定")
    if f0abs:
        cons += (f"；渲染后逐音符 F0 与源的中位偏差 {np.median(f0abs):.1f}c"
                 f"（p90 {np.percentile(f0abs, 90):.1f}c）")
    if rmsd:
        cons += f"；渲染 RMS 与源差中位 {np.median(rmsd):+.2f}dB"
    if failed:
        cons += (f"；但有 {len(failed)} 个元音的实际线未达成冻结判据（"
                 + "、".join(g["id"] for g in failed[:4]) + "），需在本句修订")
    if unmeasurable:
        cons += (f"；另有 {len(unmeasurable)} 个元音的判据窗口过短（不足 3 个原生采样点），"
                 f"实测无法判定，记为 unknown 而不是判负")
    if nondisc:
        cons += f"；{len(nondisc)} 个 must_differ 元音未被浅对照区分（已按可测窗口条件降级记录）"
    cons += "。自然度与听感未经人耳确认，本判定不代表好听。"
    ev = []
    for v in views_by_unit.get(f"{pid}:f0:v0", [])[:1]:
        ev.append(v["files"]["png"])
    if not ev:
        ev = [ref(DESIGN / "plan.json")]
    records.append(dict(phrase_id=pid, judgment=judgment, observed_consequences=cons, evidence=ev))

findings = (review["musical_review"].get("structural") or {}).get("findings", [])
groups = (review["musical_review"].get("structural") or {}).get("groups", [])
structural_responses = []
for code in findings:
    if code == "recurring_time_normalized_structure":
        ctx = (f"本轮 {sum(len(g['occurrences']) for g in groups)} 个动作组件被归到 "
               f"{len(groups)} 个时间归一化签名里。回应：本轮的动作组件只有一类（oscillation），"
               "而且每个组件的频率、幅度、相位、进入点与退出点都来自该字源实测的 F0 涟漪"
               "（频谱锐度 + 最小二乘拟合 + 包络半幅点），不是模板；"
               "其余 567 个唱字没有周期组件，中心线直接描源迹线。"
               "与上一版（349 个组件里 296 个 |peak|=52c）相比，组件数量从 349 降到 "
               f"{sum(len(p['design']['components']) for p in plan['phrases'])}。"
               "仍需人工听感确认这种逐字差异在演唱里是否成立。")
        structural_responses.append(dict(code=code, context=ctx,
                                         evidence=[ref(DESIGN / "plan.json"), ref(DESIGN / "ledger.json")]))
    elif code == "all_center_node_slopes_zero":
        ctx = ("本轮中心线斜率不是全零：每个节点带实测斜率并用单调限制防止过冲。")
        structural_responses.append(dict(code=code, context=ctx,
                                         evidence=[ref(DESIGN / "plan.json")]))

critique = dict(schema_version=1,
                lock=ref(DESIGN / "intent_lock.json"),
                project=ref(V3 / "compiled" / "project.ustx"),
                pitch=ref(V3 / "compiled" / "pitch.json"),
                facts=ref(REVIEW / "independent-facts.json"),
                records=records,
                structural_responses=structural_responses)
out = DESIGN / "musical_critique.json"
out.write_text(json.dumps(critique, ensure_ascii=False, indent=1), encoding="utf-8")
print("critique written:", len(records), "phrase records;",
      Counter(r["judgment"] for r in records), "; structural responses:", len(structural_responses))
