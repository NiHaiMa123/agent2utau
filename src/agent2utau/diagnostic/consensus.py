"""M2.1.2 GAME stochastic consensus.

Clusters voiced notes from N same-config GAME runs into consensus events
by onset proximity, then measures per-event stability:

- presence_rate    — in how many runs the event exists
- tone_agreement   — fraction of members matching the tone mode
- start/duration IQR in ms
- structure_varies — a run contributes >=2 notes over the event's span
                     (split/merge disagreement across runs)

Classification (plan2 §11):
  GAME_STABLE    presence==1.0, tone unanimous, start_iqr<30ms
  GAME_VARIABLE  4/5 presence, or boundary spread 30-100ms,
                 or minor pitch disagreement
  GAME_UNSTABLE  <=3/5 presence, or split/merge structure varies,
                 or multi-solution pitch
"""

from __future__ import annotations

import numpy as np

MATCH_TOL_S = 0.15
STABLE_START_IQR_MS = 30.0
VARIABLE_START_IQR_MS = 100.0


def build_consensus(runs: list[list[dict]], tol_s: float = MATCH_TOL_S
                    ) -> list[dict]:
    """runs: list of GAME note lists. Returns consensus events sorted by
    start_median. Only voiced notes participate."""
    n_runs = len(runs)
    events: list[dict] = []  # {members: [(run_idx, note)], }
    for ri, notes in enumerate(runs):
        used: set[int] = set()
        for n in notes:
            if not n["voiced"]:
                continue
            best, best_d = None, tol_s
            for ei, ev in enumerate(events):
                if ei in used:
                    continue
                d = abs(n["start"] - ev["start_median"])
                if d <= best_d:
                    best, best_d = ei, d
            if best is None:
                events.append({"members": [(ri, n)],
                               "start_median": float(n["start"])})
            else:
                events[best]["members"].append((ri, n))
                used.add(best)
                events[best]["start_median"] = float(np.median(
                    [m["start"] for _, m in events[best]["members"]]))
    for ev in events:
        _finalize(ev, runs, n_runs)
    events.sort(key=lambda e: e["start_median"])
    return events


def _finalize(ev: dict, runs: list[list[dict]], n_runs: int) -> None:
    mem = ev["members"]
    starts = np.array([m["start"] for _, m in mem])
    durs = np.array([m["dur"] for _, m in mem])
    tones = np.array([m["tone"] for _, m in mem])
    end = float(np.median(starts + durs))
    # split/merge disagreement: does any single run place >=2 voiced notes
    # whose midpoint falls inside this event's median span? (Adjacent notes
    # merely touching the boundary don't count — a split means a second
    # note genuinely inside.)
    t0, t1 = float(np.median(starts)), end
    structure_varies = False
    for notes in runs:
        k = sum(1 for n in notes
                if n["voiced"] and t0 < n["start"] + n["dur"] / 2 < t1)
        if k >= 2:
            structure_varies = True
            break
    tone_mode = float(np.median(tones))
    tone_agree = float(np.mean(np.abs(tones - tone_mode) < 0.5))
    presence = len({ri for ri, _ in mem}) / max(1, n_runs)
    start_iqr = float(np.percentile(starts, 75) - np.percentile(starts, 25))
    dur_iqr = float(np.percentile(durs, 75) - np.percentile(durs, 25))
    if presence <= 0.6 or structure_varies or tone_agree < 0.6:
        cls = "GAME_UNSTABLE"
    elif (presence >= 1.0 and tone_agree >= 1.0
          and start_iqr * 1000 < STABLE_START_IQR_MS):
        cls = "GAME_STABLE"
    else:
        cls = "GAME_VARIABLE"
    ev.update({
        "start_median": round(float(np.median(starts)), 4),
        "start_iqr_ms": round(start_iqr * 1000, 1),
        "start_min": round(float(starts.min()), 3),
        "start_max": round(float(starts.max()), 3),
        "duration_median": round(float(np.median(durs)), 4),
        "duration_iqr_ms": round(dur_iqr * 1000, 1),
        "tone_mode": round(tone_mode, 2),
        "tone_min": round(float(tones.min()), 2),
        "tone_max": round(float(tones.max()), 2),
        "tone_agreement": round(tone_agree, 3),
        "presence_rate": round(presence, 3),
        "n_runs_present": len({ri for ri, _ in mem}),
        "n_runs": n_runs,
        "n_members": len(mem),
        "structure_varies": structure_varies,
        "stability": cls,
    })
    del ev["members"]  # keep events JSON-small; stats retained


def consensus_stats(events: list[dict]) -> dict:
    out: dict = {"n_events": len(events), "GAME_STABLE": 0,
                 "GAME_VARIABLE": 0, "GAME_UNSTABLE": 0}
    for e in events:
        out[e["stability"]] += 1
    return out


def event_as_note(ev: dict) -> dict:
    """Consensus event -> note-shaped dict for _align_variants."""
    return {"start": ev["start_median"], "dur": ev["duration_median"],
            "tone": ev["tone_mode"], "voiced": True}
