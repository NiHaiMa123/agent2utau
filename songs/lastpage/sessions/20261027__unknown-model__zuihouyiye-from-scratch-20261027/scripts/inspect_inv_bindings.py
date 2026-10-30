import json

inv = json.loads(open("runs/production/zuihouyiye-from-scratch-20261027/design/inventory.json", encoding="utf-8").read())
print("Bindings:", json.dumps(inv["bindings"], indent=2))
print("Sources:", json.dumps(inv["sources"], indent=2))
