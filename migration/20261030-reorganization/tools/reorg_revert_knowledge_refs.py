"""把被知识契约引用的报告移回 docs/reports/ 原位，并恢复 docs/knowledge 的原始字节。

依据 PROJECT_REORGANIZATION_PLAN_20261030.md：
  * docs/knowledge 与被其引用的公开文档属字节保护范围，默认不移动；
  * 确需归类的文件可用"保持原位置 + 歌曲索引引用"的方式。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


moves = json.loads((ROOT / "songs" / "nianlun" / "sessions" / "20261030__unknown-model__"
                    "nianlun-from-scratch-v3-20261030" / "workspace" / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
new_to_old = {v: k for k, v in moves.items()}

# 1) 收集知识包引用到的公开文档路径
PAT = re.compile(r'"(?:path)"\s*:\s*"((?:docs/reports|docs/knowledge|songs)/[^"]+)"')
refs = set()
for f in git("ls-files", "docs/knowledge").split("\n"):
    if not f:
        continue
    t = read(ROOT / f)
    for m in re.findall(r'(?:docs/reports|songs)/[A-Za-z0-9_\-./]+\.(?:md|json|csv|txt)', t):
        refs.add(m)
    for m in PAT.findall(t):
        refs.add(m)
print("knowledge-referenced public docs:", len(refs))

# 2) 被移动的引用文件移回原位
back = []
for ref in sorted(refs):
    if ref in moves:
        back.append((moves[ref], ref))
    elif ref.startswith("songs/") and ref in new_to_old:
        back.append((ref, new_to_old[ref]))
for cur, orig in back:
    dst = ROOT / orig
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        continue
    r = subprocess.run(["git", "-C", str(ROOT), "mv", cur, orig], capture_output=True, text=True)
    print("  back:", cur, "->", orig, r.returncode)
    if r.returncode == 0:
        moves.pop(orig, None)
        moves[cur] = orig

# 3) 恢复 docs/knowledge 的原始字节（字节保护）
git("checkout", "HEAD", "--", "docs/knowledge")
print("docs/knowledge restored to HEAD bytes")

# 4) 更新映射表里的对应记录
for cur, orig in back:
    moves[orig] = orig
json.dump(moves, open(ROOT / "songs" / "nianlun" / "sessions" / "20261030__unknown-model__"
                      "nianlun-from-scratch-v3-20261030" / "workspace" / "reorg_moves.json", "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)
print("moves map entries:", len(moves))
