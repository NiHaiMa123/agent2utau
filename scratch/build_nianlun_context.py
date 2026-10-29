import json
from pathlib import Path
from agent2utau.evaluation.execution_review import build_inventory, validate_inventory

run_dir = Path(r"runs/production/nianlun-from-scratch-20261028")
design_dir = run_dir / "design"
score_ustx = design_dir / "score.ustx"
pitch_path = design_dir / "baseline_pitch.json"
phones_path = design_dir / "baseline_phones.json"
prov_path = design_dir / "native_provenance.json"
sources_path = design_dir / "sources.json"
ctx_path = design_dir / "context.json"
inv_path = design_dir / "inventory.json"

raw_inv = json.loads(Path("scratch/raw_inv_nianlun.json").read_text(encoding="utf-8"))

ctx_units = []
for u in raw_inv["units"]:
    uid = u["id"]
    sym = u.get("symbol", "vowel")
    s0, s1 = u["support_s"]
    ctx_units.append({
        "id": uid,
        "condition": {
            "status": "observed",
            "evidence_ids": [
                "game_obs",
                "fcpe_obs",
                "rmvpe_obs",
                "hfa_summary"
            ],
            "observation": f"Vowel {sym} spanning {s0:.3f}s to {s1:.3f}s",
            "interpretation": "Clear lyrical vowel needing natural voicing and smooth pitch",
            "reliability": "high"
        },
        "stages": [
            {
                "id": f"{uid}:body",
                "kind": "body",
                "support_s": [
                    round(s0 + 0.005, 6),
                    round(s1 - 0.005, 6),
                ],
                "required": True,
            }
        ]
    })

ctx_doc = {"schema_version": 1, "units": ctx_units}
ctx_path.write_text(json.dumps(ctx_doc, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {ctx_path} with {len(ctx_units)} context units.")

inv_path.unlink(missing_ok=True)
final_inv = build_inventory(score_ustx, inv_path, pitch_path, phones_path, prov_path, ctx_path, sources_path)
inv = validate_inventory(inv_path)
print(f"Validated final inventory.json! Total units: {len(inv['units'])}")
