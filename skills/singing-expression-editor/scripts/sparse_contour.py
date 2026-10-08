"""Shape-preserving sparse reconstruction; selection remains an external decision."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.signal import find_peaks


def sparse_nodes(times_s, cents, tolerance_c=3.0, min_turn_gap_s=.025):
    t, y = np.asarray(times_s, float), np.asarray(cents, float)
    if len(t) < 2 or len(t) != len(y) or not np.all(np.diff(t) > 0):
        raise ValueError('Need equal finite ordered arrays with at least two samples')
    if not np.isfinite(t).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite contour')
    # Meaningful turns are protected before interpolation-error refinement.
    distance = max(1, round(min_turn_gap_s / np.median(np.diff(t))))
    keep = {0, len(t)-1}
    for sign in (1, -1):
        keep.update(find_peaks(sign*y, prominence=tolerance_c, distance=distance)[0].tolist())
    def refine(a, b):
        if b-a <= 1: return
        pred = np.interp(t[a:b+1], [t[a],t[b]], [y[a],y[b]])
        k = a + int(np.argmax(abs(y[a:b+1]-pred)))
        if (abs(y[k]-pred[k-a]) > tolerance_c and a < k < b
                and t[k]-t[a] >= min_turn_gap_s and t[b]-t[k] >= min_turn_gap_s):
            keep.add(k); refine(a,k); refine(k,b)
    order = sorted(keep)
    for a,b in zip(order,order[1:]): refine(a,b)
    order = sorted(keep)
    x,v = t[order],y[order]
    slopes = PchipInterpolator(x,v).derivative()(x)
    slopes[0] = slopes[-1] = 0.
    return [dict(time_s=float(a), cents=float(b), slope_c_per_s=float(c))
            for a,b,c in zip(x,v,slopes)]


def note_connection(points_s_c, note_start_s, tone):
    """Native io bend offsets; no PITD cancellation of a hard note step."""
    pts = np.asarray(points_s_c, float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2 or not np.all(np.diff(pts[:,0]) > 0):
        raise ValueError('Connection needs ordered absolute time/cents points')
    return dict(snap_first=False, data=[dict(x=float((t-note_start_s)*1000),
                 y=float((c-tone*100)/10), shape='io') for t,c in pts])
