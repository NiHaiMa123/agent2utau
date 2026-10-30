"""定位 v3 score.ustx 反序列化失败的具体改动。"""
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
SCORE = V3 / "design" / "score.ustx"
TMP = ROOT / "scratch" / "bisect"
TMP.mkdir(parents=True, exist_ok=True)
cfg = load_config()


def test(tag, doc):
    p = TMP / f"{tag}.ustx"
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000)
    out = TMP / f"{tag}_pitch.json"
    rep = run_bridge(cfg, ["export-pitch", "--project", str(p.resolve()), "--out", str(out.resolve())])
    ok = rep.get("ok")
    print(f"{tag:24s} ok={ok} {'' if ok else rep.get('errors')}")
    return ok


base = yaml.safe_load(SCORE.read_text(encoding="utf-8"))

# A: 去掉全部曲线
a = json.loads(json.dumps(base))
for part in a["voice_parts"]:
    part["curves"] = []
test("A_no_curves", a)

# B: 只留 voic
b = json.loads(json.dumps(base))
for part in b["voice_parts"]:
    part["curves"] = [c for c in part["curves"] if c["abbr"] == "voic"]
test("B_voic_only", b)

# C: 只留 brec
c = json.loads(json.dumps(base))
for part in c["voice_parts"]:
    part["curves"] = [x for x in part["curves"] if x["abbr"] == "brec"]
test("C_brec_only", c)

# D: 只留 tenc
d = json.loads(json.dumps(base))
for part in d["voice_parts"]:
    part["curves"] = [x for x in part["curves"] if x["abbr"] == "tenc"]
test("D_tenc_only", d)

# E: 只留 dyn
e = json.loads(json.dumps(base))
for part in e["voice_parts"]:
    part["curves"] = [x for x in part["curves"] if x["abbr"] == "dyn"]
test("E_dyn_only", e)

# F: 全部曲线，但 xs 去重（相邻重复只留一个）
f = json.loads(json.dumps(base))
for part in f["voice_parts"]:
    for cv in part["curves"]:
        xs, ys = [], []
        for x, y in zip(cv["xs"], cv["ys"]):
            if xs and xs[-1] == x:
                continue
            xs.append(x)
            ys.append(y)
        cv["xs"], cv["ys"] = xs, ys
test("F_dedup_xs", f)
