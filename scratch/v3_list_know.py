"""列出表1实体与参数，选出与本任务（音高/长音/发声/气口）相关的 ID。"""
import sys, json, io, csv
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

K = Path('docs/knowledge/acoustic-manifestations-20261009')
kt = json.load(io.open(K/'knowledge-table.json', encoding='utf-8'))
print('=== table1 entities (49) ===')
for e in kt['entities']:
    print(f"  {e['id']:10s} {e.get('name','')[:38]:38s} | {str(e.get('definition',''))[:70]}")

with open(K/'control-details.csv', encoding='utf-8-sig', newline='') as f:
    pr = list(csv.DictReader(f))
print(f'\n=== parameters ({len(pr)}) cols: {list(pr[0])} ===')
for r in pr[:6]:
    print('  ', r.get('id'), '|', str(r.get('abbr') or r.get('name'))[:60])
ids = [r['id'] for r in pr]
print('\nfirst 20 param ids:', ids[:20])

# response indices
for name in ['table2-v04-DYN-accepted-index-20261014.json', 'yuai/learned-conditions-carryover-20261016-index.json']:
    p = Path('docs/knowledge/acoustic-manifestations-20261009')/name if not name.startswith('yuai') else Path('docs/reports')/name
    print(f'\n--- {p} exists={p.exists()} ---')
    if p.exists():
        d = json.load(io.open(p, encoding='utf-8'))
        rows = d.get('rows', [])
        print(f'  rows {len(rows)}')
        for r in rows[:5]: print('   ', r.get('id'), '|', str(r.get('label') or r.get('summary'))[:60])
