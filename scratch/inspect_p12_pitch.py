import json
from pathlib import Path
from agent2utau.workflow import design_math

plan = json.loads(Path("runs/production/zuihouyiye-from-scratch-20261027/design/plan.json").read_text(encoding="utf-8"))
p12_plan = plan["phrases"][12]["design"]
print("P12 center_nodes:")
for node in p12_plan["center_nodes"]:
    print(" ", node)

print("\nP12 components:")
for comp in p12_plan["components"]:
    print(" ", comp)
