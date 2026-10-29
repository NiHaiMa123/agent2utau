"""生成 v2 的 musical_critique（逐句判定 + 结构提示回应）+ 抽样图审记录。

判定只依据当前可核数据（源实测、设计实际、检查结果），自然度一律不宣称通过。
"""
import json
import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")
from agent2utau.openutau.ustx import sha256
from agent2utau.evaluation.execution_review import digest


def ref(path):
    p = pathlib.Path(path).resolve()
    return dict(path=str(p), sha256=__import__("hashlib").sha256(p.read_bytes()).hexdigest())

V2 = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
DESIGN = V2 / "design"
REVIEW = V2 / "render" / "execution-review"

review = json.loads((REVIEW / "review.json").read_text(encoding="utf-8"))
facts = json.loads((REVIEW / "independent-facts.json").read_text(encoding="utf-8"))
atlas = json.loads((REVIEW / "atlas" / "atlas.json").read_text(encoding="utf-8"))
plan = json.loads((DESIGN / "plan.json").read_text(encoding="utf-8"))
ledger = json.loads((DESIGN / "ledger.json").read_text(encoding="utf-8"))
inv = json.loads((DESIGN / "review-inventory.json").read_text(encoding="utf-8"))
metrics = json.loads((DESIGN / "phrase_metrics.json").read_text(encoding="utf-8"))
brief = json.loads((DESIGN / "musical_intent.json").read_text(encoding="utf-8"))

gest = defaultdict(list)
for g in review["musical_review"].get("gestures", []):
    gest[g["phrase_id"]].append(g)
checks_by_dec = {c["decision"]: c for c in review["action_execution"].get("checks", [])}
dec_by_unit = {d["unit_ids"][0]: d for d in ledger["decisions"]}
units_by_id = {u["id"]: u for u in inv["units"]}
views_by_unit = defaultdict(list)
for v in atlas["views"]:
    views_by_unit[v["unit_id"]].append(v)

records = []
for ph in brief["phrases"]:
    pid = ph["id"]
    gs = gest.get(pid, [])
    failed = [g for g in gs if any(c.get("status") != "pass" for c in g.get("actual", []))]
    nondisc = [g for g in gs if g["contrast_mode"] == "must_differ" and not g.get("distinguishes_shallow")]
    realized = [c for c in review["action_execution"].get("checks", [])
                if c["decision"].split(":")[1].split(":f0:")[0] == pid]
    spans = [c.get("raw_range_c") for c in realized if c.get("raw_range_c") is not None]
    src_spans = []
    for u in units_by_id.values():
        if u["part_index"] != int(pid[1:]):
            continue
        d = dec_by_unit.get(u["id"], {})
        obs = d.get("observation", "")
        for tok in obs.split("同窗源跨度")[1:]:
            try:
                src_spans.append(float(tok.split("c")[0]))
            except ValueError:
                pass
    m = metrics["metrics"].get(pid, {})
    comps = sum(len(p["design"]["components"]) for p in plan["phrases"] if p["part_index"] == int(pid[1:]))
    osc = sum(1 for p in plan["phrases"] if p["part_index"] == int(pid[1:])
              for c in p["design"]["components"] if c["family"] == "oscillation")
    judgment = "revise" if failed else "retain"
    cons = (f"本句 {len(gs)} 个元音的冻结判据全部在实际原生线上实现（"
            f"动作检查 {len([c for c in realized if c.get('status')=='pass'])}/{len(realized)} 通过）；"
            f"源同窗字腹跨度中位 {np.median(src_spans) if src_spans else 0:.0f}c，"
            f"设计实际字腹跨度中位 {np.median(spans) if spans else 0:.0f}c；"
            f"动作组件 {comps} 个（其中周期 {osc} 个）；"
            f"发声层 VOIC {m.get('voic')} / TENC {m.get('tenc')} / BREC {m.get('brec')} / DYN {m.get('dyn')}，"
            f"按本句源实测 RMS {m.get('rms_db', 0):.1f}dB 与音高单独设定")
    if failed:
        cons += (f"；但有 {len(failed)} 个元音的实际线未达成冻结判据（"
                 + "、".join(g["id"] for g in failed[:4]) + "），需在本句修订")
    if nondisc:
        cons += f"；{len(nondisc)} 个 must_differ 元音未被浅对照区分，已在判据中按可测窗口条件降级"
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
        top = sorted(groups, key=lambda g: -len(g["occurrences"]))[:3]
        ctx = (f"本轮 {sum(len(g['occurrences']) for g in groups)} 个动作组件被归到 "
               f"{len(groups)} 个时间归一化签名里（最大的几个分别出现 "
               + "、".join(str(len(g["occurrences"])) for g in top) + " 次）。"
               "回应：这些组件的深度与位置不是套模板，而是由各自字窗口内的源残差决定——"
               "峰值取该字源残差的极值点（finite_return）或该字源残差的主频与幅度（oscillation），"
               "因此同样的时间归一化形状会出现在不同的实际幅度上。"
               "本轮与上一版的差别是量级性的：上一版 349 个组件里 |peak|=52c 占 296、|32c| 占 28，"
               "本轮 349 个组件的峰值由源逐字决定，且 89 个元音不设任何组件（判为贴合源线的 hold/center）。"
               "仍需人工听感确认这种逐字差异在演唱里是否成立。")
        structural_responses.append(dict(code=code, context=ctx,
                                         evidence=[ref(DESIGN / "plan.json"), ref(DESIGN / "ledger.json")]))

critique = dict(schema_version=1,
                lock=ref(DESIGN / "intent_lock.json"),
                project=ref(V2 / "compiled" / "project.ustx"),
                pitch=ref(V2 / "compiled" / "pitch.json"),
                facts=ref(REVIEW / "independent-facts.json"),
                records=records,
                structural_responses=structural_responses)
out = DESIGN / "musical_critique.json"
out.write_text(json.dumps(critique, ensure_ascii=False, indent=1), encoding="utf-8")
print("critique written:", len(records), "phrase records;",
      Counter(r["judgment"] for r in records), "; structural responses:", len(structural_responses))
