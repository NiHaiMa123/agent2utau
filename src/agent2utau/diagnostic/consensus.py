"""GAME stochastic consensus built on formal sequence alignment (M2.2A).

Replaces the earlier 150ms greedy onset clustering: every unordered pair
of runs is DP-aligned (order-preserving, explicit match/gap/split/merge
ops, seqalign.py), then union-find merges matched notes into events.
Run order cannot change the result — all pairwise edges are symmetric.

Event fields (plan2 §9):
  start_median, start_iqr_ms, duration_median, duration_iqr_ms,
  tone_median, tone_agreement, presence_rate, n_runs_present, n_runs,
  run_note_counts, structure_varies, stability
"""

from __future__ import annotations

import numpy as np

from .seqalign import align_pair

STABLE_START_IQR_MS = 30.0


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def build_consensus(runs: list[list[dict]], **_unused) -> list[dict]:
    """runs: list of GAME note lists. Returns consensus events sorted by
    start_median. Order of `runs` does not affect the result."""
    n_runs = len(runs)
    voiced = [[n for n in r if n["voiced"] and n["dur"] > 0.005]
              for r in runs]
    uf = _UF()
    for i in range(n_runs):
        for k in range(i + 1, n_runs):
            ops, A, B = align_pair(voiced[i], voiced[k])
            for op in ops:
                if op[0] == "m":
                    uf.union((i, op[1]), (k, op[2]))
                elif op[0] == "s":
                    for j in op[2]:
                        uf.union((i, op[1]), (k, j))
                elif op[0] == "g":
                    for ii in op[1]:
                        uf.union((i, ii), (k, op[2]))
    groups: dict = {}
    for i in range(n_runs):
        for k, _ in enumerate(voiced[i]):
            groups.setdefault(uf.find((i, k)), []).append((i, k))
    events = []
    for members in groups.values():
        events.append(_finalize(members, voiced, n_runs))
    events.sort(key=lambda e: e["start_median"])
    return events


def _finalize(members: list[tuple[int, int]],
              voiced: list[list[dict]], n_runs: int) -> dict:
    notes = [voiced[ri][k] for ri, k in members]
    starts = np.array([n["start"] for n in notes])
    durs = np.array([n["dur"] for n in notes])
    # per-run note count -> split/merge structure
    counts = np.zeros(n_runs, dtype=int)
    for ri, _ in members:
        counts[ri] += 1
    present = counts[counts > 0]
    structure_varies = bool(len(set(present.tolist())) > 1)
    # per-run aggregate tone for agreement (median of that run's members)
    run_tones = [float(np.median([n["tone"] for (rj, _), n
                                in zip(members, notes) if rj == ri]))
                 for ri in range(n_runs)
                 if any(rj == ri for rj, _ in members)]
    tone_median = float(np.median([n["tone"] for n in notes]))
    tone_agree = (float(np.mean(np.abs(np.array(run_tones) - tone_median)
                              < 0.5))
                  if run_tones else 0.0)
    presence = float(len(present) / max(1, n_runs))
    start_iqr_ms = float(np.percentile(starts, 75)
                         - np.percentile(starts, 25)) * 1000
    dur_iqr_ms = float(np.percentile(durs, 75)
                       - np.percentile(durs, 25)) * 1000
    if presence <= 0.6 or structure_varies or tone_agree < 0.6:
        cls = "GAME_UNSTABLE"
    elif (presence >= 1.0 and tone_agree >= 1.0
          and start_iqr_ms < STABLE_START_IQR_MS):
        cls = "GAME_STABLE"
    else:
        cls = "GAME_VARIABLE"
    return {
        "start_median": round(float(np.median(starts)), 4),
        "start_iqr_ms": round(start_iqr_ms, 1),
        "start_min": round(float(starts.min()), 3),
        "start_max": round(float(starts.max()), 3),
        "duration_median": round(float(np.median(durs)), 4),
        "duration_iqr_ms": round(dur_iqr_ms, 1),
        "tone_median": round(tone_median, 2),
        "tone_min": round(float(min(n["tone"] for n in notes)), 2),
        "tone_max": round(float(max(n["tone"] for n in notes)), 2),
        "tone_agreement": round(tone_agree, 3),
        # §9.4 (B): continuous GAME stochastic evidence — per-run aggregate
        # tone; adjudication must consume the distribution, not a binary.
        "run_tones": [round(t, 2) for t in run_tones],
        "presence_rate": round(presence, 3),
        "n_runs_present": int(len(present)),
        "n_runs": n_runs,
        "run_note_counts": counts.tolist(),
        # §8.6 (C2): explicit per-run member note spans — merge support
        # must come from real GAME notes crossing a candidate boundary,
        # never from run_note_counts==0 (which means gap/absence).
        "member_spans": {str(ri): [[round(n["start"], 3),
                                  round(n["start"] + n["dur"], 3)]
                                 for (rj, _), n in zip(members, notes)
                                 if rj == ri]
                         for ri in range(n_runs)
                         if any(rj == ri for rj, _ in members)},
        "structure_varies": structure_varies,
        "stability": cls,
    }


def consensus_stats(events: list[dict]) -> dict:
    out: dict = {"n_events": len(events), "GAME_STABLE": 0,
                 "GAME_VARIABLE": 0, "GAME_UNSTABLE": 0,
                 "structure_varies": 0}
    for e in events:
        out[e["stability"]] += 1
        out["structure_varies"] += int(e["structure_varies"])
    return out


def event_as_note(ev: dict) -> dict:
    """Consensus event -> note-shaped dict for _align_variants."""
    return {"start": ev["start_median"], "dur": ev["duration_median"],
            "tone": ev["tone_median"], "voiced": True}
