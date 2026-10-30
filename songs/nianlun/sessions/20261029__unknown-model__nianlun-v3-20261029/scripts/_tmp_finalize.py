"""通用收尾：把 score 的连续 PITD 写回 compiled，扩展到原生 tick 全域，保存为 project_final。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

VER = sys.argv[1] if len(sys.argv) > 1 else 'v20'
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()

compiled = load_ustx(NEW/'compiled'/f'project_{VER}.ustx')
mine = load_ustx(NEW/'score'/f'{VER}_score.ustx')

mp = {}
for p in mine['voice_parts']:
    pit = next((c for c in p['curves'] if c['abbr'] == 'pitd'), None)
    if pit:
        mp[int(p['position'])] = (list(pit['xs']), list(pit['ys']))
n = 0
for cp in compiled['voice_parts']:
    k = int(cp['position'])
    if k not in mp:
        continue
    xs, ys = mp[k]
    cp['curves'] = [c for c in cp['curves'] if c['abbr'] != 'pitd']
    cp['curves'].append(dict(abbr='pitd', xs=xs, ys=ys))
    n += 1
print(f'{VER}: replaced {n} parts')

out_p = NEW/'compiled'/'pitch_baseline.json'
run_bridge(cfg, ['export-pitch', '--project', str((NEW/'compiled'/'baseline.ustx').resolve()),
                 '--out', str(out_p.resolve())])
bp = json.load(io.open(out_p, encoding='utf-8'))
samp = {}
for ph in bp['phrases']:
    pos = int(ph['part_position'])
    st = int(ph['pitch_start_tick']) - pos
    it = int(ph['pitch_interval_ticks'])
    samp.setdefault(pos, []).append(st + np.arange(len(ph['times_ms']))*it)

for part in compiled['voice_parts']:
    pos = int(part['position'])
    if pos not in samp:
        continue
    pit = next(c for c in part['curves'] if c['abbr'] == 'pitd')
    xs = np.array(pit['xs'], float); ys = np.array(pit['ys'], float)
    allt = np.unique(np.concatenate(samp[pos]))
    lo = int(min(allt.min(), xs[0])); hi = int(max(allt.max(), xs[-1]))
    g = set(range(lo - lo % 5, hi+1, 5))
    g.update(int(t) for t in allt)
    gx = sorted(g)
    gy = [int(round(float(v))) for v in np.interp(np.array(gx, float), xs, ys)]
    pit['xs'] = gx; pit['ys'] = gy

save_ustx(compiled, NEW/'compiled'/'project_final.ustx')
st = []
for p in compiled['voice_parts']:
    pit = next(c for c in p['curves'] if c['abbr'] == 'pitd')
    if len(pit['ys']) > 1:
        st.append(np.abs(np.diff(np.array(pit['ys'], float))))
a = np.concatenate(st)
print(f'  |dy| median {np.median(a):.1f} max {a.max():.0f}  >200 {(a>200).sum()}')
print('wrote project_final.ustx')
