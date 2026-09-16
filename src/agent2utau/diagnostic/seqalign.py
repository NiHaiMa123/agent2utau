"""M2.2A formal sequence alignment for GAME stochastic consensus.

Pairwise order-preserving DP alignment between two GAME note sequences.
Operations:
  match (1<->1), gap (note missing in one run), split (1<->2),
  merge (2<->1) — the last two cost a penalty plus the match cost of the
  note vs the merged pair span, so a real split beats two gaps.

All-run consensus = union-find over matched pairs from EVERY unordered
pairwise alignment, so the result is independent of run order.
"""

from __future__ import annotations

import numpy as np

GAP = 0.35            # cost of leaving a note unmatched
SPLIT_MERGE_PEN = 0.15  # extra cost for 1<->2 vs plain match
W_ONSET, W_OVL, W_DUR, W_PITCH = 1.2, 0.6, 0.4, 0.15
ONSET_CAP, DUR_CAP, PITCH_CAP = 0.5, 1.0, 3.0


def _voiced(notes: list[dict]) -> list[dict]:
    return [n for n in notes if n["voiced"] and n["dur"] > 0.005]


def _merged(n1: dict, n2: dict) -> dict:
    s = min(n1["start"], n2["start"])
    e = max(n1["start"] + n1["dur"], n2["start"] + n2["dur"])
    return {"start": s, "dur": e - s,
            "tone": (n1["tone"] * n1["dur"] + n2["tone"] * n2["dur"])
                    / max(1e-9, n1["dur"] + n2["dur"]),
            "voiced": True}


def _mcost(n1: dict, n2: dict) -> float:
    a0, a1 = n1["start"], n1["start"] + n1["dur"]
    b0, b1 = n2["start"], n2["start"] + n2["dur"]
    ov = max(0.0, min(a1, b1) - max(a0, b0))
    iou = ov / max(1e-9, max(a1, b1) - min(a0, b0))
    return (W_ONSET * min(abs(a0 - b0), ONSET_CAP)
            + W_OVL * (1.0 - iou)
            + W_DUR * min(abs(n1["dur"] - n2["dur"]), DUR_CAP)
            + W_PITCH * min(abs(n1["tone"] - n2["tone"]), PITCH_CAP)
            / PITCH_CAP)


def align_pair(a: list[dict], b: list[dict]) -> list[tuple]:
    """DP-align two note lists. Returns ops:
    ('m', i, j) | ('ga', i) | ('gb', j) | ('s', i, (j1, j2)) |
    ('g', (i1, i2), j) — indices into voiced lists a, b."""
    A, B = _voiced(a), _voiced(b)
    n, m = len(A), len(B)
    D = np.full((n + 1, m + 1), np.inf)
    back = np.empty((n + 1, m + 1), dtype=object)
    D[0, :] = np.arange(m + 1) * GAP
    D[:, 0] = np.arange(n + 1) * GAP
    for j in range(1, m + 1):
        back[0, j] = ("gb",)
    for i in range(1, n + 1):
        back[i, 0] = ("ga",)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cands = [
                (D[i - 1, j - 1] + _mcost(A[i - 1], B[j - 1]), ("m",)),
                (D[i - 1, j] + GAP, ("ga",)),
                (D[i, j - 1] + GAP, ("gb",)),
            ]
            if j >= 2:
                cands.append((D[i - 1, j - 2] + SPLIT_MERGE_PEN
                              + _mcost(A[i - 1], _merged(B[j - 2],
                                                         B[j - 1])),
                              ("s",)))
            if i >= 2:
                cands.append((D[i - 2, j - 1] + SPLIT_MERGE_PEN
                              + _mcost(_merged(A[i - 2], A[i - 1]),
                                       B[j - 1]),
                              ("g",)))
            k = int(np.argmin([c for c, _ in cands]))
            D[i, j] = cands[k][0]
            back[i, j] = cands[k][1]
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        op = back[i, j][0]
        if op == "m":
            ops.append(("m", i - 1, j - 1)); i, j = i - 1, j - 1
        elif op == "ga":
            ops.append(("ga", i - 1)); i -= 1
        elif op == "gb":
            ops.append(("gb", j - 1)); j -= 1
        elif op == "s":
            ops.append(("s", i - 1, (j - 2, j - 1))); i, j = i - 1, j - 2
        else:
            ops.append(("g", (i - 2, i - 1), j - 1)); i, j = i - 2, j - 1
    ops.reverse()
    return ops, A, B
