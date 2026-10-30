import json
from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
tm = TempoMap.from_doc(doc)

def describe_part(vp):
    notes = vp['notes']
    pos = vp['position']
    res = []
    for n in notes:
        ns = tm.tick_to_ms(pos + n['position']) / 1000.0
        ne = tm.tick_to_ms(pos + n['position'] + n['duration']) / 1000.0
        res.append(f"{n.get('lyric')}({n['tone']},{ne-ns:.2f}s)")
    return " ".join(res)

with open('songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028/reports/full_structure_compare.txt', 'w', encoding='utf-8') as f:
    f.write("=== VERSE 1 vs VERSE 2 ===\n")
    for i in range(6):
        f.write(f"V1 P{i:02d}: {describe_part(doc['voice_parts'][i])}\n")
        f.write(f"V2 P{i+16:02d}: {describe_part(doc['voice_parts'][i+16])}\n\n")

    f.write("\n=== PRE-CHORUS 1 vs PRE-CHORUS 2 ===\n")
    for i in range(6, 10):
        f.write(f"PC1 P{i:02d}: {describe_part(doc['voice_parts'][i])}\n")
        f.write(f"PC2 P{i+16:02d}: {describe_part(doc['voice_parts'][i+16])}\n\n")

    f.write("\n=== CHORUS 1 vs CHORUS 2 vs CHORUS 3 ===\n")
    for i in range(10, 16):
        f.write(f"C1 P{i:02d}: {describe_part(doc['voice_parts'][i])}\n")
        f.write(f"C2 P{i+16:02d}: {describe_part(doc['voice_parts'][i+16])}\n")
        f.write(f"C3 P{i+22:02d}: {describe_part(doc['voice_parts'][i+22])}\n\n")

print("Saved songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028/reports/full_structure_compare.txt")
