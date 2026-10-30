"""验证两件决定 v3 路线的事：

1) part 级 pitd 曲线是否满足 final = before_pitd + pitd(插值到音高栅格)。
2) note 级 vibrato 是否进入 export-pitch 的 final_cents。

只读 v2 产物 + 生成临时工程，输出到 scratch/v3_semantics_probe/。
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))

from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

V2 = ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028"
PROBE = ROOT / "scratch" / "v3_semantics_probe"

# ---------- 1) 读 v2 的 pitd 曲线与导出音高 ----------
score = yaml.safe_load((V2 / "design" / "score.ustx").read_text(encoding="utf-8"))
pitch = json.loads((V2 / "compiled" / "pitch.json").read_text(encoding="utf-8"))
TICK_MS = 60000.0 / (120.0 * 480)

print("== 1) part pitd 语义检查 ==")
checked = 0
for pi, part in enumerate(score["voice_parts"]):
    pitd = next((c for c in part.get("curves", []) if c["abbr"] == "pitd"), None)
    if not pitd:
        continue
    ph = next((p for p in pitch["phrases"]
               if p["part_position"] == part["position"]), None)
    if ph is None:
        continue
    xs = np.asarray(pitd["xs"], dtype=float)
    ys = np.asarray(pitd["ys"], dtype=float)
    rel_ms = (np.asarray(ph["times_ms"], dtype=float) - part["position"] * TICK_MS)
    got = np.interp(rel_ms, xs, ys, left=ys[0], right=ys[-1])
    delta = np.asarray(ph["final_cents"], dtype=float) - np.asarray(ph["before_pitd_cents"], dtype=float)
    err = np.abs(delta - got)
    print(f"  part{pi:02d} pitd pts={len(xs):6d} |delta-pitd| max={err.max():.6f} "
          f"p50={np.median(err):.6f} p99={np.percentile(err,99):.6f}")
    checked += 1
    if checked >= 4:
        break

# ---------- 2) vibrato 是否进入导出音高 ----------
PROBE.mkdir(parents=True, exist_ok=True)
cfg = load_config()
tpl = yaml.safe_load((ROOT / "configs" / "ustx_template.yaml").read_text(encoding="utf-8"))


def make(name, vibrato):
    doc = yaml.safe_load((ROOT / "configs" / "ustx_template.yaml").read_text(encoding="utf-8"))
    doc["name"] = name
    doc["bpm"] = 120.0
    doc["tempos"] = [{"position": 0, "bpm": 120.0}]
    note = {
        "position": 0,
        "duration": 480,
        "tone": 60,
        "lyric": "啊",
        "pitch": {"data": [{"x": -40, "y": 0, "shape": "io"},
                           {"x": 40, "y": 0, "shape": "io"}],
                  "snap_first": True},
        "vibrato": vibrato,
        "tuning": 0,
        "phoneme_expressions": [],
        "phoneme_overrides": [],
    }
    doc["voice_parts"] = [{
        "duration": 480, "name": "seg0", "comment": "", "track_no": 0,
        "position": 0, "notes": [note], "curves": [],
    }]
    doc["wave_parts"] = []
    out = PROBE / f"{name}.ustx"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=10 ** 6)
    rp = run_bridge(cfg, ["export-pitch", "--project", str(out.resolve()),
                          "--out", str((PROBE / f"{name}_pitch.json").resolve())])
    d = json.loads((PROBE / f"{name}_pitch.json").read_text(encoding="utf-8"))
    ph = d["phrases"][0]
    before = np.asarray(ph["before_pitd_cents"], float)
    final = np.asarray(ph["final_cents"], float)
    diff = final - before
    print(f"  {name}: ok={rp.get('ok')} frames={len(diff)} "
          f"max|final-before|={np.abs(diff).max():.4f} "
          f"std={np.std(diff):.4f}")
    return diff


print("== 2) vibrato 是否进入导出音高 ==")
flat = make("probe_flat", {"length": 0, "period": 175, "depth": 25, "in": 10,
                           "out": 10, "shift": 0, "drift": 0, "vol_link": 0})
vib = make("probe_vibrato", {"length": 100, "period": 200, "depth": 40, "in": 10,
                             "out": 10, "shift": 0, "drift": 0, "vol_link": 0})
print("  vibrato 与 flat 的 final 差 max =", float(np.abs(vib - flat).max()))
print("done")
