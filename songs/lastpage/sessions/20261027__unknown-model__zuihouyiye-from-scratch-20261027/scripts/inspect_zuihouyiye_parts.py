from agent2utau.openutau.ustx import load_ustx
from pathlib import Path

doc = load_ustx(Path("runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx"))
print("Total voice parts:", len(doc["voice_parts"]))
for i, vp in enumerate(doc["voice_parts"]):
    lyrics = "".join(n["lyric"] for n in vp["notes"] if n["lyric"] not in ("+", "AP", "SP"))
    print(f"Part {i:02d} (pos={vp['position']:6d}): {lyrics}")
