"""P0-B 执行：修复活动文档里的失效链接（逐条解析目标，给出新的相对路径）。"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
WS = ROOT / ("songs/nianlun/sessions/20261030__unknown-model__"
             "nianlun-from-scratch-v3-20261030/workspace")
sys.stdout.reconfigure(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


audit = json.loads((OUT / "links-audit-raw.json").read_text(encoding="utf-8"))
tracked = set(l for l in git("ls-files").split("\n") if l)
# 第一轮的换位映射（用于反查目标真实位置）
moves = json.loads((WS / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
by_leaf = {}
for old, new in moves.items():
    by_leaf.setdefault(os.path.basename(old), []).append(new)

fixed, unresolved = [], []
for src, target, cand in audit["active_broken"]:
    src_dir = os.path.dirname(src)
    # 1) 直接按当前目录解析
    cands = [os.path.normpath(os.path.join(src_dir, target)).replace("\\", "/")]
    # 2) 若该链接原本指向"被搬走后的位置"，按第一轮映射反查
    leaf = os.path.basename(cand)
    for new in by_leaf.get(leaf, []):
        cands.append(new)
    # 3) 也可能是同名的其它已跟踪文件
    cands += [p for p in tracked if os.path.basename(p) == leaf][:3]
    hit = next((c for c in cands if c in tracked and c != src), None)
    if hit is None:
        unresolved.append((src, target))
        continue
    rel = os.path.relpath(hit, src_dir).replace("\\", "/")
    fp = ROOT / src
    txt = fp.read_text(encoding="utf-8", errors="replace")
    old_md = f"]({target})"
    new_md = f"]({rel})"
    if old_md not in txt:
        unresolved.append((src, target))
        continue
    fp.write_text(txt.replace(old_md, new_md), encoding="utf-8")
    fixed.append((src, target, rel))

for f in fixed:
    print("FIX  ", f[0], "->", f[2])
for u in unresolved:
    print("UNRES", u[0], "->", u[1])
json.dump(dict(fixed=fixed, unresolved=unresolved),
          open(OUT / "links-fixed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fixed:", len(fixed), "| unresolved:", len(unresolved))
