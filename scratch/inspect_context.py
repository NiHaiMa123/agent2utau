import json

ctx = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/design/context.json', encoding='utf-8').read())
print("Context schema:", ctx.get('schema_version'), "units:", len(ctx.get('units', [])))
if ctx.get('units'):
    print("Unit 0:", json.dumps(ctx['units'][0], indent=2))
