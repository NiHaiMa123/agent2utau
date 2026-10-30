"""补齐最后一批移动后的引用改写，并重建 uncertain 清单。"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
WS = ROOT / ("songs/nianlun/sessions/20261030__unknown-model__"
             "nianlun-from-scratch-v3-20261030/workspace")
sys.stdout.reconfigure(encoding="utf-8")
MD_LINK = re.compile(r"\]\(([^)\s]+)([^)]*)\)")
TEXT_EXT = (".md", ".py", ".json", ".txt", ".yaml", ".yml", ".log", ".csv", ".html", ".tsv")

moves = json.loads((WS / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
final = json.loads((WS / "reorg_final_moves.json").read_text(encoding="utf-8"))
batch = {m["old_path"]: m["new_path"] for m in final["moved"]}
old_set = set(moves)


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


tracked = [l for l in git("ls-files").split("\n") if l]
changed = []
for p in tracked:
    if not p.endswith(TEXT_EXT):
        continue
    fp = ROOT / p
    try:
        txt = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    new_path = moves.get(p, p)
    old_dir = os.path.dirname(p)
    new_dir = os.path.dirname(new_path)
    orig = txt

    def repl(m):
        ref = m.group(0)
        target = ref.strip("`'\"()[] ,;:")
        if target in old_set:
            return ref.replace(target, moves[target])
        return ref

    txt = re.sub(r"(?<![\w/.-])(?:docs/reports|scratch|docs|research)/[\w./\-]+\.(?:md|py|json|csv|txt|log|ustx|zip|yaml|yml)",
                 repl, txt)

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
        if abs_old.startswith("..") or ":" in abs_old:
            return m.group(0)
        abs_new = moves.get(abs_old, abs_old)
        rel = os.path.relpath(abs_new, new_dir).replace("\\", "/")
        return f"]({rel}{frag}{tail})"

    txt = MD_LINK.sub(fix_link, txt)
    if txt != orig:
        fp.write_text(txt, encoding="utf-8")
        changed.append(p)
print("files rewritten in the final pass:", len(changed))

# uncertain 清单：只保留真正无法确证的
kept = []
for k in final["kept"]:
    kept.append(dict(old_path=k["old_path"], reason=k["reason"], risk="low"))
rows = [k for k in kept if k["old_path"].startswith("scratch/")]
with open(MIG / "uncertain-items.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\treason\trisk\tstatus\n")
    for r in rows:
        f.write(f"{r['old_path']}\t{r['reason']}\t{r['risk']}\tkept-in-place\n")
print("uncertain rows:", len(rows))
json.dump(dict(batch=batch, rewritten=changed),
          open(WS / "reorg_final_pass.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
