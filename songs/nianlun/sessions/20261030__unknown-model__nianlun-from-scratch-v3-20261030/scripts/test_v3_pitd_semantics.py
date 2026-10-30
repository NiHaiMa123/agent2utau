"""part 级 pitd 语义：final = before_pitd + pitd(插值到音高栅格)？查 compiled 工程。"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V2 = ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028"
TICK_MS = 60000.0 / (120.0 * 480)

for which in ("compiled/project.ustx", "design/score.ustx"):
    p = V2 / which
    if not p.exists():
        print("missing", which)
        continue
    score = yaml.safe_load(p.read_text(encoding="utf-8"))
    pitch = json.loads((V2 / "compiled" / "pitch.json").read_text(encoding="utf-8"))
    print("==", which, "parts", len(score["voice_parts"]),
          "pitch phrases", len(pitch["phrases"]))
    shown = 0
    for pi, part in enumerate(score["voice_parts"]):
        pitd = next((c for c in part.get("curves", []) if c["abbr"] == "pitd"), None)
        if not pitd:
            continue
        ph = next((q for q in pitch["phrases"]
                   if q["part_position"] == part["position"]), None)
        if ph is None:
            continue
        xs = np.asarray(pitd["xs"], float)
        ys = np.asarray(pitd["ys"], float)
        rel = np.asarray(ph["times_ms"], float) / TICK_MS - part["position"]
        got = np.interp(rel, xs, ys, left=ys[0], right=ys[-1])
        delta = np.asarray(ph["final_cents"], float) - np.asarray(ph["before_pitd_cents"], float)
        err = np.abs(delta - got)
        print(f"  part{pi:02d} pts={len(xs):6d} rel[{rel.min():.0f},{rel.max():.0f}] "
              f"max={err.max():.6f} p99={np.percentile(err,99):.6f}")
        shown += 1
        if shown >= 3:
            break
