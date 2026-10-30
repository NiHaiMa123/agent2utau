"""验证：连续 PITD（5-tick 网格）写回后，最终线 = before_pitd + PITD，误差 < 0.501c。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
PROJ = NEW/'compiled'/'project_final.ustx'
BASE = NEW/'compiled'/'baseline.ustx'

r1 = run_bridge(cfg, ['export-pitch','--project',str(PROJ.resolve()),
                      '--out',str((NEW/'compiled'/'pitch_final.json').resolve())])
r2 = run_bridge(cfg, ['export-pitch','--project',str(BASE.resolve()),
                      '--out',str((NEW/'compiled'/'pitch_baseline.json').resolve())])
print('export final:', r1.get('ok'), ' baseline:', r2.get('ok'))

pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
mine = load_ustx(NEW/'score'/'v15_score.ustx')
mymap = {}
for mp in mine['voice_parts']:
    pit = next(c for c in mp['curves'] if c['abbr']=='pitd')
    mymap[int(mp['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))

doc = load_ustx(PROJ); tm = TempoMap.from_doc(doc)
maxerr=0.0; allerr=[]
for bph, fph in zip(bp['phrases'], pf['phrases']):
    pos = int(bph['part_position'])
    if pos not in mymap: continue
    if bph['times_ms'] != fph['times_ms']: continue
    xs, ys = mymap[pos]
    times = np.asarray(bph['times_ms'], float)
    ticks = np.array([tm.ms_to_tick(t) - pos for t in times])
    # PITD at this 5-tick grid should match my values exactly if aligned
    off = np.interp(ticks, xs, ys)
    expected = np.asarray(bph['before_pitd_cents'], float) + off
    actual = np.asarray(fph['final_cents'], float)
    allerr.append(actual - expected)
    maxerr = max(maxerr, float(np.max(np.abs(actual-expected))))

e = np.concatenate(allerr)
print(f'\nframes {len(e)}')
print(f'  max |actual - (before + myPITD)| = {maxerr:.4f} c   (contract < 0.501)')
print(f'  median {np.median(np.abs(e)):.4f}  p99 {np.percentile(np.abs(e),99):.4f}')
print(f'  => {"PASS" if maxerr < 0.501 else "FAIL"}')
