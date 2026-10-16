"""Independent polynomial/native sampling, model dependency and repeat checks."""
import copy
import math
from pathlib import Path
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT, load, save, ref, check
from lastpage_own_li_entry_pitch_20261013 import RUN, F, CHANNELS
from check_lastpage_own_bright_cute_20261012 import read, native_mix
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge


def polynomial(t, nodes):
    for (a, y0, d0), (b, y1, d1) in zip(nodes, nodes[1:]):
        if a <= t <= b:
            h = b-a
            u = (t-a)/h
            p1 = h*d0
            p2 = 3*(y1-y0)-h*(2*d0+d1)
            p3 = 2*(y0-y1)+h*(d0+d1)
            return ((p3*u+p2)*u+p1)*u+y0
    raise ValueError(t)


def reconstruct_frames(doc, q, record):
    tm = TempoMap.from_doc(doc)
    grid = np.asarray(q['final_cents'], np.float32)
    period = float(np.float32(record['frame_ms']))
    origin = record['position_ms']-record['head_frames']*period
    n = tensors(record['tensors'])['f0'].size
    values, clocks = [], []
    for i in range(n):
        ms = origin+i*period
        tick = round(tm.ms_to_tick(ms))
        x = (tick-q['pitch_start_tick'])/5
        if x <= 0:
            y = float(grid[0])
        elif x >= len(grid)-1:
            y = float(grid[-1])
        else:
            k = math.floor(x)
            # Bound SampleCurve IL subtracts float32, then interpolates double.
            y = float(grid[k])+float(np.float32(grid[k+1]-grid[k]))*(x-k)
        values.append(y)
        clocks.append(ms/1000)
    cents = np.asarray(values, np.float64)
    pitch = (cents*.01).astype(np.float32)
    f0 = np.asarray([np.float32(440*math.pow(2, (c*.01-69)/12)) for c in cents], np.float32)
    return pitch, f0, np.asarray(clocks)


def phone_identity(obj):
    obj = copy.deepcopy(obj)
    for part in obj['parts']:
        for phrase in part['phrases']:
            phrase.pop('final_cents')
    return obj['parts']


def native():
    plan = load(RUN/'design/protocol.json')
    check([plan[k] for k in ['baseline_score', 'candidate', 'native_score']]+plan['model_adapters']+plan['source_bindings'])
    _, receipt = check_plan_knowledge(plan, RUN/'design/protocol.json')
    assert receipt == load(RUN/'evaluation/knowledge_receipt.json')
    base = yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'))
    doc = yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'))
    restored = copy.deepcopy(doc)
    old = next(c for c in base['voice_parts'][28]['curves'] if c['abbr'] == 'pitd')
    curve = next(c for c in doc['voice_parts'][28]['curves'] if c['abbr'] == 'pitd')
    assert curve['xs'] == old['xs']
    next(c for c in restored['voice_parts'][28]['curves'] if c['abbr'] == 'pitd')['ys'] = old['ys']
    assert restored == base
    tm = TempoMap.from_doc(doc)
    nodes = plan['gesture']['center_nodes']
    lo, hi = plan['gesture']['support_s']
    old_pitch = load(F/'native-inputs/F-pitch.json')['phrases']
    new_pitch = load(RUN/'native-inputs/J-pitch.json')['phrases']
    assert phone_identity(load(F/'native-inputs/F-phones.json')) == phone_identity(load(RUN/'native-inputs/J-phones.json'))
    rt = yaml.safe_load((RUN/'native-inputs/J-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    written = yaml.safe_load((RUN/'score/native_J.ustx').read_text(encoding='utf-8-sig'))
    assert rt['voice_parts'][0]['curves'] == written['voice_parts'][0]['curves'] and rt['voice_parts'][1]['curves'] == written['voice_parts'][1]['curves']
    loaded_F = yaml.safe_load((F/'native-inputs/F-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for p, q in zip(rt['voice_parts'], loaded_F['voice_parts']):
        assert p['notes'] == q['notes']
        for a, b in zip(p['notes'], q['notes']):
            assert a['pitch'] == b['pitch'] and a['tone'] == b['tone']
    errors = []
    for i, x in enumerate(curve['xs']):
        sec = tm.tick_to_ms(doc['voice_parts'][28]['position']+x)/1000
        if lo <= sec <= hi:
            target = polynomial(sec, nodes)
            expected = int(np.rint(target-old_pitch[0]['before_pitd_cents'][i]))
            assert curve['ys'][i] == expected
            errors.append(abs(new_pitch[0]['final_cents'][i]-target))
        else:
            assert curve['ys'][i] == old['ys'][i]
    assert errors and max(errors) <= .501
    rows = []
    for j, ctx in enumerate([28, 29]):
        a, b = old_pitch[j], new_pitch[j]
        for k in a:
            if k != 'final_cents':
                assert a[k] == b[k], (ctx, k)
        changed_grid = np.asarray(a['final_cents']) != np.asarray(b['final_cents'])
        times = np.asarray(a['times_ms'])/1000
        if ctx == 28:
            assert changed_grid.any() and np.all(~changed_grid | ((times >= lo) & (times <= hi)))
        else:
            assert not changed_grid.any()
        records = [load(p) for p in [F/f'native-inputs/F/phrase_{j:03}.json', RUN/f'native-inputs/J/phrase_{j:03}.json',
            F/f'native-inputs/F/variance_{j:03}.json', RUN/f'native-inputs/J/variance_{j:03}.json']]
        fa, fb, va, vb = records
        ac, bc, av, bv = [tensors(r['tensors']) for r in records]
        assert fb['native_acoustic_cache_verified'] and vb['native_variance_cache_verified']
        for k in ['position_ms', 'frame_ms', 'head_frames', 'tail_frames', 'sample_rate', 'phones', 'expression_deltas',
                  'tone_shift_cents', 'singer_location', 'acoustic_model', 'vocoder_model']:
            assert fa[k] == fb[k], (ctx, k)
        assert all(not np.asarray(fb['expression_deltas'][c]).any() for c in CHANNELS)
        for r, inp, key in [(fb, bc, 'singer_location'), (vb, bv, 'variance_speaker_root')]:
            mix, _ = native_mix(Path(r[key]), 'E', fb['phones'])
            assert np.array_equal(inp['spk_embed'], np.broadcast_to(mix, inp['spk_embed'].shape))
        ca = [k for k in ac if not np.array_equal(ac[k], bc[k])]
        cv = [k for k in av if not np.array_equal(av[k], bv[k])]
        if ctx == 28:
            assert cv == ['pitch'] and 'f0' in ca and set(ca).issubset({'f0', *CHANNELS})
        else:
            assert ca == cv == []
        for q, frame, var in [(a, fa, av), (b, fb, bv)]:
            pitch, f0, clock = reconstruct_frames(doc, q, frame)
            assert np.array_equal(pitch, var['pitch'].ravel())
            assert np.array_equal(f0, np.asarray(frame['vocoder_f0'], np.float32))
            assert np.array_equal(f0, tensors(frame['tensors'])['f0'].ravel())
        frame_mask = av['pitch'].ravel() != bv['pitch'].ravel()
        if ctx == 28:
            # Interpolation can affect the neighboring grid segment, not just changed grid points.
            first, last = np.flatnonzero(changed_grid)[[0, -1]]
            allowed = [times[first-1] if first else times[first], times[last+1] if last+1 < len(times) else times[last]]
            sampled_clock = np.asarray([tm.tick_to_ms(round(tm.ms_to_tick(t*1000)))/1000 for t in clock])
            assert np.all(~frame_mask | ((sampled_clock >= allowed[0]-1e-9) & (sampled_clock <= allowed[1]+1e-9)))
        else:
            allowed = None
        for ch in CHANNELS:
            p = np.asarray(fb['native_variance_predictions'][ch], np.float32)[None, :]
            limits = (-10, 10) if ch == 'tension' else (-96, 0)
            assert np.array_equal(bc[ch], np.clip(p, *limits))
            assert not np.count_nonzero((p < limits[0]) | (p > limits[1]))
        rows.append(dict(context=ctx, changed_pitch_grid_points=int(changed_grid.sum()), changed_pitch_model_frames=int(frame_mask.sum()),
            max_final_pitch_delta_cents=float(np.max(np.abs(np.asarray(a['final_cents'])-b['final_cents']))),
            actual_grid_support_s=[float(times[changed_grid][0]), float(times[changed_grid][-1])] if changed_grid.any() else None,
            model_interpolation_allowed_support_s=allowed, changed_native_acoustic=ca, changed_native_variance=cv,
            phone_clock_and_both_speaker_exact_F=True, pitch_and_both_F0_paths_reconstructed_exact=True))
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/native-independent-check.json', dict(status='passed', rows=rows,
        native_target_max_error_cents=max(errors), checker=ref(Path(__file__)),
        arithmetic_source=ref(ROOT/'runs/research/table2-2e-native-check-20261010/core-metadata.json'),
        knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'), measurement_validated=False))
    print('J native target, phone identity, two-stage speaker and full pitch dependency gate passed.', flush=True)


def fresh():
    f = load(RUN/'native-inputs/J/phrase_000.json')
    v = load(RUN/'native-inputs/J/variance_000.json')
    old = {k: read(F/f'fresh/context28/F/{k}.npz') for k in ['inputs', 'variance-inputs', 'predictions', 'vocoder-f0']}
    values, pred_changes, clipping = [], [], {}
    for label in ['J', 'J_repeat']:
        d = RUN/f'fresh/context28/{label}'
        data = {k: read(d/(k+'.npz')) for k in ['inputs', 'variance-inputs', 'predictions', 'mel', 'vocoder-f0']}
        data['wave'] = np.load(d/'raw.npy', allow_pickle=False)
        ac, va = tensors(f['tensors']), tensors(v['tensors'])
        n = ac['f0'].size
        assert all(np.array_equal(data['variance-inputs'][k], va[k]) for k in va)
        assert all(np.array_equal(data['inputs'][k], ac[k]) for k in ac if k not in CHANNELS)
        assert np.array_equal(data['variance-inputs']['probe_noise'], gaussian_frame_noise(11, 3, 24, n))
        assert np.array_equal(data['inputs']['probe_noise'], gaussian_frame_noise(101, 1, 128, n))
        assert np.array_equal(data['vocoder-f0']['f0'], np.asarray(f['vocoder_f0'], np.float32)[None, :])
        changed_var = [k for k in old['variance-inputs'] if not np.array_equal(old['variance-inputs'][k], data['variance-inputs'][k])]
        assert changed_var == ['pitch']
        changed_ac = [k for k in old['inputs'] if not np.array_equal(old['inputs'][k], data['inputs'][k])]
        assert 'f0' in changed_ac and set(changed_ac).issubset({'f0', *CHANNELS})
        pred_changes = [k for k in old['predictions'] if not np.array_equal(old['predictions'][k], data['predictions'][k])]
        assert pred_changes
        for ch in CHANNELS:
            raw = data['predictions'][ch+'_pred'] + np.asarray(f['expression_deltas'][ch], np.float32)[None, :]
            limits = (-10, 10) if ch == 'tension' else (-96, 0)
            assert np.array_equal(data['inputs'][ch], np.clip(raw, *limits))
            clipping[ch] = int(np.count_nonzero((raw < limits[0]) | (raw > limits[1])))
        assert not any(clipping.values())
        assert data['wave'].dtype == np.float32 and len(data['wave']) == n*512 and np.isfinite(data['wave']).all()
        values.append(data)
    a, b = values
    assert np.array_equal(a['wave'], b['wave'])
    for k in ['inputs', 'variance-inputs', 'predictions', 'mel', 'vocoder-f0']:
        assert all(np.array_equal(a[k][q], b[k][q]) for q in a[k])
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/fresh-independent-check.json', dict(status='passed', checker=ref(Path(__file__)),
        rows=[dict(context=28, repeat_exact=True, changed_vs_F=changed_ac, changed_variance=['pitch'], rebuilt_changed_predictions=pred_changes,
            manual_deltas_zero=True, feature_clipping=clipping)], new_waveforms=2,
        context29='sealed F reuse, native feeds independently verified exact', measurement_validated=False))
    print('J repeat exact; new pitch-conditioned predictions rebuilt, clipping0.', flush=True)


if __name__ == '__main__':
    {'native': native, 'fresh': fresh}[sys.argv[1]]()
