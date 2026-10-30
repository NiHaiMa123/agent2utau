"""把 experiments/misc 里其实是「某首歌的局部修订/审计」的报告归回该歌的 session，
并重写 experiments/ 各目录 README（只列真实存在的实验入口，不堆空目录说明）。"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")

TARGETS = {
    "experiments/misc/reports/conditioned-voicing-feedback-20261011-audit.json":
        "songs/lastpage/sessions/20261011__unknown-model__lastpage-conditioned-voicing-20261011/reports/conditioned-voicing-feedback-20261011-audit.json",
    "experiments/misc/reports/li-kan-author-reference-20261011-audit.json":
        "songs/lastpage/sessions/20261011__unknown-model__lastpage-li-kan-author-reference-20261011/reports/li-kan-author-reference-20261011-audit.json",
    "experiments/misc/reports/whole-song-baseline-review-20261011-phrases.csv":
        "songs/lastpage/sessions/20261011__unknown-model__lastpage-accepted-baseline-20261011/reports/whole-song-baseline-review-20261011-phrases.csv",
    "experiments/misc/reports/first-phrase-firmness-r03-accepted-20261017.md":
        "songs/yuai/sessions/20261017__unknown-model__yuai-first-phrase-firmness-r03-20261017/reports/first-phrase-firmness-r03-accepted-20261017.md",
    "experiments/misc/reports/directory-reorganization-20261009.json":
        "docs/reports/maintenance/directory-reorganization-20261009.json",
}
rows = []
for old, new in TARGETS.items():
    src = ROOT / old
    if not src.exists():
        print("SKIP (missing)", old)
        continue
    dst = ROOT / new
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "-C", str(ROOT), "mv", old, new], capture_output=True, text=True)
    print(("OK  " if r.returncode == 0 else "FAIL"), old, "->", new)
    rows.append(dict(old_path=old, new_path=new, action="git-mv",
                     reason="phase-1 归入通用 experiments/misc 过粗；正文显示它是该歌的一次局部审计/修订",
                     sha_before="", sha_after="", references_checked="no reference",
                     status="moved" if r.returncode == 0 else "failed"))
with open(OUT / "session-consolidation.tsv", "a", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")

# ---- experiments/ README：只列真实入口 ----
EXPDOC = {
    "alignment": ("音素/歌词对齐", [
        "scripts/check_polyphones.py — 合成多音字串的音素切分探针（与任何歌曲无关）",
        "scripts/read_test_polyphones.py — 读取上述导出的音素表",
        "scripts/check_phones_structure.py — 读取音素/单元结构",
        "data/test_polyphones.json、data/test_modified_phones.json — 上述探针的导出数据",
    ], "本轮唯一有实际内容的对齐实验入口；歌曲专属的对齐/时钟脚本留在 songs/<song>/sessions/*/scripts。"),
    "pitch": ("音高", [],
              "暂无独立归档的音高实验；相关脚本目前分散在 songs/<song>/sessions/*/scripts（逐句画线、PITD 诊断）。"),
    "phonation": ("发声", [],
                  "暂无独立归档的发声实验；发声参数相关的研究与剂量-响应记录见 songs/<song>/sessions/*/reports。"),
    "evaluation": ("独立评价", [],
                   "生产级评价接口仍在 src/agent2utau/evaluation（不搬出）；此处只放方法实验脚本，目前为空。"),
    "misc": ("其它", [],
             "原 phase-1 归入此目录的 5 份报告已按正文证据归回各自歌曲 session 与 docs/reports/maintenance；此处暂无归档内容。"),
    "covers": ("试唱/对照", [],
               "面向某首歌的试唱与版本对照归 songs/<song>/sessions/*/scripts|reports；此处暂无归档内容。"),
    "diagnostics": ("诊断", [],
                    "通用诊断脚本目前仍在 scratch/（未确证归属的 7 项已于 phase-2 判定归位，scratch/ 现为空）。"),
    "research-tables": ("表1/表2 复核", [],
                        "研究表1/表2 的复核记录仍以 research/table1-*、research/table2-* 原地保留（字节保护）。"),
    "research-baishuo": ("白烁研究", [],
                         "白烁作者原件与研究证据仍在 research/baishuo（字节保护，不搬动）。"),
}
for cat, (title, entries, note) in EXPDOC.items():
    d = ROOT / "experiments" / cat
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# experiments/{cat} — {title}", "", note, ""]
    if entries:
        lines += ["## 当前已有入口", ""] + [f"- `{e}`" for e in entries] + [""]
    else:
        lines += ["## 当前已有入口", "", "（暂无）", ""]
    lines += ["---", "",
              "边界：只有**跨歌曲可复用**或**有明确对照协议**的方法实验放这里；",
              "属于某首歌的局部修订/试唱/审计留在 `songs/<song>/sessions/<session>/`。",
              "具备受控输入、断言、可重复 pass/fail 的测试才进 `tests/`；生产评价代码留在 `src/agent2utau/evaluation`。", ""]
    (d / "README.md").write_text("\n".join(lines), encoding="utf-8")
print("experiments READMEs rewritten:", len(EXPDOC))
