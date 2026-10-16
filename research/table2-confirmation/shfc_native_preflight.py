"""Read-only clock/curve/model declarations for the two sealed conditions.

No cache reader, predictor, ONNX session, project writer or audio operation.
Clock/sampling formulas are checked against bound local Core IL separately.
"""
import math
import numpy as np
from agent2utau.evaluation.controlled_probe import tensors

FRAME_MS = 512 / 44100 * 1000


def check_identity(a, v, case):
    if a['phrase_index'] != v['phrase_index'] or a['phrase_index'] != case['condition']['context']:
        raise ValueError('Wrong phrase identity')
    if a['sample_rate'] != 44100 or np.float32(a['frame_ms']) != np.float32(FRAME_MS):
        raise ValueError('Wrong native frame representation')
    for key in ('frame_ms', 'head_frames', 'tail_frames'):
        if a[key] != v[key]:
            raise ValueError('Variance/acoustic clock differs')
    if (a['head_frames'], a['tail_frames']) != (8, 8):
        raise ValueError('Unexpected native padding')
    phones = a['phones']
    if not phones or a['position_ms'] != phones[0]['positionMs']:
        raise ValueError('Phrase origin differs from complete phone clock')
    durations = [8 * FRAME_MS]
    labels = ['SP']
    for i, phone in enumerate(phones):
        if phone['endMs'] <= phone['positionMs']:
            raise ValueError('Invalid phone interval')
        if i:
            gap = phone['positionMs'] - phones[i - 1]['endMs']
            if gap < 0:
                raise ValueError('Overlapping phones')
            if gap > 0:
                durations.append(gap); labels.append('SP')
        durations.append(phone['endMs'] - phone['positionMs'])
        labels.append(phone['phoneme'])
    durations.append(8 * FRAME_MS); labels.append('SP')
    accumulated, previous, frames = 0., 0, []
    for d in durations:
        accumulated += d
        end = round(accumulated / FRAME_MS + .5)
        frames.append(end - previous); previous = end
    av, vv = tensors(a['tensors']), tensors(v['tensors'])
    expected = np.asarray(frames, np.int64)[None, :]
    if not np.array_equal(av['durations'], expected) or not np.array_equal(vv['ph_dur'], expected):
        raise ValueError('Complete padded phone duration reconstruction differs')
    if av['tokens'].shape != expected.shape or av['languages'].shape != expected.shape:
        raise ValueError('Token/language layout differs')
    if av['f0'].shape != vv['pitch'].shape or av['f0'].size != sum(frames):
        raise ValueError('Frame count differs from complete phone clock')
    found = []
    for target in case['condition']['native_phones']:
        ix = [i for i, phone in enumerate(phones) if phone['phoneme'] == target['phoneme']
            and phone['tone'] == target['tone'] and phone['positionMs'] == target['start_ms']
            and phone['endMs'] == target['end_ms']]
        if len(ix) != 1:
            raise ValueError('Target phone clock/tone identity differs')
        found.append(ix[0])
    if found[1] != found[0] + 1:
        raise ValueError('Target consonant/vowel not adjacent')
    # Language IDs for every real zh phone, including neighbours, not just target.
    if any(int(av['languages'][0, i]) != 4 for i, label in enumerate(labels) if label.startswith('zh/')):
        raise ValueError('Chinese phone language differs')
    return dict(real_phones=len(phones), padded_segments=len(labels), total_frames=sum(frames),
        target_phone_indices=found, complete_phone_clock_exact=True,
        native_float32_frame_ms=float(np.float32(a['frame_ms'])), sample_period_ms=FRAME_MS,
        vocabulary_token_semantics_revalidated=False, current_native_execution=False)


def q5_value(t, anchors, peak):
    a,b,c,d = anchors
    if not a < b <= c < d or peak != -400:
        raise ValueError('Frozen geometry order/peak required')
    if t < a or t > d:
        return 0
    if b <= t <= c:
        return peak
    u = (t-a)/(b-a) if t < b else (t-c)/(d-c)
    q = u*u*u*(10 + u*(-15 + 6*u))
    return round(peak * (q if t < b else 1-q))


def planned_curve(project, a, case):
    # Only this explicit fixed project clock is supported; no guessed tempo map.
    if project['resolution'] != 480 or project['tempos'] != [dict(position=0, bpm=120)]:
        raise ValueError('Unsupported project timeAxis')
    part = project['voice_parts'][case['condition']['context']]
    start = math.floor((case['shifted_support_s'][0]*960 - part['position'])/5)*5 - 5
    end = math.ceil((case['shifted_support_s'][1]*960 - part['position'])/5)*5 + 5
    xs = list(range(start, end+1, 5))
    ys = [q5_value((part['position']+x)/960, case['nominal_Q5_anchors_s'], case['peak_cents']) for x in xs]
    if min(ys) != -400 or ys[0] != 0 or ys[-1] != 0:
        raise ValueError('Planned integer grid lacks peak/zero boundary')
    return dict(abbr='shfc', xs=xs, ys=ys)


def sample_curve(project, a, curve, *, unit='cents'):
    if unit not in ('cents', 'semitones'):
        raise ValueError('Unknown SHFC sampling unit')
    part = project['voice_parts'][a['phrase_index']]
    # Local Core: TimeAxis round-to-even integer tick first, then /5 interpolation.
    # Model uses dsconfig double period, exporter frame_ms is a float32 summary.
    origin = a['position_ms'] - a['head_frames']*FRAME_MS
    n = tensors(a['tensors'])['f0'].size
    xs, ys = curve['xs'], curve['ys']
    if len(xs) != len(ys) or any(x % 5 for x in xs) or any(b-a != 5 for a,b in zip(xs,xs[1:])):
        raise ValueError('Only integer 5tick grid accepted')
    result = []
    for i in range(n):
        local = round((origin+i*FRAME_MS)*.96) - part['position']
        if local <= xs[0] or local >= xs[-1]:
            value = 0.
        else:
            k = (local-xs[0])//5
            value = ys[k]+(ys[k+1]-ys[k])*((local-xs[k])/5)
        # Local DsVariance b__19_5: double value * 0.01, then float32.
        # Acoustic SHFC: float32 cents before /1200; these orders differ.
        result.append(value if unit == 'cents' else value*.01)
    return np.asarray(result, np.float32)


def check_sample_support(a, sampled, case):
    clock = (a['position_ms']+(np.arange(len(sampled))-a['head_frames'])*a['frame_ms'])/1000
    ix = np.flatnonzero(sampled)
    if not len(ix) or sampled.min() != -400 or np.any(sampled > 0) or np.any(sampled < -400):
        raise ValueError('Sampled peak/range differs')
    if np.any(clock[ix] < case['shifted_support_s'][0]) or np.any(clock[ix] > case['shifted_support_s'][1]):
        raise ValueError('Sampled support escapes frozen interval')
    return dict(changed_frames=len(ix), sampled_peak_cents=float(sampled.min()),
        sampled_support_s=clock[ix[[0,-1]]].tolist(), scope='local IL mathematical reconstruction, not new installed export')


def normalize_model_inputs(values, declarations):
    """Match model declarations; only steps/depth singleton to scalar permitted.

    Values/dtypes remain exact. Never cast, resample, rename or fill a tensor.
    Used immediately at the backend feed boundary; original native arrays stay.
    """
    if set(values) != {d['name'] for d in declarations}:
        raise ValueError('Model input names differ')
    dtype_map = {1: np.dtype('float32'), 7: np.dtype('int64'), 9: np.dtype('bool')}
    result, dimensions = {}, {}
    for d in declarations:
        k = d['name']; x = np.asarray(values[k]); shape = d['shape']
        if x.dtype != dtype_map.get(d['type']) or not x.size or not np.isfinite(x).all():
            raise ValueError('Model input dtype/nonfinite differs')
        if not shape and k in ('steps','depth') and x.shape == (1,):
            x = x.reshape(())
        if x.ndim != len(shape):
            raise ValueError('Model input rank differs')
        for declared, actual in zip(shape, x.shape):
            if isinstance(declared, int):
                if declared != actual:
                    raise ValueError('Model fixed dimension differs')
            else:
                if declared in dimensions and dimensions[declared] != actual:
                    raise ValueError('Model shared dimension differs')
                dimensions[declared] = actual
        result[k] = x.copy()
    return result
