"""核验 v3 字界：与 GAME 音符、能量、F0 的一致性。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
w = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
notes = g['notes']

allw = []
for p in w['phrases']:
    for x in p['words']:
        allw.append(dict(pid=p['pid'], **x))

print(f"words {len(allw)}")
# 1. coverage vs GAME notes: each word should contain >=1 GAME note onset or be inside a long note
miss = 0
for x in allw:
    ons = [n for n in notes if x['start']-0.02 <= n['start'] < x['end']+0.02]
    x['n_notes'] = len(ons)
    if len(ons) == 0: miss += 1
print(f"words containing no GAME note onset: {miss}")
from collections import Counter
print("notes-per-word distribution:", dict(Counter(min(x['n_notes'],6) for x in allw)))

# 2. pitch continuity check: adjacent words shouldn't jump wildly unless real
big = []
for p in w['phrases']:
    ws = [x for x in p['words'] if x['pitch_cents'] is not None]
    for a, b in zip(ws, ws[1:]):
        if abs(b['pitch_cents']-a['pitch_cents']) > 700:
            big.append((p['pid'], a['hanzi'], round(a['pitch_cents'],0), b['hanzi'], round(b['pitch_cents'],0),
                        round(b['pitch_cents']-a['pitch_cents'])))
print(f"\nadjacent-word pitch jumps >700c: {len(big)}")
for x in big[:15]: print('   ', x)

# 3. pitch range sanity
pc = np.array([x['pitch_cents'] for x in allw if x['pitch_cents'] is not None])
print(f"\npitch: min {pc.min():.0f} p5 {np.percentile(pc,5):.0f} median {np.median(pc):.0f} "
      f"p95 {np.percentile(pc,95):.0f} max {pc.max():.0f} (cents rel 6900=C5)")
print(f"  in MIDI: {np.median(pc)/100:.1f} median, range {pc.min()/100:.1f}-{pc.max()/100:.1f}")

# 4. phrase-level summary
print("\nper phrase: n | dur sum | pitch range")
for p in w['phrases']:
    ps = [x['pitch_cents'] for x in p['words'] if x['pitch_cents'] is not None]
    du = sum(x['dur'] for x in p['words'])
    rng = f"{min(ps):.0f}-{max(ps):.0f}" if ps else "n/a"
    print(f"  {p['pid']} {p['hanzi'][:12]:12s} n={p['n']:2d} dur={du:5.2f}/{p['time'][1]-p['time'][0]:5.2f} pitch={rng}")
