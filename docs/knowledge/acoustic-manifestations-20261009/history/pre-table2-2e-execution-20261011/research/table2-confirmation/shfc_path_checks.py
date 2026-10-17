"""Independent reconstruction/checks; deliberately does not import adapter."""
import numpy as np

CHANNELS = ('breathiness', 'voicing', 'tension')


def exact(a, b, message):
    if a.shape != b.shape or a.dtype != b.dtype or not np.array_equal(a, b):
        raise ValueError(message)


def check_paths(paths, base, shifted, manual, predictions, acoustic_noise, vocoder_f0, *,
                batch_id, condition_id, repetition, conditioning_bindings):
    """Check actual final tensors, rather than trust variant labels/assembler."""
    if set(paths) != {'A', 'S', 'D', 'P'} or set(predictions) != {'A', 'S'}:
        raise ValueError('Incomplete four paths or joint prediction sources')
    keys = set(base) | {'probe_noise'}
    if set(base) != set(shifted) or set(manual) != set(CHANNELS):
        raise ValueError('Native layout/manual group differs')
    for source in ('A', 'S'):
        draw = predictions[source]
        if (draw.batch_id, draw.condition_id, draw.source, draw.repetition, draw.origin) != (
                batch_id, condition_id, source, repetition, 'predictor_return_this_call'):
            raise ValueError('Prediction provenance mismatch')
        if draw.conditioning_sha256 != conditioning_bindings[source]:
            raise ValueError('Prediction conditioning mismatch')
        if set(draw.values) != {k + '_pred' for k in CHANNELS}:
            raise ValueError('Partial prediction group')
    clipping = {}
    for label in ('A', 'S', 'D', 'P'):
        row = paths[label]
        if (row['batch_id'], row['condition_id'], row['repetition']) != (batch_id, condition_id, repetition):
            raise ValueError('Variant provenance mismatch')
        f0_source = 'S' if label in ('S', 'D') else 'A'
        prediction_source = 'S' if label in ('S', 'P') else 'A'
        if (row['f0_source'], row['prediction_source'], row['native_equivalent']) != (f0_source, prediction_source, label in ('A', 'S')):
            raise ValueError('Incorrect counterfactual role label')
        inputs = row['inputs']
        exact(row['vocoder_f0'], vocoder_f0, 'Vocoder F0 changed')
        exact(vocoder_f0, base['f0'], 'Vocoder target is not unshifted')
        if set(inputs) != keys:
            raise ValueError('Undeclared final tensor names')
        for key, a in inputs.items():
            if not a.size or not np.isfinite(a).all():
                raise ValueError('Empty/nonfinite final input')
            if key == 'probe_noise':
                exact(a, acoustic_noise, 'Acoustic noise changed')
            elif key == 'f0':
                exact(a, (shifted if f0_source == 'S' else base)[key], 'Wrong acoustic F0 path')
            elif key not in CHANNELS:
                exact(a, base[key], 'Nonselected final input changed')
        clipping[label] = {}
        for channel in CHANNELS:
            prediction = predictions[prediction_source].values[channel + '_pred']
            delta = manual[channel]
            if prediction.dtype != np.float32 or prediction.shape != base['f0'].shape or not np.isfinite(prediction).all():
                raise ValueError('Bad prediction layout/finite values')
            if delta.dtype != np.float32 or delta.shape != prediction.shape or not np.isfinite(delta).all():
                raise ValueError('Bad manual baseline layout')
            raw = np.add(prediction, delta, dtype=np.float32)
            lower, upper = (-10., 10.) if channel == 'tension' else (-96., 0.)
            wanted = np.minimum(np.maximum(raw, np.float32(lower)), np.float32(upper))
            exact(inputs[channel], wanted, 'Wrong prediction/manual/clip arithmetic')
            clipping[label][channel] = (raw < lower) | (raw > upper)
    # Do not demand nonzero predicted effects, or mask prediction responses
    # outside the SHFC support. Either would choose results to fit a hypothesis.
    for label in ('S', 'D', 'P'):
        for channel in CHANNELS:
            if np.any(clipping[label][channel] & ~clipping['A'][channel]):
                raise ValueError('New feature clipping relative to A')
    for x, y, allowed in [('D', 'A', {'f0'}), ('P', 'A', set(CHANNELS)),
                          ('S', 'D', set(CHANNELS)), ('S', 'P', {'f0'})]:
        for key in keys - allowed:
            exact(paths[x]['inputs'][key], paths[y]['inputs'][key], 'Path split has a nonselected difference')
    if np.array_equal(paths['D']['inputs']['f0'], paths['A']['inputs']['f0']):
        raise ValueError('No direct SHFC conditioning change')
    return dict(final_float32_arithmetic_exact=True, nonselected_inputs_exact=True,
        clipping_counts={v: {k: int(m.sum()) for k, m in channels.items()} for v, channels in clipping.items()},
        conditional_prediction_response_may_be_zero=True, measured_output_F0_fixed=False,
        real_model_execution_verified=False, generic_rule_validated=False)


def check_repetition(first, second):
    if first['condition_id'] != second['condition_id'] or first['batch_id'] != second['batch_id']:
        raise ValueError('Repeat batch/condition differs')
    for source in ('A', 'S'):
        a, b = first['predictions'][source], second['predictions'][source]
        if a.conditioning_sha256 != b.conditioning_sha256 or set(a.values) != set(b.values):
            raise ValueError('Repeat prediction condition differs')
        for k in a.values:
            exact(a.values[k], b.values[k], 'Repeat prediction not exact')
    for label in ('A', 'S', 'D', 'P'):
        exact(first['paths'][label]['vocoder_f0'], second['paths'][label]['vocoder_f0'], 'Repeat vocoder target differs')
        aa = first['paths'][label]['inputs']
        bb = second['paths'][label]['inputs']
        if set(aa) != set(bb):
            raise ValueError('Repeat final names differ')
        for k in aa:
            exact(aa[k], bb[k], 'Repeat final input not exact')
    return dict(prediction_repeat_exact=True, final_input_repeat_exact=True,
        acoustic_or_vocoder_or_PCM_repeat_checked=False, independent_effect_replications=0)
