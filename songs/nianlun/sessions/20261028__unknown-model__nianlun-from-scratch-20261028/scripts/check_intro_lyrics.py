import json
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
game = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))
asr = json.loads((obs_dir / "asr.json").read_text(encoding="utf-8"))

print("GAME notes between 15s and 35s:")
for n in game["notes"]:
    if 15.0 <= n["start"] <= 35.0:
        print(f"  {n['start']:6.2f} - {n['start']+n['dur']:6.2f}s (dur={n['dur']:.2f}s) midi={n['tone']:.1f} voiced={n['voiced']}")

print("\nASR segments between 15s and 35s:")
for s in asr["segments"]:
    if s["start"] <= 35.0:
        print(f"  {s['start']:6.2f} - {s['end']:6.2f}s: {s['text']}")
