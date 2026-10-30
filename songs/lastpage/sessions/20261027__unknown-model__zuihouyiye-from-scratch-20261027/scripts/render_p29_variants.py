import copy
from pathlib import Path
import yaml
import soundfile as sf
import subprocess

def make_variant(name, high_v, high_t, high_b, mid_v, mid_t, mid_b, low_v, low_t, low_b, dyn_val):
    ustx_path = Path("runs/production/zuihouyiye-from-scratch-20261027/compiled_v5/project.ustx")
    doc = yaml.safe_load(ustx_path.read_text(encoding="utf-8"))
    
    p29 = copy.deepcopy(doc['voice_parts'][29])
    notes = p29['notes']
    
    ticks = []
    v_vals, t_vals, b_vals = [], [], []
    for n in notes:
        n_pos = n['position']
        n_dur = n['duration']
        n_end = n_pos + n_dur
        tone = n['tone']
        lyric = n.get('lyric', '')
        
        if lyric in ('AP', 'SP'):
            vt, tt, bt = 100, 0, 0
        elif tone >= 72:
            vt, tt, bt = high_v, high_t, high_b
        elif tone >= 67:
            vt, tt, bt = mid_v, mid_t, mid_b
        else:
            vt, tt, bt = low_v, low_t, low_b
            
        t_in = n_pos + min(40, int(0.12 * n_dur))
        t_out = n_end - min(60, int(0.18 * n_dur))
        ticks.extend([n_pos, t_in, t_out, n_end])
        v_vals.extend([vt, vt, vt, vt])
        t_vals.extend([tt, tt, tt, tt])
        b_vals.extend([bt, bt, bt, bt])
        
    combined = sorted(zip(ticks, v_vals, t_vals, b_vals), key=lambda x: x[0])
    u_ticks, u_voic, u_tenc, u_brec = [], [], [], []
    for t, v, te, b in combined:
        if not u_ticks or t > u_ticks[-1]:
            u_ticks.append(int(t))
            u_voic.append(int(round(v)))
            u_tenc.append(int(round(te)))
            u_brec.append(int(round(b)))
            
    # Curves
    curves = [c for c in p29.get('curves', []) if c['abbr'] not in ('voic', 'tenc', 'brec', 'dyn')]
    curves.append({'abbr': 'voic', 'xs': u_ticks, 'ys': u_voic})
    curves.append({'abbr': 'tenc', 'xs': u_ticks, 'ys': u_tenc})
    curves.append({'abbr': 'brec', 'xs': u_ticks, 'ys': u_brec})
    
    # Add dyn curve
    if dyn_val != 0:
        d_ticks = [0, notes[0]['position'], notes[0]['position'] + 40, notes[-1]['position'] + notes[-1]['duration'] - 40, notes[-1]['position'] + notes[-1]['duration']]
        d_ys = [0, 0, int(dyn_val * 10), int(dyn_val * 10), 0]
        curves.append({'abbr': 'dyn', 'xs': d_ticks, 'ys': d_ys})
        
    p29['curves'] = curves
    
    test_doc = copy.deepcopy(doc)
    test_doc['voice_parts'] = [p29]
    
    out_ustx = Path(f"scratch/test_p29_{name}.ustx")
    out_ustx.write_text(yaml.safe_dump(test_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    
    out_wav = Path(f"scratch/test_p29_{name}.wav")
    print(f"Rendering {name}...")
    subprocess.run([
        r"E:\project\agent2utau\.venv\Scripts\python.exe",
        "-m", "agent2utau.cli", "render-project",
        "--project", str(out_ustx),
        "--out", str(out_wav)
    ], check=True)
    print(f"Rendered {name} successfully.")

# Variant A: Solid mix-voice belt
make_variant("A_solid", high_v=120, high_t=16, high_b=-18, mid_v=116, mid_t=10, mid_b=-14, low_v=112, low_t=5, low_b=-10, dyn_val=3.5)

# Variant B: Stronger belt
make_variant("B_strong", high_v=126, high_t=22, high_b=-25, mid_v=120, mid_t=14, mid_b=-18, low_v=115, low_t=8, low_b=-12, dyn_val=5.0)

print("Both variants rendered!")
