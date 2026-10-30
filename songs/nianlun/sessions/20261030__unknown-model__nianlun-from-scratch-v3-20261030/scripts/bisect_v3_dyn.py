"""dyn 曲线失败的具体原因：整数 vs 浮点 / 数值范围。"""
import json
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
cfg = load_config()
base = yaml.safe_load(SCORE.read_text(encoding="utf-8"))


def test(tag, doc):
    p = TMP / f"{tag}.ustx"
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000)
    out = TMP / f"{tag}_pitch.json"
    rep = run_bridge(cfg, ["export-pitch", "--project", str(p.resolve()), "--out", str(out.resolve())])
    print(f"{tag:28s} ok={rep.get('ok')} {'' if rep.get('ok') else rep.get('errors')}")


def only_dyn(doc, fn):
    d = json.loads(json.dumps(doc))
    for part in d["voice_parts"]:
        for cv in part["curves"]:
            if cv["abbr"] == "dyn":
                cv["ys"] = fn(cv["ys"])
    return d


test("G_dyn_int", only_dyn(base, lambda ys: [int(round(y)) for y in ys]))
test("H_dyn_zero", only_dyn(base, lambda ys: [0 for y in ys]))
test("I_dyn_float_half", only_dyn(base, lambda ys: [float(y) / 2 for y in ys]))
# v2 的 dyn 曲线直接搬到 v3（整数）
v2 = yaml.safe_load((ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028" / "design" / "score.ustx").read_text(encoding="utf-8"))
j = json.loads(json.dumps(base))
for pi, part in enumerate(j["voice_parts"]):
    part["curves"] = [c for c in part["curves"] if c["abbr"] != "dyn"]
    part["curves"].extend([dict(c) for c in v2["voice_parts"][pi]["curves"] if c["abbr"] == "dyn"])
test("J_dyn_from_v2", j)
