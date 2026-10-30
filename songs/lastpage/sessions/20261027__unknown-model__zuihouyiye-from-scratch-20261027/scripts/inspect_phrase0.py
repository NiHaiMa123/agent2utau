import sys
sys.path.insert(0, 'src')
import json
from pathlib import Path
from agent2utau.openutau.ustx import TempoMap, load_ustx

run_dir = Path('runs/production/zuihouyiye-from-scratch-20261027')
design_dir = run_dir / 'design'
doc = load_ustx(design_dir / 'score.ustx')
tm = TempoMap.from_doc(doc)
base_pitch = json.loads((design_dir / 'baseline_pitch.json').read_text(encoding='utf-8'))
base_phones = json.loads((design_dir / 'baseline_phones.json').read_text(encoding='utf-8'))

part0 = doc['voice_parts'][0]
notes0 = part0['notes']
pos0 = part0['position']

print('Phrase 0 Notes:')
for i, n in enumerate(notes0):
    s = tm.tick_to_ms(pos0 + n['position']) / 1000.0
    e = tm.tick_to_ms(pos0 + n['position'] + n['duration']) / 1000.0
    dur = e - s
    lyric = n.get('lyric')
    tone = n.get('tone')
    print(f"  Note {i}: {lyric} tone={tone} dur={dur*1000:.1f}ms [{s:.3f}s -> {e:.3f}s]")

print('\nPhrase 0 Phones:')
ph0 = base_phones['parts'][0]['phrases'][0]['phones']
for p in ph0:
    sym = p.get('symbol')
    sms = p.get('start_ms')
    ems = p.get('end_ms')
    print(f"  Phone {sym}: [{sms:.1f}ms -> {ems:.1f}ms]")
