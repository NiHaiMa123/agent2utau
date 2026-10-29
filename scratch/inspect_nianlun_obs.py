import json
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
asr = json.loads((obs_dir / "asr.json").read_text(encoding="utf-8"))
game = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))

print(f"=== ASR Segments Count: {len(asr.get('segments', []))}")
for i, s in enumerate(asr.get("segments", [])):
    print(f"Seg {i:02d}: {s['start']:.2f}s - {s['end']:.2f}s: {s['text']}")

voiced_notes = [n for n in game.get("notes", []) if n.get("voiced")]
print(f"\n=== GAME Total Notes: {len(game.get('notes', []))}, Voiced Notes: {len(voiced_notes)}")
for i, n in enumerate(voiced_notes[:20]):
    print(f"Note {i:02d}: {n['start']:.2f}s - {n['end']:.2f}s (dur={n['end']-n['start']:.2f}s), midi={n.get('pitch', n.get('midi'))}")
