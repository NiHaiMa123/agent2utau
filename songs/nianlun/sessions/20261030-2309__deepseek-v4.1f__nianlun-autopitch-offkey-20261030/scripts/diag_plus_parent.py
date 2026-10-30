"""Is the '+' extension block's tone equal to its parent syllable?

That is the decisive difference: a '+' block is a continuation of the same sung
syllable. If its tone differs, the melody handed to an auto-pitch predictor is
wrong (it will sing an invented leap). 最后一页 may keep them equal; 年轮 v3 does not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo

PROJECTS = {
    "lastpage_v6": REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
    "nianlun_v3": REPO / "runs/production/nianlun-from-scratch-v3-20261030/compiled/project.ustx",
    "nianlun_v2": REPO / "runs/production/nianlun-from-scratch-v2-20261028/compiled/project.ustx",
    "yuai_v02": None,
}


def main():
    for name, p in PROJECTS.items():
        if p is None or not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        jumps = []
        total_plus = 0
        for vp in d["voice_parts"]:
            ns = vp["notes"]
            for i, n in enumerate(ns):
                if not str(n["lyric"]).startswith("+"):
                    continue
                total_plus += 1
                # parent = nearest previous note that is not '+'
                for j in range(i - 1, -1, -1):
                    if not str(ns[j]["lyric"]).startswith("+"):
                        jumps.append(n["tone"] - ns[j]["tone"])
                        break
        jumps = np.array(jumps)
        if not len(jumps):
            print("%-12s no '+' blocks" % name)
            continue
        print(
            "%-12s '+' blocks %3d : same tone as parent %3d (%.0f%%) ; |jump|>=1 %3d ; >=3 %3d ; max |%d|"
            % (name, total_plus, (jumps == 0).sum(), 100 * (jumps == 0).mean(),
               (np.abs(jumps) >= 1).sum(), (np.abs(jumps) >= 3).sum(), np.abs(jumps).max())
        )
        print("             jump histogram:", {int(k): int(v) for k, v in zip(*np.unique(jumps, return_counts=True))})


if __name__ == "__main__":
    main()
