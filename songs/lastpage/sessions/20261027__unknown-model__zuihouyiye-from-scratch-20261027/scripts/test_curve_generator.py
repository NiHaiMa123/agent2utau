import numpy as np
from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
tm = TempoMap.from_doc(doc)

def generate_part_curves(vp):
    pos = vp['position']
    notes = vp.get('notes', [])
    if not notes:
        return []

    # Sample points every 20 ticks (approx 10ms at 120bpm, 480 ticks/beat)
    # Part start and end
    p_start_tick = notes[0]['position']
    p_end_tick = notes[-1]['position'] + notes[-1]['duration']

    ticks = []
    voic_vals = []
    tenc_vals = []
    brec_vals = []

    for ni, n in enumerate(notes):
        n_pos = n['position']
        n_dur = n['duration']
        n_end = n_pos + n_dur
        tone = n['tone']
        lyric = n.get('lyric', '')

        # Determine target parameters for this note
        if lyric in ('AP', 'SP'):
            v_target = 100
            t_target = 0
            b_target = 0
        elif tone >= 72:
            # High note (falsetto / head-voice): C#5
            v_target = 98
            t_target = -14
            b_target = 20
        elif tone >= 67:
            # Upper mid register: G4 to B4
            v_target = 110
            t_target = 0
            b_target = -4
        else:
            # Chest / lower register: <= 66
            v_target = 120
            t_target = 6
            b_target = -12

        # Check if long sustained note (dur > 1500 ticks)
        is_long_tail = (n_dur >= 1400) and (lyric not in ('AP', 'SP'))

        # Add key points inside note
        # Attack (first 10% or 40 ticks)
        # Body
        # Release (last 15% or 60 ticks)
        t_in = n_pos + min(40, int(0.15 * n_dur))
        t_out = n_end - min(60, int(0.20 * n_dur))

        if is_long_tail:
            # Starts with target, relaxes into soft breath at tail
            t_mid = n_pos + int(0.45 * n_dur)
            ticks.extend([n_pos, t_in, t_mid, t_out, n_end])
            voic_vals.extend([v_target, v_target, max(100, v_target - 8), max(96, v_target - 14), 100])
            tenc_vals.extend([t_target, t_target, t_target - 8, -12, 0])
            brec_vals.extend([b_target, b_target, b_target + 12, b_target + 20, 0])
        else:
            ticks.extend([n_pos, t_in, t_out, n_end])
            voic_vals.extend([v_target, v_target, v_target, v_target])
            tenc_vals.extend([t_target, t_target, t_target, t_target])
            brec_vals.extend([b_target, b_target, b_target, b_target])

    # Sort and remove duplicate ticks
    combined = sorted(zip(ticks, voic_vals, tenc_vals, brec_vals), key=lambda x: x[0])
    u_ticks, u_voic, u_tenc, u_brec = [], [], [], []
    for t, v, te, b in combined:
        if not u_ticks or t > u_ticks[-1]:
            u_ticks.append(int(t))
            u_voic.append(int(round(v)))
            u_tenc.append(int(round(te)))
            u_brec.append(int(round(b)))
        else:
            # Overwrite with average
            u_voic[-1] = int(round(0.5 * (u_voic[-1] + v)))
            u_tenc[-1] = int(round(0.5 * (u_tenc[-1] + te)))
            u_brec[-1] = int(round(0.5 * (u_brec[-1] + b)))

    curves = [
        {"abbr": "voic", "xs": u_ticks, "ys": u_voic},
        {"abbr": "brec", "xs": u_ticks, "ys": u_brec},
        {"abbr": "tenc", "xs": u_ticks, "ys": u_tenc},
    ]
    return curves

for pi in [9, 10, 11, 12]:
    vp = doc['voice_parts'][pi]
    curves = generate_part_curves(vp)
    print(f"=== Part {pi} ({vp['name']}) ===")
    for c in curves:
        print(f"  {c['abbr']}: {len(c['xs'])} pts, min={min(c['ys'])}, max={max(c['ys'])}")
        # print high note points
        for x, y in zip(c['xs'], c['ys']):
            if y < -5 or y > 15 or y > 115 or y < 99:
                pass
