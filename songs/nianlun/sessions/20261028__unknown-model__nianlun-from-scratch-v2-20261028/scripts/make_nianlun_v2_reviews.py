"""写入 v2 的逐元音审阅记录（抽样实图审）+ 生成 musical_critique，然后重跑复检。

records 只覆盖本次实际打开过图并写具体观察的单元；其余保持 pending（不冒充已审）。
"""
import json
import pathlib
import sys

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
ATLAS = REVIEW / "atlas"

facts = json.loads((REVIEW / "independent-facts.json").read_text(encoding="utf-8"))
atlas = json.loads((ATLAS / "atlas.json").read_text(encoding="utf-8"))
inv = json.loads((DESIGN / "review-inventory.json").read_text(encoding="utf-8"))
ledger = json.loads((DESIGN / "ledger.json").read_text(encoding="utf-8"))

views_by_unit = {}
for v in atlas["views"]:
    views_by_unit.setdefault(v["unit_id"], []).append(v)
facts_by_unit = {u["id"]: u for u in facts["units"]}

# 实际打开并观察过的单元（人工实图审记录：观察 -> 结论 -> 理由）
OBSERVED = json.loads(pathlib.Path(r"E:\project\agent2utau\scratch\v2_review_observations.json")
                      .read_text(encoding="utf-8"))

records = []
for unit_id, o in OBSERVED.items():
    vs = views_by_unit.get(unit_id, [])
    if not vs:
        print("skip (no view):", unit_id)
        continue
    view_ids = [v["id"] for v in vs]
    rec = dict(unit_id=unit_id, view_ids=view_ids, method="image_and_numeric",
               view_evidence=[v["files"]["png"] for v in vs],
               facts_sha256=digest(facts_by_unit.get(unit_id)),
               observation=o["observation"], result=o["result"], reason=o["reason"],
               evidence_ids=o.get("evidence_ids", ["fcpe_obs", "rmvpe_obs"]),
               resolved_findings=o.get("resolved_findings", []))
    records.append(rec)

reviews = dict(schema_version=1,
                inventory=ref(DESIGN / "review-inventory.json"),
                facts=ref(REVIEW / "independent-facts.json"),
                ledger=ref(DESIGN / "ledger.json"),
                atlas=ref(ATLAS / "atlas.json"),
                records=records)
out = DESIGN / "review_records.json"
out.write_text(json.dumps(reviews, ensure_ascii=False, indent=1), encoding="utf-8")
print("review records written:", len(records))
