import json
import numpy as np
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
game = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))
voiced = [n for n in game["notes"] if n["voiced"]]

# Let's inspect intervals between note starts in verse 1
starts = [n["start"] for n in voiced if 18.0 <= n["start"] <= 40.0]
diffs = np.diff(starts)
print("Note start diffs in Verse 1:")
for d in diffs:
    print(f"{d:.3f}", end=" ")
print()

# Median eighth note or quarter note?
# If quarter note is ~0.8s, BPM ~ 75
# If quarter note is ~0.9s, BPM ~ 67
# Let's estimate BPM by autocorrelation or inspecting bar lines
