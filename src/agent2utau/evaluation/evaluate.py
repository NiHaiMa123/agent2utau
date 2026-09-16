"""Cover evaluation: pitch accuracy + timing + basic audio checks.

Compares rendered vocal F0 against the target (source-vocal) F0 inside each
note window. Reported as cents error statistics; this measures whether the
synthesized melody tracks the source — it is NOT a perceptual quality score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..analysis.f0 import extract_f0, hz_to_midi


def evaluate(rendered_wav: str | Path, notes: list[dict], target_f0: dict,
             device: str = "cpu") -> dict[str, Any]:
    """notes use absolute timeline seconds (start/dur)."""
    got = extract_f0(rendered_wav, device=device)
    errs, per_note = [], []
    for n in notes:
        t0, t1 = n["start"], n["start"] + n["dur"]
        gm = (got["times"] >= t0) & (got["times"] < t1) & got["voiced"]
        tm = (target_f0["times"] >= t0) & (target_f0["times"] < t1) \
            & target_f0["voiced"]
        if gm.sum() < 3 or tm.sum() < 3:
            per_note.append({"lyric": n["lyric"], "start": n["start"],
                             "status": "unvoiced"})
            continue
        gmed = float(np.median(hz_to_midi(got["f0_hz"][gm])))
        tmed = float(np.median(hz_to_midi(target_f0["f0_hz"][tm])))
        err_cents = (gmed - tmed) * 100.0
        errs.append(err_cents)
        per_note.append({"lyric": n["lyric"], "start": n["start"],
                         "err_cents": round(err_cents, 1),
                         "status": "ok"})
    errs = np.array(errs)
    stats = {
        "n_notes": len(notes),
        "n_evaluated": int(errs.size),
        "n_unvoiced": len(notes) - int(errs.size),
    }
    if errs.size:
        stats.update({
            "median_abs_cents": round(float(np.median(np.abs(errs))), 1),
            "p90_abs_cents": round(float(np.percentile(np.abs(errs), 90)), 1),
            "frac_within_50c": round(float((np.abs(errs) <= 50).mean()), 3),
            "frac_within_100c": round(float((np.abs(errs) <= 100).mean()), 3),
            "bias_cents": round(float(np.median(errs)), 1),
        })
    return {"pitch": stats, "per_note": per_note}
