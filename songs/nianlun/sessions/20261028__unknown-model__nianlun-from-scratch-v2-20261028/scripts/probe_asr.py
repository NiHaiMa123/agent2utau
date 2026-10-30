import json, io, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(io.open('runs/production/nianlun-from-scratch-v2-20261028/observation/asr.json', encoding='utf-8'))
for s in d['segments']:
    print(f"{s['start']:7.2f} {s['end']:7.2f}  {s['text']}")
