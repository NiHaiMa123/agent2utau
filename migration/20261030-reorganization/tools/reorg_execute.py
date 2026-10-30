"""执行移动：先按新位置重写引用，再 git mv，最后校验。

引用处理规则：
  * 仓库根相对路径串（如 docs/reports/yuai/x.md、scratch/a.py）-> 换成新路径；
  * 相对链接（markdown 的 ](target)）-> 先按旧目录解析成仓库相对目标，
    若目标也被移动则映射到新路径，再按"文件新所在目录"重新生成相对链接。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

MOVES = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json").read_text(encoding="utf-8"))["moves"]
MD_LINK = re.compile(r"\]\(([^)\s]+)([^)]*)\)")
TEXT_EXT = (".md", ".py", ".json", ".txt", ".yaml", ".yml", ".log", ".csv", ".html", ".tsv")

tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace").stdout.split("\n") if l]
old_set = set(MOVES)


def read(p):
    try:
        return (ROOT / p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def write(p, text):
    (ROOT / p).write_text(text, encoding="utf-8")


changed = []
skipped = []
for p in tracked:
    if not p.endswith(TEXT_EXT):
        continue
    txt = read(p)
    if txt is None:
        continue
    new_path = MOVES.get(p, p)
    old_dir = os.path.dirname(p)
    new_dir = os.path.dirname(new_path)
    orig = txt

    # 1) 仓库根相对路径串
    def repl_path(m):
        old_ref = m.group(0)
        target = old_ref.strip("`'\"()[] ,;:")
        if target in old_set:
            return old_ref.replace(target, MOVES[target])
        return old_ref

    txt = re.sub(r"(?<![\w/.-])(?:docs/reports|scratch|docs|research)/[\w./\-]+\.(?:md|py|json|csv|txt|log|ustx|zip|yaml|yml)",
                 repl_path, txt)

    # 2) 相对链接
    def fix_link(m):
        target, tail = m.group(1), m.group(2)
        if target.startswith(("http:", "https:", "#", "mailto:")):
            return m.group(0)
        frag = ""
        if "#" in target:
            target, frag = target.split("#", 1)
            frag = "#" + frag
        if not target:
            return m.group(0)
        abs_old = os.path.normpath(os.path.join(old_dir, target)).replace("\\", "/")
        if abs_old.startswith(".."):
            return m.group(0)
        abs_new = MOVES.get(abs_old, abs_old)
        rel = os.path.relpath(abs_new, new_dir).replace("\\", "/")
        return f"]({rel}{frag}{tail})"

    txt = MD_LINK.sub(fix_link, txt)
    if txt != orig:
        write(p, txt)
        changed.append(p)

print("content rewritten:", len(changed))

# git mv
ok, fail = 0, []
for old, new in sorted(MOVES.items()):
    src = ROOT / old
    dst = ROOT / new
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        fail.append((old, new, "source missing"))
        continue
    if dst.exists():
        fail.append((old, new, "target exists"))
        continue
    r = subprocess.run(["git", "-C", str(ROOT), "mv", old, new], capture_output=True, text=True)
    if r.returncode != 0:
        fail.append((old, new, r.stderr.strip()[:120]))
    else:
        ok += 1
print("git mv ok:", ok, "failed:", len(fail))
for f in fail[:15]:
    print("   ", f)
json.dump(dict(changed=changed, moved=ok, failed=fail),
          open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_exec.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
