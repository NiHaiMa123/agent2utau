import json
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
print('voice_parts count:', len(doc['voice_parts']))
for pi, vp in enumerate(doc['voice_parts'][:16]):
    curves = vp.get('curves', [])
    abbr_summaries = []
    for c in curves:
        abbr = c.get('abbr')
        xs = c.get('xs', [])
        ys = c.get('ys', [])
        min_y = min(ys) if ys else None
        max_y = max(ys) if ys else None
        abbr_summaries.append(f"{abbr}({len(xs)} pts, min={min_y}, max={max_y})")
    lyrics = "".join([n.get("lyric", "") for n in vp.get("notes", [])])
    print(f"Part {pi}: '{lyrics}' -> {abbr_summaries}")
