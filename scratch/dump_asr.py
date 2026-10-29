import json
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
asr = json.loads((obs_dir / "asr.json").read_text(encoding="utf-8"))

lines = []
for i, s in enumerate(asr.get("segments", [])):
    lines.append(f"Seg {i:02d}: {s['start']:6.2f}s - {s['end']:6.2f}s: {s['text']}")

out_txt = Path(r"scratch/asr_segments.txt")
out_txt.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(lines)} segments to {out_txt}")
