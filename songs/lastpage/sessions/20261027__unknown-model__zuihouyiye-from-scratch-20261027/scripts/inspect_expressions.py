import json
from agent2utau.openutau.ustx import load_ustx

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
print("Expressions:", json.dumps(doc.get("expressions", {}), indent=2))
