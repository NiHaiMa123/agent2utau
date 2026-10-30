"""Why does auto-pitch work for 最后一页 but fail for 年轮?

Compare the two projects' inputs to the SAME DiffSinger pitch predictor:
  - note layout ('+' extension blocks, rest blocks, note lengths)
  - whether the score's tone already equals the sung pitch
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))

PROJECTS = {
    "lastpage_v6": REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
    "nianlun_v3_rebuild": REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx",
    "nianlun_v3_compiled": REPO / "runs/production/nianlun-from-scratch-v3-20261030/compiled/project.ustx",
}
TICK_MS = 60000.0 / (120.0 * 480.0)


def main():
    print("%-22s %6s %6s %6s %6s %8s %10s %10s" %
          ("project", "parts", "notes", "sung", "'+'", "rest", "overrides", "min_dur_ms"))
    stats = {}
    for name, p in PROJECTS.items():
        if not p.exists():
            print("%-22s MISSING" % name)
            continue
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        plus = sung = rest = ov = tot = 0
        durs = []
        for vp in d["voice_parts"]:
            for n in vp["notes"]:
                tot += 1
                L = str(n["lyric"])
                if L.startswith("+"):
                    plus += 1
                elif L in ("SP", "AP"):
                    rest += 1
                else:
                    sung += 1
                    durs.append(n["duration"] * TICK_MS)
                if n.get("phoneme_overrides"):
                    ov += 1
        stats[name] = dict(d=d, plus=plus, sung=sung, rest=rest, ov=ov, tot=tot,
                           durs=np.array(durs))
        print("%-22s %6d %6d %6d %6d %8d %10d %10.0f" %
              (name, len(d["voice_parts"]), tot, sung, plus, rest, ov, min(durs)))

    # --- the decisive number: how far is each score's tone from its own source?
    from nianlun_v3_source import Source, filled_track
    V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
    nian = stats.get("nianlun_v3_rebuild")
    if nian:
        src = Source(V3)
        errs, plus_errs = [], []
        for vp in nian["d"]["voice_parts"]:
            pos = vp["position"]
            for n in vp["notes"]:
                L = str(n["lyric"])
                if L in ("SP", "AP"):
                    continue
                a = (pos + n["position"]) * TICK_MS / 1000.0
                b = a + n["duration"] * TICK_MS / 1000.0
                ft = filled_track(src, a, b)
                if not ft:
                    continue
                m = (ft[0] >= a) & (ft[0] < b)
                if m.sum() < 3:
                    continue
                e = float(np.median(ft[1][m])) - n["tone"] * 100.0
                errs.append(e)
                if L.startswith("+"):
                    plus_errs.append(e)
        errs = np.array(errs)
        print("\n年轮 score tone vs its own source F0 (cents):")
        print("  all  n=%d  median %+.1f   |e|median %.1f  p90 %.1f  >100c %d" %
              (len(errs), np.median(errs), np.median(np.abs(errs)),
               np.percentile(np.abs(errs), 90), (np.abs(errs) > 100).sum()))
        if plus_errs:
            pe = np.array(plus_errs)
            print("  '+'  n=%d  median %+.1f   |e|median %.1f" %
                  (len(pe), np.median(pe), np.median(np.abs(pe))))

    # --- lastpage: does its score tone already match its source? (cannot: no source here)
    # Instead show that lastpage has almost no '+' blocks, so its score = sung melody.
    lp = stats.get("lastpage_v6")
    if lp:
        print("\n最后一页 v6: %d notes, %d '+' blocks (%.1f%%), %d rests" %
              (lp["tot"], lp["plus"], 100 * lp["plus"] / lp["tot"], lp["rest"]))
    if nian:
        print("年轮 v3重建: %d notes, %d '+' blocks (%.1f%%), %d rests" %
              (nian["tot"], nian["plus"], 100 * nian["plus"] / nian["tot"], nian["rest"]))


if __name__ == "__main__":
    main()
