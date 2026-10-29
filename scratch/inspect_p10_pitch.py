import json
from pathlib import Path

plan = json.loads(Path("runs/production/zuihouyiye-from-scratch-20261027/design/plan.json").read_text(encoding="utf-8"))
p10_plan = plan["phrases"][10]["design"]
print("P10 center_nodes:")
for node in p10_plan["center_nodes"]:
    print(" ", node)

print("\nP10 components:")
for comp in p10_plan["components"]:
    print(" ", comp)
