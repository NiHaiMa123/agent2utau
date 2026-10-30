"""把本轮 v3 的新脚本与报告归入 songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/。"""
import shutil
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
S = ROOT / "songs" / "nianlun" / "sessions" / "20261030__unknown-model__nianlun-from-scratch-v3-20261030"
(S / "scripts").mkdir(parents=True, exist_ok=True)
(S / "reports").mkdir(parents=True, exist_ok=True)
(S / "workspace").mkdir(parents=True, exist_ok=True)

SCRIPTS = ["nianlun_v3_source.py", "build_nianlun_v3_score.py", "build_nianlun_v3_design.py",
           "build_nianlun_v3_plan.py", "compile_nianlun_v3.py", "mix_review_nianlun_v3.py",
           "measure_nianlun_v3.py", "check_nianlun_v3_design.py", "diag_v3_pitd.py",
           "probe_v3_params.py", "measure_v3_probe.py", "balance_v3_mix.py",
           "make_nianlun_v3_reviews.py", "make_nianlun_v3_critique.py",
           "test_v3_pitch_semantics.py", "test_v3_pitd_semantics.py",
           "probe_phoneme_override.py", "probe_phoneme_override2.py", "probe_ripple_criteria.py",
           "bisect_v3_ustx.py", "bisect_v3_dyn.py", "debug_v3_bands.py", "debug_v3_flat.py",
           "debug_v3_grid.py", "v3_review_observations.json"]
moved = []
for f in SCRIPTS:
    src = ROOT / "scratch" / f
    if src.exists():
        shutil.move(str(src), str(S / "scripts" / f))
        moved.append(f)
rep = ROOT / "docs" / "reports" / "nianlun" / "nianlun-from-scratch-v3-20261030.md"
if rep.exists():
    shutil.move(str(rep), str(S / "reports" / rep.name))
    moved.append(rep.name)
print("moved into v3 session:", len(moved))
for m in moved:
    print("   ", m)
