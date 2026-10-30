import json
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
game = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))

voiced = [n for n in game["notes"] if n["voiced"]]
print(f"Total voiced GAME notes: {len(voiced)}")

# Find gaps between voiced notes > 1.0s to detect natural musical phrases
phrases = []
cur_phrase = []

for i, n in enumerate(voiced):
    if not cur_phrase:
        cur_phrase.append(n)
    else:
        gap = n["start"] - (cur_phrase[-1]["start"] + cur_phrase[-1]["dur"])
        if gap > 1.0:
            phrases.append(cur_phrase)
            cur_phrase = [n]
        else:
            cur_phrase.append(n)
if cur_phrase:
    phrases.append(cur_phrase)

print(f"Detected {len(phrases)} major phrase blocks based on >1.0s gaps:")
for idx, p in enumerate(phrases):
    t_start = p[0]["start"]
    t_end = p[-1]["start"] + p[-1]["dur"]
    dur = t_end - t_start
    print(f"Block {idx:02d}: {t_start:6.2f}s - {t_end:6.2f}s (dur={dur:5.2f}s, notes={len(p):2d})")
