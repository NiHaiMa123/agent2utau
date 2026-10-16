"""Independent mathematical checks of sealed input/prediction arrays only."""
import math
import numpy as np

CHANNELS = ('breathiness', 'voicing', 'tension')
COMMON = ('position_ms', 'frame_ms', 'head_frames', 'tail_frames', 'sample_rate',
    'singer_location', 'acoustic_model', 'vocoder_model', 'acoustic_mel_base', 'vocoder_mel_base', 'phones', 'vocoder_f0')
VAR_COMMON = ('frame_ms', 'head_frames', 'tail_frames', 'variance_model',
    'variance_speaker_root', 'native_linguistic_cache', 'linguistic_tensors')


def tensors(record):
    assert len({v['name'] for v in record['tensors']}) == len(record['tensors'])
    result = {v['name']: np.asarray(v['values'], dtype=v['dtype']).reshape(v['shape']) for v in record['tensors']}
    assert all(np.isfinite(v).all() for v in result.values())
    return result


def changed(a, b):
    assert set(a) == set(b)
    assert all(a[k].shape == b[k].shape and a[k].dtype == b[k].dtype for k in a)
    return sorted(k for k in a if not np.array_equal(a[k], b[k]))


def clock(record, frames):
    return (record['position_ms'] + (np.arange(frames) - record['head_frames']) * record['frame_ms']) / 1000


def arithmetic(record, inputs, predictions):
    clipped = {}
    for k in CHANNELS:
        limits = (-10, 10) if k == 'tension' else (-96, 0)
        base = np.asarray(predictions[k + '_pred'], np.float32)
        delta = np.asarray(record['expression_deltas'][k], np.float32)[None, :]
        assert base.shape == delta.shape == inputs[k].shape
        raw = base + delta
        assert np.array_equal(np.clip(raw, *limits), inputs[k]), ('arithmetic', k)
        clipped[k] = int(np.count_nonzero((raw < limits[0]) | (raw > limits[1])))
    return clipped


def finite_support(a, b, support, times):
    ix = np.flatnonzero(a.ravel() != b.ravel())
    assert len(ix) and np.all(times[ix] >= support[0]) and np.all(times[ix] <= support[1]), 'finite support'
    return dict(changed_frames=len(ix), actual_support_s=times[ix[[0, -1]]].tolist())


def check_native(a, b, va, vb, operation, support, peak=None, unshifted_variance_pitch=None):
    aa, bb, av, bv = [tensors(r) for r in (a, b, va, vb)]
    for key in COMMON:
        assert a[key] == b[key], ('native invariant', key)
    for key in VAR_COMMON:
        assert va[key] == vb[key], ('variance invariant', key)
    assert a['frame_ms'] == va['frame_ms'] and a['head_frames'] == va['head_frames']
    times = clock(a, aa['f0'].size)
    nc, vc = changed(aa, bb), changed(av, bv)
    deltas = [{k: np.asarray(r['expression_deltas'][k], np.float32) for k in CHANNELS} for r in (a, b)]
    if operation in ['tension_cancel', 'breathiness_delta']:
        selected = 'tension' if operation == 'tension_cancel' else 'breathiness'
        assert nc == [selected] and not vc
        assert va == vb, 'manual intervention variance metadata changed'
        for k in CHANNELS:
            if k != selected:
                assert np.array_equal(deltas[0][k], deltas[1][k])
        actual = finite_support(aa[selected], bb[selected], support, times)
        manual = finite_support(deltas[0][selected], deltas[1][selected], support, times)
        if operation == 'tension_cancel':
            assert np.all(deltas[1][selected][deltas[0][selected] != deltas[1][selected]] == 0)
        else:
            assert np.min(deltas[1][selected] - deltas[0][selected]) < 0
            assert np.max(deltas[1][selected] - deltas[0][selected]) == 0
    else:
        assert 'f0' in nc and set(nc) <= {'f0', *CHANNELS} and vc == ['pitch']
        for k in CHANNELS:
            assert np.array_equal(deltas[0][k], deltas[1][k]), ('manual channel changed', k)
        for record, variance, inputs, vt in [(a, va, aa, av), (b, vb, bb, bv)]:
            cents = np.asarray(record['tone_shift_cents'], np.float32)
            semitones = np.asarray(variance['tone_shift_semitones'], np.float32)
            assert cents.shape == semitones.shape == times.shape
            assert np.max(np.abs(semitones.astype(np.float64) * 100 - cents)) <= .00005
            unshifted = np.asarray(record['vocoder_f0'], np.float32)[None, :]
            # Exact native float32 division precedes Math.Pow's double input.
            factor = np.asarray([math.pow(2, float(v)) for v in cents / np.float32(1200)], np.float32)[None, :]
            assert np.array_equal(inputs['f0'], unshifted * factor), 'SHFC float32 native transform'
        sa, sb = [np.asarray(r['tone_shift_cents'], np.float32) for r in (a, b)]
        shift_a, shift_b = [np.asarray(r['tone_shift_semitones'], np.float32)[None, :] for r in (va, vb)]
        base_pitch = av['pitch'] if unshifted_variance_pitch is None else unshifted_variance_pitch
        assert np.array_equal(av['pitch'], base_pitch + shift_a), 'reference variance pitch transform'
        assert np.array_equal(bv['pitch'], base_pitch + shift_b), 'intervention variance pitch transform'
        assert np.min(sb) == peak and np.max(sb) <= 0 and np.all(sb >= peak)
        actual = finite_support(sa, sb, support, times)
        manual = dict(changed_manual_channels=[], sampled_peak_cents=float(sb.min()))
        if operation == 'shfc_onset':
            attack_end = 183.87645833333335
            assert np.array_equal(sa[times >= attack_end], sb[times >= attack_end]), 'platform/exit changed'
        else:
            assert not np.any(sa)
    for r, ts in [(a, aa), (b, bb)]:
        native_pred = {k + '_pred': np.asarray(r['native_variance_predictions'][k], np.float32)[None, :] for k in CHANNELS}
        arithmetic(r, ts, native_pred)
    return dict(changed_native_inputs=nc, changed_variance_inputs=vc, finite_support=actual,
        manual_check=manual, native_arithmetic_exact=True, vocoder_F0_exact=True,
        cache_verified_flags_from_historical_export=[a['native_acoustic_cache_verified'], b['native_acoustic_cache_verified'], va['native_variance_cache_verified'], vb['native_variance_cache_verified']],
        current_cache_or_engine_execution_verified=False)


def check_fresh(a, b, ia, ib, pa, pb, operation, repeat_inputs, repeat_prediction):
    native_a, native_b = tensors(a), tensors(b)
    changes, prediction_changes = changed(ia, ib), changed(pa, pb)
    allowed = {'f0', *CHANNELS} if operation.startswith('shfc') else {'tension' if operation == 'tension_cancel' else 'breathiness'}
    assert set(changes) <= allowed and changes
    if operation.startswith('shfc'):
        assert 'f0' in changes
    else:
        assert set(changes) == allowed and not prediction_changes
    assert not changed(ia, repeat_inputs) and not changed(pa, repeat_prediction), 'repeat input/prediction mismatch'
    for native, fresh in [(native_a, ia), (native_b, ib)]:
        assert set(fresh) == set(native) | {'probe_noise'}
        for k in native.keys() - set(CHANNELS):
            assert np.array_equal(native[k], fresh[k]), ('fresh direct input', k)
    clipped_a, clipped_b = arithmetic(a, ia, pa), arithmetic(b, ib, pb)
    delta_stats = {}
    for k in CHANNELS:
        d = ib[k] - ia[k]
        delta_stats[k] = dict(min=float(d.min()), max=float(d.max()), changed_frames=int(np.count_nonzero(d)))
    assert np.array_equal(ia['probe_noise'], ib['probe_noise'])
    return dict(changed_final_inputs=changes, changed_predictions=prediction_changes,
        final_float32_arithmetic_exact=True, repeat_input_and_prediction_exact=True,
        clipping_counts_A=clipped_a, clipping_counts_intervention=clipped_b,
        final_channel_delta_stats=delta_stats, current_model_or_waveform_repeat_execution=False,
        speaker_tensor_and_acoustic_noise_exact=True,
        speaker_embedding_contents_or_current_install_revalidated=False)
