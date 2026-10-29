import json
import numpy as np
from pathlib import Path

run_dir = Path(r"runs/production/nianlun-from-scratch-20261028")
hfa = json.loads((run_dir / "hfa" / "hfa_summary.json").read_text(encoding="utf-8"))
fcpe = np.load(run_dir / "observation" / "fcpe.npz")
rmvpe = np.load(run_dir / "observation" / "rmvpe.npz")
t_f, f0_f = fcpe["times"], fcpe["f0_hz"]
midi_f = np.where(f0_f > 50.0, 69.0 + 12.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)

print("=== Analyzing Syllable Melodies and Slurs ===")
detailed_notes = {}

for p in hfa["phrases"]:
    pid = p["phrase_id"]
    hanzi = p["hanzi"]
    l_words = p["lexical_words"]
    gv = p["game_voiced"]
    
    phrase_notes_spec = []
    
    for wi, lw in enumerate(l_words):
        ws, we = lw["start_s"], lw["end_s"]
        hz = lw["hanzi"]
        py = lw["mark"]
        dur = we - ws
        
        # Check GAME notes overlapping this syllable
        g_in = [g for g in gv if not (g["end_s"] <= ws or g["start_s"] >= we)]
        
        # Check FCPE pitch contour in this syllable
        mask = (t_f >= ws) & (t_f <= we) & (~np.isnan(midi_f))
        pts = midi_f[mask]
        
        if len(g_in) > 1 and dur >= 0.45:
            # Multi-note melisma detected by GAME!
            # e.g. 2 notes: first note frac, second note frac
            sub_tones = []
            for k, gn in enumerate(g_in):
                sub_tones.append((int(round(gn["tone"])), round(gn["dur_s"] / dur, 2)))
            # Normalize fractions
            total_frac = sum(f for t, f in sub_tones)
            sub_tones = [(t, round(f / total_frac, 2)) for t, f in sub_tones]
            phrase_notes_spec.append(sub_tones)
        elif len(pts) > 10 and dur >= 0.50:
            # Long syllable: check if pitch moves by >= 1.5 semitones from start to end
            p_start = np.median(pts[:len(pts)//3])
            p_end = np.median(pts[2*len(pts)//3:])
            if abs(p_end - p_start) >= 1.5:
                # Slur detected by FCPE!
                t1 = int(round(p_start))
                t2 = int(round(p_end))
                phrase_notes_spec.append([(t1, 0.5), (t2, 0.5)])
            else:
                tone = int(round(np.median(pts))) if len(pts) > 0 else (g_in[0]["midi"] if g_in else 60)
                phrase_notes_spec.append(tone)
        else:
            tone = int(round(np.median(pts))) if len(pts) > 0 else (g_in[0]["midi"] if g_in else 60)
            phrase_notes_spec.append(tone)
            
    detailed_notes[pid] = phrase_notes_spec

out_path = Path("scratch/nianlun_phrase_tones.json")
out_path.write_text(json.dumps(detailed_notes, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved phrase tone specifications to {out_path}")
