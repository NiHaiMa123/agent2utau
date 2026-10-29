import json

inv = json.loads(open("runs/production/zuihouyiye-from-scratch-20261027/design/inventory.json", encoding="utf-8").read())
print("Dependencies:", json.dumps(inv["dependencies"], indent=2))
