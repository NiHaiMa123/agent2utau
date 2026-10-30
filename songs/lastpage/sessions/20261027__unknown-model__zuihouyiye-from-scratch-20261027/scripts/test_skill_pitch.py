import sys
sys.path.insert(0, 'src')
import json
import numpy as np
from pathlib import Path
from agent2utau.openutau.ustx import TempoMap, load_ustx
from agent2utau.workflow import design_math

dm = design_math()
run_dir = Path('runs/production/zuihouyiye-from-scratch-20261027')
design_dir = run_dir / 'design'
doc = load_ustx(design_dir / 'score.ustx')
tm = TempoMap.from_doc(doc)
base_pitch = json.loads((design_dir / 'baseline_pitch.json').read_text(encoding='utf-8'))

part0 = doc['voice_parts'][0]
notes = part0['notes']
pos = part0['position']
p_start_s = tm.tick_to_ms(pos + notes[0]['position']) / 1000.0
p_end_s = tm.tick_to_ms(pos + notes[-1]['position'] + notes[-1]['duration']) / 1000.0

n_spans = []
for n in notes:
    ns = tm.tick_to_ms(pos + n['position']) / 1000.0
    ne = tm.tick_to_ms(pos + n['position'] + n['duration']) / 1000.0
    n_spans.append((ns, ne, float(n['tone'] * 100.0), n['lyric']))

def build_natural_center_nodes(p_start_s, p_end_s, n_spans):
    center_nodes = [[p_start_s, n_spans[0][2], 0.0]]
    for ni in range(len(n_spans) - 1):
        _, b_s, tone_left, _ = n_spans[ni]
        _, _, tone_right, _ = n_spans[ni + 1]
        dur_left = n_spans[ni][1] - n_spans[ni][0]
        dur_right = n_spans[ni + 1][1] - n_spans[ni + 1][0]
        diff = tone_right - tone_left

        if abs(diff) < 1e-3:
            # Same tone: subtle re-articulation dip if not slurred
            if dur_left > 0.25 and dur_right > 0.25:
                t_pre = round(max(center_nodes[-1][0] + 0.020, b_s - 0.040), 6)
                t_mid = round(b_s, 6)
                t_post = round(b_s + 0.040, 6)
                center_nodes.append([t_pre, tone_left, 0.0])
                center_nodes.append([t_mid, tone_left - 18.0, 0.0])
                center_nodes.append([t_post, tone_left, 0.0])
        elif diff > 0 and diff < 280:
            # Small upward: smooth S-curve 100-140ms
            t_lead = min(0.065, 0.35 * dur_left)
            t_lag = min(0.075, 0.40 * dur_right)
            t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
            t_arrive = round(b_s + t_lag, 6)
            t_mid = round(0.5 * (t_depart + t_arrive), 6)
            slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.35, 2)
            center_nodes.append([t_depart, tone_left, 0.0])
            center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
            center_nodes.append([t_arrive, tone_right, 0.0])
        elif diff >= 280:
            # Large upward (3-9 semitones): two-stage terrace if sufficient duration
            if dur_left >= 0.16 and dur_right >= 0.22:
                r = 130.0 + min(60.0, 10.0 * (diff / 100.0 - 3.0))
                T_terrace = tone_right - r
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - min(0.085, 0.32 * dur_left)), 6)
                t_terrace_in = round(b_s + min(0.020, 0.08 * dur_right), 6)
                t_terrace_out = round(b_s + min(0.080, 0.30 * dur_right), 6)
                t_arrive = round(b_s + min(0.145, 0.50 * dur_right), 6)
                slope_1 = round((T_terrace - tone_left) / max(0.03, t_terrace_in - t_depart) * 1.25, 2)
                slope_2 = round((tone_right - (T_terrace + 10.0)) / max(0.03, t_arrive - t_terrace_out) * 1.25, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([round(0.5 * (t_depart + t_terrace_in), 6), round(0.5 * (tone_left + T_terrace), 2), slope_1])
                center_nodes.append([t_terrace_in, T_terrace, 20.0])
                center_nodes.append([t_terrace_out, T_terrace + 10.0, 30.0])
                center_nodes.append([round(0.5 * (t_terrace_out + t_arrive), 6), round(0.5 * (T_terrace + 10.0 + tone_right), 2), slope_2])
                center_nodes.append([t_arrive, tone_right, 0.0])
            else:
                t_lead = min(0.080, 0.38 * dur_left)
                t_lag = min(0.090, 0.42 * dur_right)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_arrive = round(b_s + t_lag, 6)
                t_mid = round(0.5 * (t_depart + t_arrive), 6)
                slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.4, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
                center_nodes.append([t_arrive, tone_right, 0.0])
        else:
            # Downward: diff < 0
            if abs(diff) >= 350 and dur_right >= 0.25:
                # Large downward: slide down with gentle undershoot & recovery
                t_lead = min(0.070, 0.32 * dur_left)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_pass = round(b_s + min(0.035, 0.15 * dur_right), 6)
                t_dip = round(b_s + min(0.085, 0.32 * dur_right), 6)
                t_recover = round(b_s + min(0.145, 0.50 * dur_right), 6)
                dip_c = 32.0
                slope_down = round((diff - dip_c) / max(0.04, t_dip - t_depart) * 1.2, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_pass, round(0.5 * (tone_left + tone_right), 2), slope_down])
                center_nodes.append([t_dip, round(tone_right - dip_c, 2), 0.0])
                center_nodes.append([t_recover, tone_right, 0.0])
            else:
                t_lead = min(0.060, 0.32 * dur_left)
                t_lag = min(0.075, 0.38 * dur_right)
                t_depart = round(max(center_nodes[-1][0] + 0.015, b_s - t_lead), 6)
                t_arrive = round(b_s + t_lag, 6)
                t_mid = round(0.5 * (t_depart + t_arrive), 6)
                slope_mid = round((diff / max(0.04, t_arrive - t_depart)) * 1.35, 2)
                center_nodes.append([t_depart, tone_left, 0.0])
                center_nodes.append([t_mid, round(0.5 * (tone_left + tone_right), 2), slope_mid])
                center_nodes.append([t_arrive, tone_right, 0.0])

    if p_end_s > center_nodes[-1][0] + 0.010:
        center_nodes.append([p_end_s, n_spans[-1][2], 0.0])
    else:
        center_nodes[-1][0] = p_end_s
    return center_nodes

nodes = build_natural_center_nodes(p_start_s, p_end_s, n_spans)
print(f'Generated {len(nodes)} natural center nodes for phrase 0:')
for n in nodes:
    print(f'  [{n[0]:.4f}s, {n[1]:.1f}c, slope={n[2]:.1f}]')
