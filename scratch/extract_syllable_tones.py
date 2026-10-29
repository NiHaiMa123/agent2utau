import json
import numpy as np
from pathlib import Path

run_dir = Path(r"runs/production/nianlun-from-scratch-20261028")
hfa = json.loads((run_dir / "hfa" / "hfa_summary.json").read_text(encoding="utf-8"))
fcpe = np.load(run_dir / "observation" / "fcpe.npz")
rmvpe = np.load(run_dir / "observation" / "rmvpe.npz")

t_f, f0_f = fcpe["times"], fcpe["f0_hz"]
t_r, f0_r = rmvpe["times"], rmvpe["f0_hz"]

cents_f = np.where(f0_f > 50.0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)
midi_f = cents_f / 100.0

cents_r = np.where(f0_r > 50.0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_r, 1e-6) / 440.0), np.nan)
midi_r = cents_r / 100.0

# Scale name helper
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def midi_to_name(m):
    if np.isnan(m): return "None"
    im = int(round(m))
    return f"{NOTE_NAMES[im % 12]}{im // 12 - 1}({im})"

print("=== Analyzing Syllable Pitches across all 51 phrases ===")
phrase_specs = {}

for p in hfa["phrases"]:
    pid = p["phrase_id"]
    hanzi = p["hanzi"]
    l_words = p["lexical_words"]
    gv = p["game_voiced"]
    
    syl_tones = []
    lines = []
    for wi, lw in enumerate(l_words):
        ws, we = lw["start_s"], lw["end_s"]
        hz = lw["hanzi"]
        py = lw["mark"]
        
        # FCPE points in this syllable
        mask = (t_f >= ws) & (t_f <= we) & (~np.isnan(midi_f))
        if np.any(mask):
            pts = midi_f[mask]
            # Take core 20%-80% to avoid consonant transition
            q20, q80 = np.percentile(pts, [20, 80])
            mid_pts = pts[(pts >= q20) & (pts <= q80)]
            med_m = float(np.median(mid_pts)) if len(mid_pts) > 0 else float(np.median(pts))
            tone = int(round(med_m))
        else:
            # Fallback to nearest GAME voiced
            tone = 60
        syl_tones.append(tone)
        lines.append(f"{hz}[{py}]={midi_to_name(tone)}")
    
    phrase_specs[pid] = syl_tones
    print(f"{pid} ({len(hanzi)}): {' '.join(lines)}")

out_json = run_dir / "design" / "preliminary_tones.json"
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(phrase_specs, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nWrote preliminary tones to {out_json}")
