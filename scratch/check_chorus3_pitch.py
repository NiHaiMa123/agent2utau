import json
import numpy as np
from pathlib import Path

run_dir = Path(r"runs/production/nianlun-from-scratch-20261028")
hfa = json.loads((run_dir / "hfa" / "hfa_summary.json").read_text(encoding="utf-8"))
fcpe = np.load(run_dir / "observation" / "fcpe.npz")
rmvpe = np.load(run_dir / "observation" / "rmvpe.npz")
t_f, f0_f = fcpe["times"], fcpe["f0_hz"]
midi_f = np.where(f0_f > 50.0, 69.0 + 12.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)

for p in hfa["phrases"]:
    pid = p["phrase_id"]
    if pid in ("p44", "p45", "p46", "p47", "p48", "p49", "p50"):
        print(f"\n=== {pid}: {p['hanzi']} ===")
        for lw in p["lexical_words"]:
            ws, we = lw["start_s"], lw["end_s"]
            hz = lw["hanzi"]
            py = lw["mark"]
            mask = (t_f >= ws) & (t_f <= we) & (~np.isnan(midi_f))
            pts = midi_f[mask]
            med = np.median(pts) if len(pts) > 0 else 0
            max_p = np.max(pts) if len(pts) > 0 else 0
            print(f"  {hz}[{py:5s}]: med={med:5.1f}, max={max_p:5.1f} ({ws:.2f}-{we:.2f}s)")
