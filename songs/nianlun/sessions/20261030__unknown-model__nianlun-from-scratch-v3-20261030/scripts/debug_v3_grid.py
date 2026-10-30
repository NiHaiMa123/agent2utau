"""逐音符打印 part 2 的栅格/轮廓/涟漪/连接，定位设计与源不吻合的音符。"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))
from agent2utau.openutau.ustx import load_ustx
from nianlun_v3_source import Source

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
doc = load_ustx(DESIGN / "score.ustx")
src = Source(V3)
TICK_S = 60.0 / (120.0 * 480)
pi = 2
part = doc["voice_parts"][pi]
base = part["position"] * TICK_S
notes = []
for ni, n in enumerate(part["notes"]):
    a = base + n["position"] * TICK_S
    b = base + (n["position"] + n["duration"]) * TICK_S
    notes.append((ni, a, b, int(n["tone"]), str(n["lyric"])))
for ni, a, b, tone, lyric in notes:
    tr = src.track(a, b)
    if tr:
        print(f"n{ni:02d} {lyric:3s} {a:8.3f}-{b:8.3f} dur {b-a:.3f} tone {tone} "
              f"src frames {len(tr[0]):3d} span {float(tr[1].max()-tr[1].min()):7.1f} "
              f"med {float(np.median(tr[1])):7.1f} first {tr[1][0]:7.1f} last {tr[1][-1]:7.1f}")
    else:
        print(f"n{ni:02d} {lyric:3s} {a:8.3f}-{b:8.3f} dur {b-a:.3f} tone {tone} src NO DATA")
