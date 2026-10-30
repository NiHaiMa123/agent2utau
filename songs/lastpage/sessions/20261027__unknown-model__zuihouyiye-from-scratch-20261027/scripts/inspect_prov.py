import json

prov = json.loads(open("runs/production/zuihouyiye-from-scratch-20261027/design/native_provenance.json", encoding="utf-8").read())
print(json.dumps(prov, indent=2))
