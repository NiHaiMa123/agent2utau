"""定位指定 part 的设计为何在某窗口里是平的。"""
import importlib.util
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

spec = importlib.util.spec_from_file_location("dmath", ROOT / "skills/singing-expression-editor/scripts/design_functions.py")
dmath = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmath)

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
doc = load_ustx(DESIGN / "score.ustx")
plan = json.loads((DESIGN / "plan.json").read_text(encoding="utf-8"))
src = Source(V3)
TICK_S = 60.0 / (120.0 * 480)

TARGETS = {18: (79.38125000000001, 79.63729166666668), 12: (59.540625000000006, 59.81645833333334),
           3: (28.616666666666667, 28.999791666666667)}
for pi, (wa, wb) in TARGETS.items():
    print("=" * 25, "part", pi, "window", wa, wb)
    part = doc["voice_parts"][pi]
    base = part["position"] * TICK_S
    ph = [p for p in plan["phrases"] if p["part_index"] == pi][0]
    d = ph["design"]
    for ni, n in enumerate(part["notes"]):
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        if b < wa - 0.2 or a > wb + 0.2:
            continue
        tr = src.track(a, b)
        st = (f"frames {len(tr[0]):3d} span {float(tr[1].max()-tr[1].min()):7.1f} "
              f"p5p95 {float(np.percentile(tr[1],95)-np.percentile(tr[1],5)):7.1f} "
              f"first {tr[1][0]:7.1f} last {tr[1][-1]:7.1f}") if tr else "NO DATA"
        print(f"  n{ni:02d} {str(n['lyric']):3s} {a:8.3f}-{b:8.3f} dur {b-a:.3f} tone {n['tone']} | {st}")
    ts = np.linspace(wa, wb, 10)
    print("  design:", [round(dmath.evaluate(d, float(x)), 1) for x in ts])
    print("  source:", [round(src.level_at(float(x)), 1) for x in ts])
