"""定位 v3 判据失败的个别窗口。"""
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
src = Source(V3)
feat = json.loads((DESIGN / "note_features.json").read_text(encoding="utf-8"))["notes"]
feat_by_note = {(f["part_index"], f["note_index"]): f for f in feat}

for pi in (1, 2, 11):
    ph = [p for p in plan["phrases"] if p["part_index"] == pi][0]
    d = ph["design"]
    print("=" * 30, "part", pi, "support", d["support_s"])
    try:
        res = dmath.compile_plan(d, step_s=0.002)
        bad = [c for c in res["local_checks"] if not c["pass"]]
    except Exception as ex:
        print("  validate error:", ex)
        bad = []
    for c in bad:
        print("  FAIL win", c["support_s"], "band", c["range_c"], "observed", round(c["observed_range_c"], 1))
        a, b = c["support_s"]
        tr = src.track(a, b)
        if tr:
            print("     source frames in win:", len(tr[0]), "span", round(float(tr[1].max() - tr[1].min()), 1))
        trw = src.track(a - 0.06, b + 0.06)
        if trw:
            print("     wide span", round(float(trw[1].max() - trw[1].min()), 1))
        ts = np.linspace(a, b, 12)
        print("     design values:", [round(dmath.evaluate(d, float(x)), 1) for x in ts])
        print("     source values:", [round(src.level_at(float(x)), 1) for x in ts])
    # 该句的音符
    for f in feat:
        if f["part_index"] == pi and f["src_span"] > 200:
            print("   note", f["note_index"], f["lyric"], "span", f["src_span"], "level", f["level"],
                  "nominal", f["nominal_c"], "dur", f["dur"])
