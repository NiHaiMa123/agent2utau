import json
from pathlib import Path
from agent2utau.evaluation.execution_review import build_inventory, validate_inventory
from agent2utau.openutau.ustx import sha256

design_dir = Path("runs/production/zuihouyiye-from-scratch-20261027/design")
score_path = design_dir / "score.ustx"
pitch_path = design_dir / "baseline_pitch.json"
phones_path = design_dir / "baseline_phones.json"
prov_path = design_dir / "native_provenance.json"
inv_path = design_dir / "inventory.json"
sources_path = design_dir / "sources.json"
ctx_path = design_dir / "context.json"

# Build raw inventory first to get new vowel clock boundaries
test_inv_path = Path("songs/lastpage/sessions/20261027__unknown-model__zuihouyiye-from-scratch-20261027/reports/raw_new_inventory.json")
test_inv_path.unlink(missing_ok=True)
raw_inv = build_inventory(score_path, test_inv_path, pitch_path, phones_path, prov_path, None, sources_path)
print("Raw new inventory built, units:", len(raw_inv['units']))

# Update context.json stages to be strictly inside the new vowel boundaries
ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
raw_units_by_id = {u['id']: u for u in raw_inv['units']}

for cu in ctx['units']:
    uid = cu['id']
    if uid in raw_units_by_id:
        u_s0, u_s1 = raw_units_by_id[uid]['support_s']
        u_dur = u_s1 - u_s0
        # Set stage support_s inside [u_s0, u_s1]
        for s in cu['stages']:
            s['support_s'] = [round(u_s0 + 0.005, 6), round(u_s1 - 0.005, 6)]

ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated context.json with aligned stage supports!")

# Now build final inventory.json with context!
inv_path.unlink(missing_ok=True)
final_inv = build_inventory(score_path, inv_path, pitch_path, phones_path, prov_path, ctx_path, sources_path)
print("Final inventory.json built with context! Units:", len(final_inv['units']))

# Validate inventory
v = validate_inventory(inv_path)
print("validate_inventory PASSED successfully!")
