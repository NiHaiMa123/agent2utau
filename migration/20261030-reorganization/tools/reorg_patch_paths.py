"""修正迁移工具在新位置下的数据路径（scratch/*.json -> v3 session workspace）。"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
TOOLS = ROOT / "migration" / "20261030-reorganization" / "tools"
WS_REL = ("songs/nianlun/sessions/20261030__unknown-model__"
          "nianlun-from-scratch-v3-20261030/workspace")

# 还在 scratch 的迁移脚本归位
for f in sorted((ROOT / "scratch").glob("reorg_*.py")):
    shutil.move(str(f), str(TOOLS / f.name))
    print("moved tool:", f.name)

for f in sorted(TOOLS.glob("*.py")):
    t = f.read_text(encoding="utf-8")
    new = re.sub(r'ROOT / "scratch" / "(reorg_[a-z_]+\.json)"', rf'ROOT / "{WS_REL}" / "\1"', t)
    new = new.replace('ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_final_moves.json"',
                      f'ROOT / "{WS_REL}" / "reorg_final_moves.json"')
    if new != t:
        f.write_text(new, encoding="utf-8")
        print("patched paths:", f.name)
