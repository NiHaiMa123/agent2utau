"""Is the rebuild's score identical to v3's compiled score?

If the notes (lyric/tone/position/duration) match, the off-key result comes from
the auto-pitch curve. If they differ, the rebuild changed the melody itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030/compiled/project.ustx"
REB = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"


def notes_of(path):
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = {}
    for part in d["voice_parts"]:
        pos = part["position"]
        out[pos] = [
            (n["position"], n["duration"], n["tone"], n["lyric"]) for n in part["notes"]
        ]
    return out


def main():
    a = notes_of(V3)
    b = notes_of(REB)
    print("parts v3/rebuild:", len(a), len(b))
    print("same part set:", set(a) == set(b))
    diff_parts = []
    tot = 0
    diffs = 0
    for k in sorted(set(a) & set(b)):
        na, nb = a[k], b[k]
        tot += max(len(na), len(nb))
        if na != nb:
            diff_parts.append(k)
            for i in range(max(len(na), len(nb))):
                x = na[i] if i < len(na) else None
                y = nb[i] if i < len(nb) else None
                if x != y:
                    diffs += 1
                    if len(diff_parts) <= 3:
                        print("  part %d note %d\n    v3   %s\n    reb  %s" % (k, i, x, y))
    print("parts differing:", len(diff_parts), "notes differing:", diffs, "of", tot)

    # tone histogram of '+' notes in rebuild
    tones_plus = [n["tone"] for p in b.values() for n in p if n["lyric"].startswith("+")]
    tones_sung = [n["tone"] for p in b.values() for n in p if n["lyric"] not in ("AP", "SP") and not n["lyric"].startswith("+")]
    print("'+' notes: %d, tone range %d..%d" % (len(tones_plus), min(tones_plus), max(tones_plus)))
    print("sung notes: %d, tone range %d..%d" % (len(tones_sung), min(tones_sung), max(tones_sung)))

    # for each '+' note, compare its tone with the preceding note's tone
    jumps = []
    for k, ns in b.items():
        for i, n in enumerate(ns):
            if n[3].startswith("+") and i > 0:
                jumps.append(n[2] - ns[i - 1][2])
    jumps = np.array(jumps)
    print("'+' tone minus previous tone: |jump|>=3 semitones: %d / %d, max %d"
          % ((np.abs(jumps) >= 3).sum(), len(jumps), np.abs(jumps).max()))

    # what does the v3 note_features say for these notes? (design-side truth)
    feat = json.loads((V3.parent.parent / "design/note_features.json").read_text(encoding="utf-8"))["notes"]
    print("v3 note_features entries:", len(feat), "keys:", list(feat[0].keys()))
    f_by = {}
    for f in feat:
        f_by[(f.get("part_index"), f.get("note_index"))] = f
    # print first few with tone/start
    for f in feat[:5]:
        print("   ", {k: f[k] for k in list(f)[:10]})


if __name__ == "__main__":
    main()
