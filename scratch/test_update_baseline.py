import copy
import json
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx, save_ustx, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from agent2utau.evaluation.execution_review import validate_inventory

cfg = load_config()
design_dir = Path("runs/production/zuihouyiye-from-scratch-20261027/design")
score_path = design_dir / "score.ustx"
pitch_path = design_dir / "baseline_pitch.json"
phones_path = design_dir / "baseline_phones.json"
prov_path = design_dir / "native_provenance.json"
inv_path = design_dir / "inventory.json"
sources_path = design_dir / "sources.json"

doc = load_ustx(score_path)

# Apply fixes to score.ustx:
# 1. Polyphone fixes in Chorus 2 & 3: '没' -> '没[m ei]'
for pi in [28, 34]:
    for n in doc['voice_parts'][pi]['notes']:
        if n.get('lyric') == '没':
            n['lyric'] = '没[m ei]'

# 2. Bogus APs in middle of words -> '+'
# Part 18: note 8 was AP(64)
doc['voice_parts'][18]['notes'][8]['lyric'] = '+'
doc['voice_parts'][18]['notes'][8]['tone'] = doc['voice_parts'][18]['notes'][7]['tone']

# Part 24: note 10 was AP(59)
doc['voice_parts'][24]['notes'][10]['lyric'] = '+'
doc['voice_parts'][24]['notes'][10]['tone'] = doc['voice_parts'][24]['notes'][9]['tone']

# Part 25: note 4 & 8 were AP(64)
doc['voice_parts'][25]['notes'][4]['lyric'] = '+'
doc['voice_parts'][25]['notes'][4]['tone'] = doc['voice_parts'][25]['notes'][3]['tone']
doc['voice_parts'][25]['notes'][8]['lyric'] = '+'
doc['voice_parts'][25]['notes'][8]['tone'] = doc['voice_parts'][25]['notes'][7]['tone']

# Part 31: note 5 was AP(59)
doc['voice_parts'][31]['notes'][5]['lyric'] = '+'
doc['voice_parts'][31]['notes'][5]['tone'] = doc['voice_parts'][31]['notes'][4]['tone']

# Part 37: note 5 was AP(59)
doc['voice_parts'][37]['notes'][5]['lyric'] = '+'
doc['voice_parts'][37]['notes'][5]['tone'] = doc['voice_parts'][37]['notes'][4]['tone']

# Save updated score.ustx
save_ustx(doc, score_path)
score_hash = sha256(score_path)
print("Updated score.ustx, sha256:", score_hash[:12])

# Export fresh baseline_pitch.json and baseline_phones.json
r_pitch = run_bridge(cfg, ['export-pitch', '--project', str(score_path.resolve()), '--out', str(pitch_path.resolve())])
assert r_pitch.get('ok'), f"export-pitch failed: {r_pitch}"
pitch_hash = sha256(pitch_path)
print("Exported baseline_pitch.json, sha256:", pitch_hash[:12])

r_phones = run_bridge(cfg, ['export-phonemes', '--project', str(score_path.resolve()), '--out', str(phones_path.resolve())])
assert r_phones.get('ok'), f"export-phonemes failed: {r_phones}"
phones_hash = sha256(phones_path)
print("Exported baseline_phones.json, sha256:", phones_hash[:12])

# Update native_provenance.json
prov_obj = json.loads(prov_path.read_text(encoding="utf-8"))
prov_obj["project_sha256"] = score_hash
prov_obj["pitch_sha256"] = pitch_hash
prov_obj["phonemes_sha256"] = phones_hash
prov_path.write_text(json.dumps(prov_obj, ensure_ascii=False, indent=2), encoding="utf-8")
prov_hash = sha256(prov_path)
print("Updated native_provenance.json, sha256:", prov_hash[:12])

# Update sources.json
sources_obj = json.loads(sources_path.read_text(encoding="utf-8"))
for s in sources_obj["sources"]:
    if s["id"] == "score_ustx":
        s["file"]["sha256"] = score_hash
    elif s["id"] == "baseline_pitch":
        s["file"]["sha256"] = pitch_hash
    elif s["id"] == "baseline_phones":
        s["file"]["sha256"] = phones_hash
    elif s["id"] == "native_provenance":
        s["file"]["sha256"] = prov_hash
sources_path.write_text(json.dumps(sources_obj, ensure_ascii=False, indent=2), encoding="utf-8")
sources_hash = sha256(sources_path)
print("Updated sources.json, sha256:", sources_hash[:12])

# Update inventory.json
inv_obj = json.loads(inv_path.read_text(encoding="utf-8"))
inv_obj["bindings"]["project"]["sha256"] = score_hash
inv_obj["bindings"]["pitch"]["sha256"] = pitch_hash
inv_obj["bindings"]["phonemes"]["sha256"] = phones_hash
inv_obj["bindings"]["provenance"]["sha256"] = prov_hash

for d in inv_obj["dependencies"]:
    if d["path"].endswith("sources.json"):
        d["sha256"] = sources_hash

for s in inv_obj["sources"]:
    if s["id"] == "score_ustx":
        s["file"]["sha256"] = score_hash
    elif s["id"] == "baseline_pitch":
        s["file"]["sha256"] = pitch_hash
    elif s["id"] == "baseline_phones":
        s["file"]["sha256"] = phones_hash
    elif s["id"] == "native_provenance":
        s["file"]["sha256"] = prov_hash

inv_path.write_text(json.dumps(inv_obj, ensure_ascii=False, indent=2), encoding="utf-8")

# Validate inventory!
try:
    inv = validate_inventory(inv_path)
    print("validate_inventory PASSED successfully!")
except Exception as e:
    print("validate_inventory exception:", e)
