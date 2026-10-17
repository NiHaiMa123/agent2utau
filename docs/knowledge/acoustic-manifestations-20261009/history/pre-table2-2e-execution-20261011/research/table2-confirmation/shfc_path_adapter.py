"""Research-only tensor assembly. No files, inference, audio, or USTX writes."""
from dataclasses import dataclass
import hashlib
import numpy as np

CHANNELS = ('breathiness', 'voicing', 'tension')


def tensor_binding(values):
    h = hashlib.sha256()
    for key in sorted(values):
        a = np.asarray(values[key])
        if not a.size or a.dtype.kind not in 'fiub' or not np.isfinite(a).all():
            raise ValueError('Empty, nonnumeric or nonfinite tensor')
        h.update(key.encode() + b'\0' + a.dtype.str.encode() + b'\0')
        h.update(str(a.shape).encode() + b'\0' + np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


@dataclass(frozen=True)
class FreshPrediction:
    batch_id: str
    condition_id: str
    source: str
    repetition: int
    conditioning_sha256: str
    values: dict
    # Created by runner immediately after the supplied predictor returns.
    # The numerical contract cannot prove that a backend executed real ONNX.
    origin: str = 'predictor_return_this_call'


def assemble_paths(base, shifted, manual, predictions, *, batch_id, condition_id,
                   repetition, conditioning_bindings, acoustic_noise, vocoder_f0):
    """A/S native-equivalent paths and D/P same-condition counterfactuals."""
    if not batch_id or not condition_id or repetition not in (0, 1):
        raise ValueError('Explicit batch/condition and bounded repetition required')
    if set(predictions) != {'A', 'S'} or set(conditioning_bindings) != {'A', 'S'}:
        raise ValueError('Both fresh A/S predictions required')
    if set(base) != set(shifted) or not {'f0', *CHANNELS} <= set(base) or 'probe_noise' in base:
        raise ValueError('Changed native input names or preexisting probe noise')
    tensor_binding(base)
    tensor_binding(shifted)
    shape = base['f0'].shape
    if len(shape) != 2 or shape[0] != 1 or base['f0'].dtype != np.float32:
        raise ValueError('Only native float32 [1, frames] layout supported')
    if set(manual) != set(CHANNELS):
        raise ValueError('Complete manual baseline required')
    for k in base:
        if base[k].dtype != shifted[k].dtype or base[k].shape != shifted[k].shape:
            raise ValueError('Changed tensor dtype/shape')
        if k not in {'f0', *CHANNELS} and not np.array_equal(base[k], shifted[k]):
            raise ValueError('Changed nonselected native input')
    for source, draw in predictions.items():
        if (draw.batch_id, draw.condition_id, draw.source, draw.repetition, draw.origin) != (
                batch_id, condition_id, source, repetition, 'predictor_return_this_call'):
            raise ValueError('Prediction from wrong batch/condition/source/repetition or historical cache')
        if draw.conditioning_sha256 != conditioning_bindings[source]:
            raise ValueError('Prediction conditioning binding mismatch')
        if set(draw.values) != {k + '_pred' for k in CHANNELS}:
            raise ValueError('Complete joint prediction group required')
        for k in CHANNELS:
            pred = draw.values[k + '_pred']
            if pred.dtype != np.float32 or pred.shape != shape or not np.isfinite(pred).all():
                raise ValueError('Invalid prediction dtype/shape/finite values')
            if manual[k].dtype != np.float32 or manual[k].shape != shape or not np.isfinite(manual[k]).all():
                raise ValueError('Invalid manual baseline')
    if acoustic_noise.dtype != np.float32 or acoustic_noise.shape != (1, 1, 128, shape[1]) or not np.isfinite(acoustic_noise).all():
        raise ValueError('Invalid shared acoustic noise')
    if vocoder_f0.dtype != np.float32 or vocoder_f0.shape != shape or not np.isfinite(vocoder_f0).all() or not np.array_equal(vocoder_f0, base['f0']):
        raise ValueError('Vocoder must retain unshifted target F0')
    matrix = {'A': ('A', 'A'), 'S': ('S', 'S'), 'D': ('S', 'A'), 'P': ('A', 'S')}
    result = {}
    for label, (f0_source, prediction_source) in matrix.items():
        inputs = {k: v.copy() for k, v in base.items()}
        inputs['f0'] = (base if f0_source == 'A' else shifted)['f0'].copy()
        inputs['probe_noise'] = acoustic_noise.copy()
        for k in CHANNELS:
            limits = (-10, 10) if k == 'tension' else (-96, 0)
            inputs[k] = np.clip(predictions[prediction_source].values[k + '_pred'] + manual[k], *limits)
        result[label] = dict(inputs=inputs, f0_source=f0_source, prediction_source=prediction_source,
            native_equivalent=label in ('A', 'S'), batch_id=batch_id,
            condition_id=condition_id, repetition=repetition, vocoder_f0=vocoder_f0.copy())
    return result
