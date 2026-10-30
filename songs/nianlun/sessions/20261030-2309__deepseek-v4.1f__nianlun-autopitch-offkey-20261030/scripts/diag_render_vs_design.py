"""Compare rendered F0 against the renderer's own exported final pitch grid."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

CASES = [
    ("step1_pitch_only", REPO / "scratch/diag_step1_pitch.json", REPO / "scratch/nianlun_v3_rebuild_audio/step1_vocal_vocal.wav"),
]


def cents(hz):
    return 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0)


def main():
    for name, pj, wav in CASES:
        d = json.loads(pj.read_text(encoding="utf-8"))
        tt, cc = [], []
        for p in d["phrases"]:
            tt.append(np.asarray(p["times_ms"], dtype=float))
            cc.append(np.asarray(p["final_cents"], dtype=float))
        tt = np.concatenate(tt)
        cc = np.concatenate(cc)
        o = np.argsort(tt)
        tt, cc = tt[o] / 1000.0, cc[o]

        print(f"== {name}")
        print("  design: %.2fs..%.2fs  cents %.0f..%.0f" % (tt[0], tt[-1], cc.min(), cc.max()))

        r = extract_f0(wav)
        tv, hz = r["times"], r["f0_hz"]
        cv = np.where(hz > 50.0, cents(hz), np.nan)
        m = np.isfinite(cv)
        print("  render voiced %.2fs..%.2fs" % (tv[m][0], tv[m][-1]))

        ref = np.interp(tv[m], tt, cc)
        dlt = cv[m] - ref
        print(
            "  render - design: median %+.1f  mean %+.1f  p05 %+.1f p95 %+.1f  |d|>50c %.1f%%"
            % (np.median(dlt), dlt.mean(), np.percentile(dlt, 5), np.percentile(dlt, 95),
               100 * (np.abs(dlt) > 50).mean())
        )
        # octave-folded version
        fold = (dlt + 600) % 1200 - 600
        print(
            "  octave-folded: median %+.1f  |d|>50c %.1f%%  |d|>100c %.1f%%"
            % (np.median(fold), 100 * (np.abs(fold) > 50).mean(), 100 * (np.abs(fold) > 100).mean())
        )
        # drift over time: bias per 20s bucket
        print("  bias by 20s bucket:")
        for a in np.arange(tt[0], tt[-1], 20):
            sel = m & (tv >= a) & (tv < a + 20)
            if sel.sum() > 50:
                print("    %6.0f-%6.0fs  n=%4d  bias %+7.1f  |d|med %6.1f"
                      % (a, a + 20, sel.sum(), np.median(cv[sel] - np.interp(tv[sel], tt, cc)),
                         np.median(np.abs(cv[sel] - np.interp(tv[sel], tt, cc)))))


if __name__ == "__main__":
    main()
