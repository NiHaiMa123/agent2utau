"""v3：写入逐元音审阅记录（实图审）+ 生成 musical_critique。

records 只覆盖本次实际打开图并写具体观察的单元；其余保持 pending。
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
from agent2utau.evaluation.execution_review import digest

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
REVIEW = V3 / "render" / "execution-review"
ATLAS = REVIEW / "atlas"
OBS = ROOT / "scratch" / "v3_review_observations.json"


def ref(path):
    p = pathlib.Path(path).resolve()
    import hashlib
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


facts = json.loads((REVIEW / "independent-facts.json").read_text(encoding="utf-8"))
atlas = json.loads((ATLAS / "atlas.json").read_text(encoding="utf-8"))
views_by_unit = {}
for v in atlas["views"]:
    views_by_unit.setdefault(v["unit_id"], []).append(v)
facts_by_unit = {u["id"]: u for u in facts["units"]}

OBSERVED = json.loads(OBS.read_text(encoding="utf-8"))
records = []
for unit_id, o in OBSERVED.items():
    vs = views_by_unit.get(unit_id, [])
    if not vs:
        print("skip (no view):", unit_id)
        continue
    rec = dict(unit_id=unit_id, view_ids=[v["id"] for v in vs], method="image_and_numeric",
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
(DESIGN / "review_records.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=1), encoding="utf-8")
print("review records written:", len(records))
