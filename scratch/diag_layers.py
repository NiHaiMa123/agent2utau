import sys, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx, TempoMap

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'

def load(p):
    d = np.load(p)
    return d['times'], d['f0_hz'], d['voiced']

def midi(hz):
    return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

s_t, s_fc, s_vfc = load(f'{RUN}/observation/fcpe.npz')
_, s_rm, s_vrm = load(f'{RUN}/observation/rmvpe.npz')
r_t, r_fc, r_vfc = load('scratch/render_fcpe.npz')
_, r_rm, r_vrm = load('scratch/render_rmvpe.npz')

src_fc, src_rm = midi(s_fc), midi(s_rm)
rnd_fc = midi(np.interp(s_t, r_t, r_fc))
r_vfc_i = np.interp(s_t, r_t, r_vfc.astype(float)) > 0.5
r_vrm_i = np.interp(s_t, r_t, r_vrm.astype(float)) > 0.5
rnd_rm = midi(np.interp(s_t, r_t, r_rm))

doc = load_ustx(f'{RUN}/compiled/project.ustx')
tm = TempoMap.from_doc(doc)

# Build per-frame label: which note, and position within note (fraction)
note_ok_mid = np.zeros(len(s_t), bool)   # middle 40% of a sung note
note_ok_edge = np.zeros(len(s_t), bool)  # first/last 25%
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP', 'SP', '+'):
            continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        d = b-a
        m_mid = (s_t >= a+0.30*d) & (s_t < b-0.30*d)
        m_edge = ((s_t >= a) & (s_t < a+0.25*d)) | ((s_t >= b-0.25*d) & (s_t < b))
        note_ok_mid |= m_mid
        note_ok_edge |= m_edge

valid = s_vfc & s_vrm & r_vfc_i & r_vrm_i & (s_t > 18) & (s_t < 243)
for label, mask in (('note MIDDLE 40%', valid & note_ok_mid),
                    ('note EDGES 25%', valid & note_ok_edge),
                    ('NOT in any sung note', valid & ~note_ok_mid & ~note_ok_edge)):
    if mask.sum() < 20:
        print(label, 'too few'); continue
    d = (rnd_fc - src_fc)[mask]*100
    print(f'{label:22s} n={mask.sum():5d}  med|Δ|={np.median(np.abs(d)):6.1f}c  p90={np.percentile(np.abs(d),90):6.1f}  >100c={(np.abs(d)>100).mean():6.1%}')

# Detector agreement on the render itself (is the render noisy/creaky?)
both_r = r_vfc_i & r_vrm_i
disagree = (np.abs(rnd_fc - rnd_rm) > 100) & both_r & (s_t > 18) & (s_t < 243)
print(f'\nrender internal detector disagreement >100c: {disagree.mean():.2%} of frames')

# Source vibrato/glide content in middle segments: how much does source itself move?
print('\nsource F0 local motion (middle 40% of notes), per 50ms window:')
mv = []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        d = b-a
        m = (s_t >= a+0.3*d) & (s_t < b-0.3*d) & s_vfc & s_vrm
        if m.sum() > 8:
            v = src_fc[m]*100
            mv.append(np.percentile(v,95)-np.percentile(v,5))
mv = np.array(mv)
print(f'  n={len(mv)}  median {np.median(mv):.0f}c  p90 {np.percentile(mv,90):.0f}c  max {mv.max():.0f}c')
