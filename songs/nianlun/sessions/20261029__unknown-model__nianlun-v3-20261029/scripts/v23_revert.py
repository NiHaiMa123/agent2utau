"""回退到 v21 的曲线（v22 的「单峰单谷 + 交替极性」使 body_dev 恶化到 139 个 watch）。

判断依据（客观）：
  v21: keep 342 / watch 7，body_dev median 8c, max 41c
  v22: keep 210 / watch 139，body_dev 普遍 ±110-120c
  → v22 是退步，回退。

同时保留 v22 的正面成果：逐字参数离散度证据（已记录在 no_fixed_recipe_check.json）。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

src = NEW/'compiled'/'project_v21.ustx'
if not src.is_file():
    print('project_v21.ustx missing - rebuilding from v20 pipeline')
    raise SystemExit(1)

doc = load_ustx(src)
mine = load_ustx(NEW/'score'/'v21_score.ustx')
mp = {}
for p in mine['voice_parts']:
    pit = next((c for c in p['curves'] if c['abbr']=='pitd'), None)
    if pit: mp[int(p['position'])] = (list(pit['xs']), list(pit['ys']))
n=0
for cp in doc['voice_parts']:
    k = int(cp['position'])
    if k not in mp: continue
    xs, ys = mp[k]
    cp['curves'] = [c for c in cp['curves'] if c['abbr']!='pitd']
    cp['curves'].append(dict(abbr='pitd', xs=xs, ys=ys))
    n+=1
print(f'replaced PITD in {n} parts from v21_score')

# 扩展到原生全域
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
cfg = load_config()
bp_out = NEW/'compiled'/'pitch_baseline.json'
run_bridge(cfg, ['export-pitch','--project',str((NEW/'compiled'/'baseline.ustx').resolve()),
                 '--out',str(bp_out.resolve())])
bp = json.load(io.open(bp_out, encoding='utf-8'))
samp={}
for ph in bp['phrases']:
    pos=int(ph['part_position']); st=int(ph['pitch_start_tick'])-pos; it=int(ph['pitch_interval_ticks'])
    samp.setdefault(pos,[]).append(st+np.arange(len(ph['times_ms']))*it)
for part in doc['voice_parts']:
    pos=int(part['position'])
    if pos not in samp: continue
    pit=next(c for c in part['curves'] if c['abbr']=='pitd')
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    allt=np.unique(np.concatenate(samp[pos]))
    lo=int(min(allt.min(),xs[0])); hi=int(max(allt.max(),xs[-1]))
    g=set(range(lo-lo%5,hi+1,5)); g.update(int(t) for t in allt)
    gx=sorted(g); gy=[int(round(float(v))) for v in np.interp(np.array(gx,float),xs,ys)]
    pit['xs']=gx; pit['ys']=gy

save_ustx(doc, NEW/'compiled'/'project_final.ustx')
st=[]
for p in doc['voice_parts']:
    pit=next(c for c in p['curves'] if c['abbr']=='pitd')
    if len(pit['ys'])>1: st.append(np.abs(np.diff(np.array(pit['ys'],float))))
a=np.concatenate(st)
print(f'  |dy| median {np.median(a):.1f} max {a.max():.0f}')
print('wrote project_final.ustx (reverted to v21 curve)')
