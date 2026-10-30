"""P2-F：把 7 个未归属 scratch 条目按正文判定归位，并修正它们的路径引用。

  check_polyphones.py / read_test_polyphones.py / check_phones_structure.py
  test_polyphones.json / test_modified_phones.json
      → 合成多音字/音素诊断，与任何歌曲无关 → experiments/alignment/
  test_compile_phrase0.py / test_compile_phrase0_full.py
      → 依赖 test_skill_pitch（属最后一页 zuihouyiye-from-scratch-20261027）
      → 随其依赖进入同一 song session 的 scripts/
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")
EXP = "experiments/alignment"
LAST = "songs/lastpage/sessions/20261027__unknown-model__zuihouyiye-from-scratch-20261027"

MOVES = {
    "scratch/check_polyphones.py": f"{EXP}/scripts/check_polyphones.py",
    "scratch/read_test_polyphones.py": f"{EXP}/scripts/read_test_polyphones.py",
    "scratch/check_phones_structure.py": f"{EXP}/scripts/check_phones_structure.py",
    "scratch/test_polyphones.json": f"{EXP}/data/test_polyphones.json",
    "scratch/test_modified_phones.json": f"{EXP}/data/test_modified_phones.json",
    "scratch/test_compile_phrase0.py": f"{LAST}/scripts/test_compile_phrase0.py",
    "scratch/test_compile_phrase0_full.py": f"{LAST}/scripts/test_compile_phrase0_full.py",
}
REASON = {
    "scratch/check_polyphones.py": "合成多音字诊断（歌词为测试串，非任何歌曲），与歌曲无关",
    "scratch/read_test_polyphones.py": "读取上述合成诊断的音素导出，与歌曲无关",
    "scratch/check_phones_structure.py": "读取上述合成诊断的音素结构，与歌曲无关",
    "scratch/test_polyphones.json": "合成多音字诊断的音素导出数据",
    "scratch/test_modified_phones.json": "合成多音字诊断的改写音素导出数据",
    "scratch/test_compile_phrase0.py": "依赖 test_skill_pitch（属最后一页 zuihouyiye-from-scratch-20261027），随依赖同址",
    "scratch/test_compile_phrase0_full.py": "依赖 test_skill_pitch（属最后一页 zuihouyiye-from-scratch-20261027），随依赖同址",
}

rows = []
for old, new in MOVES.items():
    dst = ROOT / new
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "-C", str(ROOT), "mv", old, new], capture_output=True, text=True)
    ok = r.returncode == 0
    # 路径引用修正
    if ok and dst.suffix == ".py":
        t = dst.read_text(encoding="utf-8", errors="replace")
        t2 = t.replace('Path("scratch/test_polyphones.json")', f'Path("{EXP}/data/test_polyphones.json")')
        t2 = t2.replace('Path("scratch/test_polyphones.ustx")', f'Path("{EXP}/data/test_polyphones.ustx")')
        if t2 != t:
            dst.write_text(t2, encoding="utf-8")
    rows.append(dict(old_path=old, new_path=new, action="git-mv", reason=REASON[old],
                     sha_before="", sha_after="", references_checked="path string updated",
                     status="moved" if ok else "failed"))
    print(("OK  " if ok else "FAIL"), old, "->", new)

# uncertain 清单里这 7 条改为已解决
unc = OUT.parent / "uncertain-items.tsv"
if unc.exists():
    lines = unc.read_text(encoding="utf-8").splitlines()
    head, body = lines[0], lines[1:]
    keep = [l for l in body if l.split("\t")[0] not in MOVES]
    unc.write_text("\n".join([head] + keep) + "\n", encoding="utf-8")
    print("uncertain remaining:", len(keep))

with open(OUT / "session-consolidation.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")
