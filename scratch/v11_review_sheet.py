"""生成逐元音审阅工作表：349 个单元分页（每页 8 个），含每个单元的源观察与设计摘要。

审阅流程（Skill 要求）：
  实际打开图 -> 记录具体观察 -> 判定 keep/revise/fail/unknown
本脚本先产出工作表，随后逐页 read_image 并填记录。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ATLAS = NEW/'compiled'/'execution-review'/'atlas'
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
units = inv['units']

doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)
pitch = json.load(io.open(NEW/'compiled'/'pitch.json', encoding='utf-8'))
dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

def atlas_name(u):
    # id like p0:f0:v0 -> p0_f0_v0_000.png
    pid, fid, vid = u['id'].split(':')
    return f'{pid}_{fid}_{vid}_000.png'

rows=[]
for u in units:
    s0,s1 = u['support_s']
    T=np.arange(s0,s1,0.005)
    c=np.interp(T,dt,dc) if len(T)>=2 else np.array([np.interp(s0,dt,dc)])
    tone = u.get('musical_stages',[{}])[0].get('tone')
    rows.append(dict(
        id=u['id'], lyric=u['lyric'], symbol=u['symbol'],
        tone=tone, dur=round(s1-s0,3),
        t0=round(s0,3), t1=round(s1,3),
        design_min=round(float(c.min()),1), design_max=round(float(c.max()),1),
        design_span=round(float(c.max()-c.min()),1),
        design_med=round(float(np.median(c)),1),
        body_dev=round(float(np.median(c))-tone*100,1) if tone is not None else None,
        atlas=atlas_name(u),
        exists=(ATLAS/atlas_name(u)).is_file(),
    ))

missing=[r for r in rows if not r['exists']]
print(f'units {len(rows)}, atlas missing {len(missing)}')
if missing: print('  missing:', [m['id'] for m in missing[:8]])

# 分组统计
spans=np.array([r['design_span'] for r in rows])
devs=np.array([abs(r['body_dev']) for r in rows if r['body_dev'] is not None])
print(f'\ndesign span per vowel: median {np.median(spans):.0f}c  p90 {np.percentile(spans,90):.0f}c')
print(f'|body_dev| median {np.median(devs):.1f}c  >50c {(devs>50).mean():.1%}  >100c {(devs>100).mean():.1%}')

# 分页
PAGE=8
pages=[]
for i in range(0,len(rows),PAGE):
    pages.append(rows[i:i+PAGE])
print(f'\npage count (8 units/page): {len(pages)}')

sheet=dict(schema_version=1, page_size=PAGE, total=len(rows), pages=pages,
           review_status='pending', note='每页需实际打开其 png 并记录具体观察')
(NEW/'evaluation').mkdir(exist_ok=True)
(NEW/'evaluation'/'visual_review_sheet.json').write_text(
    json.dumps(sheet, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"wrote evaluation/visual_review_sheet.json")

# 打印前 3 页便于开始审阅
for pi,page in enumerate(pages[:3]):
    print(f'\n--- page {pi+1} ---')
    for r in page:
        print(f"  {r['id']:12s} {r['lyric']} {r['symbol']:9s} tone={r['tone']} dur={r['dur']:.2f}s "
              f"design {r['design_min']:.0f}..{r['design_max']:.0f} (span {r['design_span']:.0f}) "
              f"bodydev {r['body_dev']:+.0f}c")
