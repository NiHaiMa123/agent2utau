"""修两处：歌曲 README 的 session 链接前缀；以及因 reports 归位而失效的 4 处引用。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

# 1) 歌曲 README：session 链接应指向 sessions/<sid>/
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    p = ROOT / "songs" / song / "README.md"
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    t2 = re.sub(r"\]\((\d{8}__[^)]+)/\)", r"](sessions/\1/)", t)
    if t2 != t:
        p.write_text(t2, encoding="utf-8")
        print("session links fixed:", song)

# 2) 因 first-phrase-firmness-r03 归位而失效的引用
OLD = "experiments/misc/reports/first-phrase-firmness-r03-accepted-20261017.md"
NEW = "songs/yuai/sessions/20261017__unknown-model__yuai-first-phrase-firmness-r03-20261017/reports/first-phrase-firmness-r03-accepted-20261017.md"
targets = ["AGENTS.md", "README.md", "plan.md",
           "docs/reports/production/skill-local-phonation-accepted-20261017.md"]
for rel in targets:
    p = ROOT / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    if OLD not in t:
        continue
    # 根目录文档用仓库根相对路径；docs/reports/production 下用相对路径
    if rel.startswith("docs/"):
        new = "../../../" + NEW
    else:
        new = NEW
    p.write_text(t.replace(OLD, new), encoding="utf-8")
    print("reference fixed:", rel)
