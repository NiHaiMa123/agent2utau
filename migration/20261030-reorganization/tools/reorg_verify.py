"""迁移验收：零丢失核对 + 受保护 SHA + 残留引用检查，输出 migration/.../verification.md。"""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
WS = ROOT / ("songs/nianlun/sessions/20261030__unknown-model__"
             "nianlun-from-scratch-v3-20261030/workspace")
sys.stdout.reconfigure(encoding="utf-8")


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def sha_file(p):
    f = ROOT / p
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else ""


old_files = [l for l in git("ls-tree", "-r", "--name-only", "HEAD").split("\n") if l]
new_files = [l for l in git("ls-files").split("\n") if l]
moves = json.loads((WS / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
new_set = set(new_files)
missing = [p for p in old_files if p not in new_set and moves.get(p) not in new_set]
print("old tracked:", len(old_files), "new tracked:", len(new_files),
      "| old files without a new home:", len(missing))
for m in missing[:20]:
    print("   MISSING:", m)

# 受保护字节
protected = [p for p in old_files if p.startswith("research/baishuo/") or p.endswith(".zip")]
prot_rows = []
for p in protected:
    prot_rows.append((p, sha_file(p)))
print("protected files checked:", len(prot_rows))

# 残留旧路径引用（指向已移动但仍被引用的旧路径）
old_paths = {k for k, v in moves.items() if k != v}
stale = defaultdict(list)
pat = re.compile(r'(?:docs/reports|scratch)/[A-Za-z0-9_\-./]+\.(?:md|py|json|csv|txt|log|ustx)')
for f in new_files:
    if not f.endswith((".md", ".py", ".json", ".txt", ".yaml", ".yml", ".csv")):
        continue
    try:
        t = (ROOT / f).read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for m in set(pat.findall(t)):
        if m in old_paths:
            stale[m].append(f)
print("stale references to moved old paths:", len(stale))

out = dict(
    old_tracked=len(old_files), new_tracked=len(new_files),
    new_files=len([p for p in new_files if p not in old_files]),
    moved=len([k for k, v in moves.items() if k != v]),
    missing=missing,
    protected=[[p, s] for p, s in prot_rows],
    stale_refs={k: v[:5] for k, v in list(stale.items())[:50]},
    stale_count=len(stale),
    session_count=len([p for p in new_files if p.startswith("songs/") and "/sessions/" in p
                       and p.endswith("manifest.json")]),
)
(WS / "verification_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("sessions with manifest:", out["session_count"])
print("stale sample:", list(stale.items())[:5])
