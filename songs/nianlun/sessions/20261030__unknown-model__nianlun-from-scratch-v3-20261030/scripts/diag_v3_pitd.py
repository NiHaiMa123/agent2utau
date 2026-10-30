"""定位 PITD 越界：逐句计算 目标 - 原生基底 的偏移量。"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("dmath", ROOT / "skills/singing-expression-editor/scripts/design_functions.py")
dmath = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmath)

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
plan = json.loads((V3 / "design" / "plan.json").read_text(encoding="utf-8"))
native = json.loads((V3 / "design" / "baseline_pitch.json").read_text(encoding="utf-8"))["phrases"]

worst = []
for ph, line in zip(plan["phrases"], native):
    d = ph["design"]
    t = np.asarray(line["times_ms"], float) / 1000.0
    before = np.asarray(line["before_pitd_cents"], float)
    target = np.array([dmath.evaluate(d, float(x)) for x in t])
    off = target - before
    worst.append((float(np.abs(off).max()), ph["part_index"], float(off.min()), float(off.max()),
                  float(t[int(np.argmax(np.abs(off)))])))
worst.sort(reverse=True)
print("phrase |max|offset| (limit 1200):")
for w in worst[:12]:
    print("   part %2d  max %7.1f  min %8.1f  max %8.1f  at t=%.3f" % (w[1], w[0], w[2], w[3], w[4]))
over = [w for w in worst if w[0] > 1200]
print("phrases over budget:", len(over))
total_over = 0
for p, l in zip(plan["phrases"], native):
    d = p["design"]
    t = np.asarray(l["times_ms"], float) / 1000.0
    target = np.array([dmath.evaluate(d, float(x)) for x in t])
    off = np.abs(target - np.asarray(l["before_pitd_cents"], float))
    total_over += int(np.sum(off > 1200))
print("total frames over budget:", total_over)
