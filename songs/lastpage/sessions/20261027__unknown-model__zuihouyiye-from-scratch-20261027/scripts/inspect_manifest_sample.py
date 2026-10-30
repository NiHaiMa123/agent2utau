import json
from pathlib import Path

p = Path(r"runs/production/zuihouyiye-from-scratch-20261027/hfa_inputs/slices_manifest.json")
m = json.loads(p.read_text(encoding="utf-8"))
print(f"Total phrases: {len(m['phrases'])}")
print("Sample phrase 0:", json.dumps(m["phrases"][0], ensure_ascii=False, indent=2))
print("Sample phrase 1:", json.dumps(m["phrases"][1], ensure_ascii=False, indent=2))
