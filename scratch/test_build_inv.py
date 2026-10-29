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

# First, let's update context.json so that any unit's stage support_s fits inside the new native vowel clock
# Let's run build_inventory without context first, or with context
try:
    res = build_inventory(score_path, inv_path, pitch_path, phones_path, prov_path, None, sources_path)
    print("build_inventory without context: ok, units =", len(res['units']))
    v = validate_inventory(inv_path)
    print("validate_inventory without context: ok!")
except Exception as e:
    print("Error:", e)
