"""v3 画线自检：DSL 形状判据 + 设计与原唱迹线的贴合度（编译前的本地核对）。"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))
from nianlun_v3_source import Source

spec = importlib.util.spec_from_file_location("dmath", ROOT / "skills/singing-expression-editor/scripts/design_functions.py")
dmath = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmath)

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
plan = json.loads((DESIGN / "plan.json").read_text(encoding="utf-8"))
native = json.loads((DESIGN / "baseline_pitch.json").read_text(encoding="utf-8"))["phrases"]
src = Source(V3)

fails, devs, devs_all = [], [], []
for ph, line in zip(plan["phrases"], native):
    d = ph["design"]
    try:
        res = dmath.compile_plan(d, step_s=0.002)
    except Exception as ex:
        fails.append((ph["part_index"], str(ex)))
        continue
    if not res["shape_checks_pass"]:
        bad = [c for c in res["local_checks"] if not c["pass"]]
        fails.append((ph["part_index"], [(c["support_s"], c["range_c"], round(c["observed_range_c"], 1)) for c in bad]))
    t = np.asarray(line["times_ms"], float) / 1000.0
    y = np.array([dmath.evaluate(d, float(x)) for x in t])
    tr = src.track(float(t[0]), float(t[-1]))
    if tr is None:
        continue
    tt, vv = tr
    got = np.interp(tt, t, y)
    ok = (tt >= t[0]) & (tt <= t[-1])
    dev = got[ok] - vv[ok]
    if len(dev):
        devs_all.append(np.abs(dev))
        devs.append(dict(part_index=ph["part_index"], n=int(len(dev)),
                         median=float(np.median(np.abs(dev))), p90=float(np.percentile(np.abs(dev), 90))))

allv = np.concatenate(devs_all) if devs_all else np.array([0.0])
print("design vs source F0 trace: median %.1fc  p90 %.1fc  max %.1fc" %
      (np.median(allv), np.percentile(allv, 90), allv.max()))
worst = sorted(devs, key=lambda d: -d["p90"])[:8]
for w in worst:
    print("   worst part %2d: median %.1fc p90 %.1fc (n=%d)" % (w["part_index"], w["median"], w["p90"], w["n"]))
print("shape check failures:", len(fails))
for f in fails[:10]:
    print("   ", f)
