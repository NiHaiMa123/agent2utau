"""Measure 最后一页 v6's auto-pitch quality the same way as 年轮's.

Source = the project's own separation source.wav F0 (fcpe/rmvpe npz), so both
songs are judged on the identical criteria: rendered/score pitch vs the singer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))

LP = REPO / "runs/production/zuihouyiye-from-scratch-20261027"
TICK_MS = 60000.0 / (120.0 * 480.0)


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def load_obs(path):
    z = np.load(path)
    print("  npz keys:", list(z.keys()))
    return z


def main():
    print("== lastpage source observation")
    for n in ("fcpe.npz", "rmvpe.npz"):
        p = LP / "observation" / n
        if p.exists():
            z = np.load(p)
            print(n, {k: (z[k].shape if hasattr(z[k], "shape") else type(z[k])) for k in z.keys()})

    # rendered audio of lastpage v6
    for cand in ["vocal_vocal.wav", "vocal.wav"]:
        for d in ["render_v6", "render"]:
            p = LP / d / cand
            if p.exists():
                print("lastpage render:", p)


if __name__ == "__main__":
    main()
