"""Compare measured phonation axes on shared vowel body centers, not a voice score."""
from statistics import median
import math

from .features import phone_kind
from .phonation import FEATURES


def _words(rows):
    result = {}
    for row in rows:
        if row['id'] in result:
            raise ValueError('Duplicate region')
        result[row['id']] = row
    return result


def _body(row):
    frames = {}
    for frame in row['frames']:
        if frame.get('stage') != 'body' or frame.get('status') != 'measured':
            continue
        at = round(frame['time_s'], 6)
        if at in frames:
            raise ValueError('Duplicate body center')
        if not all(math.isfinite(frame[k]) for k in (*FEATURES, 'midi')):
            raise ValueError('Nonfinite body feature')
        frames[at] = frame
    return frames


def compare_pair(left, right, *, min_body_frames=5, max_pitch_semitones=3.):
    """Return right-minus-left axes, each vowel one vote on shared centers.

    These are diagnostic directions only. No human label, parameter amount,
    expected direction or production target is accepted as a metric input.
    """
    if (not isinstance(min_body_frames, int) or min_body_frames < 2
            or not math.isfinite(max_pitch_semitones) or max_pitch_semitones <= 0):
        raise ValueError('Invalid matching limits')
    a, b = _words(left), _words(right)
    if set(a) != set(b):
        raise ValueError('Region identity mismatch')
    rows = []
    for ident, x in a.items():
        y = b[ident]
        if any(x[k] != y[k] for k in ('phone', 'support_s', 'phrase_id')):
            raise ValueError('Different phone, support or phrase')
        if phone_kind(x['phone']) != 'vowel':
            continue
        f, g = _body(x), _body(y)
        centers = [t for t in sorted(f.keys() & g.keys())
                   if abs(f[t]['midi'] - g[t]['midi']) <= max_pitch_semitones]
        usable = bool(x.get('body') and y.get('body')) and len(centers) >= min_body_frames
        delta = {k: median(g[t][k] - f[t][k] for t in centers) for k in FEATURES} if usable else None
        rows.append(dict(id=ident, phone=x['phone'], shared_body_centers=centers,
                         shared_count=len(centers), status='measured' if usable else 'unknown',
                         reason=None if usable else 'insufficient_shared_reliable_body',
                         right_minus_left=delta))
    measured = [r for r in rows if r['status'] == 'measured']
    return dict(vowels=len(rows), comparable_vowels=len(measured),
                comparable_fraction=len(measured)/len(rows) if rows else 0., words=rows,
                median_right_minus_left={k: median(r['right_minus_left'][k] for r in measured)
                                         for k in FEATURES} if measured else None,
                perceptual_firmness=None, perceptual_consistency=None,
                boundary='Paired acoustic axes on shared body centers; no perceptual threshold or automatic pass')
