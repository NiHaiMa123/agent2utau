"""整理迁移工具与探针产物到 migration/ 与 session workspace，然后统一入索引。"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
TOOLS = ROOT / "migration" / "20261030-reorganization" / "tools"
TOOLS.mkdir(parents=True, exist_ok=True)
WS = ROOT / "songs" / "nianlun" / "sessions" / "20261030__unknown-model__nianlun-from-scratch-v3-20261030" / "workspace"
WS.mkdir(parents=True, exist_ok=True)

moved = []
for f in sorted((ROOT / "scratch").glob("reorg_*.py")):
    shutil.move(str(f), str(TOOLS / f.name))
    moved.append(f"scratch/{f.name} -> migration/20261030-reorganization/tools/{f.name}")
for name in ("reorg_survey.json", "reorg_classify.json", "reorg_local_runs.json", "reorg_moves.json",
             "reorg_exec.json", "reorg_final_moves.json"):
    p = ROOT / "scratch" / name
    if p.exists():
        shutil.move(str(p), str(WS / name))
        moved.append(f"scratch/{name} -> <v3 session>/workspace/{name}")
for d in ("bisect", "v3_param_probe"):
    p = ROOT / "scratch" / d
    if p.exists():
        shutil.move(str(p), str(WS / d))
        moved.append(f"scratch/{d}/ -> <v3 session>/workspace/{d}/")
print("moved", len(moved), "items")
for m in moved:
    print("   ", m)
