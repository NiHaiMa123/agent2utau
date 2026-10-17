"""Two-call-per-repeat fresh predictor -> four research acoustic-input paths.

Pure array preparation and raw render callbacks; no CLI, weight loading, native
export, or audio writes. Actual execution and provenance require separate checks.
"""
import hashlib
import json
from pathlib import Path
import numpy as np

from agent2utau.evaluation.controlled_probe import tensors, require_shift_isolation
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from shfc_path_adapter import FreshPrediction, assemble_paths, tensor_binding, CHANNELS
from shfc_path_checks import check_paths, check_repetition


def load_sealed_protocol():
    root = Path(__file__).resolve().parents[2]
    seal = json.loads((root / 'research/table2-confirmation/stage_2d_protocol_binding.json').read_text(encoding='utf-8'))
    for ref in seal['bindings']:
        if hashlib.sha256((root / ref['path']).read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('Frozen protocol or design SHA changed')
    p = json.loads((root / 'docs/knowledge/acoustic-manifestations-20261009/validation-protocols/shfc-path-separation-v1.json').read_text(encoding='utf-8'))
    if p['id'] != 'T2D-SHFC-PATHS-01' or p['version'] != 1 or p['budget']['total_acoustic_vocoder_waveforms'] != 16:
        raise ValueError('Only the sealed finite protocol is supported')
    return p


def prepare_condition(native_a, native_s, variance_a, variance_s, case, *, batch_id, predict):
    """Callable predictor receives copied native conditions + fixed seed noise.

    Returns exactly two prepared repetitions; never accepts cached prediction
    arrays as public runner arguments. A supplied callable is not proof of ONNX.
    """
    if not batch_id:
        raise ValueError('Explicit new batch ID required')
    if case not in load_sealed_protocol()['cases']:
        raise ValueError('Condition or geometry differs from frozen protocol')
    condition_id = case['condition']['id']
    isolation = require_shift_isolation(native_a, native_s, variance_a, variance_s,
        case['shifted_support_s'], case['peak_cents'])
    base, shifted, va, vs = [tensors(r['tensors']) for r in (native_a, native_s, variance_a, variance_s)]
    for group in (base, shifted, va, vs):
        tensor_binding(group)
    frames = base['f0'].size
    if native_a['frame_ms'] != variance_a['frame_ms'] or native_a['head_frames'] != variance_a['head_frames'] or native_a['tail_frames'] != variance_a['tail_frames']:
        raise ValueError('Resampled variance layout unsupported')
    if native_a['sample_rate'] != 44100 or np.float32(native_a['frame_ms']) != np.float32(512 / 44100 * 1000):
        raise ValueError('Frozen 44100/512 clock required')
    for group in (base, shifted):
        if 'steps' not in group or 'depth' not in group or group['steps'].size != 1 or group['steps'].dtype.kind not in 'iu' or group['depth'].size != 1 or group['depth'].dtype != np.float32 or not np.all(group['steps'] == 20) or not np.all(group['depth'] == np.float32(.6)):
            raise ValueError('Frozen steps20/depth0.6 required')
    manual = {k: np.asarray(native_a['expression_deltas'][k], np.float32)[None, :] for k in CHANNELS}
    acoustic_noise = gaussian_frame_noise(101, 1, 128, frames)
    variance_noise = gaussian_frame_noise(11, 3, 24, frames)
    vocoder_f0 = np.asarray(native_a['vocoder_f0'], np.float32)[None, :]
    prepared = []
    for repetition in (0, 1):
        predictions, conditioning_bindings = {}, {}
        for source, original in (('A', va), ('S', vs)):
            values = {k: v.copy() for k, v in original.items()}
            if 'probe_noise' in values:
                raise ValueError('Existing stochastic input not accepted')
            values['probe_noise'] = variance_noise.copy()
            h = tensor_binding(values)
            outputs = predict({k: v.copy() for k, v in values.items()})
            # Rebind/copy immediately: callbacks retaining/mutating returned
            # arrays cannot change already prepared variants or first draws.
            outputs = {k: np.asarray(v).copy() for k, v in outputs.items()}
            predictions[source] = FreshPrediction(batch_id, condition_id, source, repetition, h, outputs)
            conditioning_bindings[source] = h
        paths = assemble_paths(base, shifted, manual, predictions, batch_id=batch_id,
            condition_id=condition_id, repetition=repetition, conditioning_bindings=conditioning_bindings,
            acoustic_noise=acoustic_noise, vocoder_f0=vocoder_f0)
        check = check_paths(paths, base, shifted, manual, predictions, acoustic_noise, vocoder_f0,
            batch_id=batch_id, condition_id=condition_id, repetition=repetition, conditioning_bindings=conditioning_bindings)
        prepared.append(dict(batch_id=batch_id, condition_id=condition_id, predictions=predictions,
            paths=paths, checks=check, reconstruction=dict(base={k:v.copy() for k,v in base.items()},
                shifted={k:v.copy() for k,v in shifted.items()},manual={k:v.copy() for k,v in manual.items()},
                acoustic_noise=acoustic_noise.copy(),vocoder_f0=vocoder_f0.copy(),conditioning_bindings=dict(conditioning_bindings))))
    repeat = check_repetition(*prepared)
    return dict(condition_id=condition_id, repetitions=prepared, native_isolation=isolation,
        repeat_checks=repeat, predictor_calls=4, prepared_acoustic_inputs=8,
        fresh_model_execution_verified=False, acoustic_vocoder_calls=0, new_audio=0,
        native_sampling_matches_frozen_Q5_verified=False, actual_speaker_embeddings_verified=False,
        source_project_or_target_phone_identity_verified=False)


def prepare_batch(native_conditions, *, batch_id, predict):
    """Exactly the sealed two conditions; reject omissions/extra conditions."""
    cases = load_sealed_protocol()['cases']
    expected = {c['condition']['id'] for c in cases}
    if set(native_conditions) != expected:
        raise ValueError('Both and only frozen conditions required')
    result = [prepare_condition(*native_conditions[c['condition']['id']], c,
        batch_id=batch_id, predict=predict) for c in cases]
    return dict(batch_id=batch_id, conditions=result, predictor_calls=8,
        prepared_acoustic_inputs=16, independent_effect_replications=0,
        model_execution_verified=False, rendered_waveforms=0, listening_status='not_started')


def render_prepared_batch(prepared, *, render):
    """Future explicit backend integration: finite raw in-memory waveforms.

    Does not apply DYN/gain, encode audio, or deliver listening files. Not called
    for current preparation, even if native templates happen to be available.
    """
    cases = load_sealed_protocol()['cases']
    if [r['condition_id'] for r in prepared['conditions']] != [c['condition']['id'] for c in cases]:
        raise ValueError('Render batch does not match frozen conditions')
    results = []
    for condition in prepared['conditions']:
        if len(condition['repetitions']) != 2:
            raise ValueError('Two exact prepared repetitions required')
        check_repetition(*condition['repetitions'])
        repeats = []
        for repetition in condition['repetitions']:
            proof = repetition['reconstruction']
            check_paths(repetition['paths'],proof['base'],proof['shifted'],proof['manual'],
                repetition['predictions'],proof['acoustic_noise'],proof['vocoder_f0'],
                batch_id=repetition['batch_id'],condition_id=repetition['condition_id'],
                repetition=repetition['paths']['A']['repetition'],conditioning_bindings=proof['conditioning_bindings'])
            variants = {}
            for label in ('A', 'S', 'D', 'P'):
                row = repetition['paths'][label]
                mel, wave = render({k:v.copy() for k,v in row['inputs'].items()}, row['vocoder_f0'].copy(), condition['condition_id'])
                mel, wave = np.asarray(mel).copy(), np.asarray(wave).copy()
                if mel.dtype != np.float32 or wave.dtype != np.float32 or mel.ndim != 3 or mel.shape[0] != 1 or mel.shape[1] != row['inputs']['f0'].shape[1] or mel.shape[2] != 128 or wave.ndim != 1 or not wave.size or not np.isfinite(mel).all() or not np.isfinite(wave).all() or np.max(np.abs(wave)) >= 1:
                    raise ValueError('Invalid/nonfinite/fullscale raw backend output')
                variants[label] = dict(mel=mel, wave=wave)
            repeats.append(variants)
        for label in ('A','S','D','P'):
            for key in ('mel','wave'):
                a,b = repeats[0][label][key],repeats[1][label][key]
                if a.dtype != b.dtype or a.shape != b.shape or not np.array_equal(a,b):
                    raise ValueError('Raw acoustic/vocoder repeat not exact')
        results.append(dict(condition_id=condition['condition_id'],repetitions=repeats))
    return dict(conditions=results, raw_waveforms=16, delivery_waveforms=0,
        DYN_or_gain_or_PCM_checked=False, listening_status='pending', generic_rule_validated=False)
