import json
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/project.ustx')
tm = TempoMap.from_doc(doc)
print(f"Total parts: {len(doc['voice_parts'])}")
for pi, vp in enumerate(doc['voice_parts']):
    lyrics = ''.join([n.get('lyric','') for n in vp['notes']])
    pos = vp['position']
    ns = tm.tick_to_ms(pos + vp['notes'][0]['position']) / 1000.0 if vp['notes'] else 0
    ne = tm.tick_to_ms(pos + vp['notes'][-1]['position'] + vp['notes'][-1]['duration']) / 1000.0 if vp['notes'] else 0
    curve_abbrs = [f"{c['abbr']}({len(c.get('xs', []))})" for c in vp.get('curves', [])]
    print(f"Part {pi:2d} [{ns:6.1f}s-{ne:6.1f}s]: {vp['name']:6s} ({len(vp['notes']):2d} notes) curves={curve_abbrs} lyrics='{lyrics}'")
