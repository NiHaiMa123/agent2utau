"""探针2：辅音侧 offset 行为 + 负 offset 是否可用。"""
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
phones = json.loads((V3 / "design" / "baseline_phones.json").read_text(encoding="utf-8"))
part0 = phones["parts"][0]
pos = part0["part_position"]
hp = []
for ph in part0["phrases"]:
    hp.extend(ph["phones"])
owner, group = 1, sorted([y for y in hp if 1 in y.get("owner_note_indices", [])],
                          key=lambda z: z["start_ms"])
init, final = group[0], group[-1]
print("init", init["phoneme"], init["start_ms"], init["end_ms"])
print("final", final["phoneme"], final["start_ms"], final["end_ms"])


def run(tag, overrides, show=("zh/y0", "zh/van")):
    doc = json.loads(json.dumps(base))
    doc["voice_parts"][0]["notes"][owner]["phoneme_overrides"] = overrides
    p = TMP / f"p2_{tag}.ustx"
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000)
    out = TMP / f"p2_{tag}_phones.json"
    rep = run_bridge(cfg, ["export-phonemes", "--project", str(p.resolve()), "--out", str(out.resolve())])
    if not rep.get("ok"):
        print(f"{tag:26s} FAILED {rep.get('errors')}")
        return
    d = json.loads(out.read_text(encoding="utf-8"))
    rows = []
    for pp in d["parts"]:
        if pp["part_position"] != pos:
            continue
        for ph in pp["phrases"]:
            for x in ph["phones"]:
                if owner in x.get("owner_note_indices", []):
                    rows.append((x["phoneme"], x["start_ms"], x["end_ms"]))
    print(f"{tag:26s} " + " | ".join(f"{n}[{s:.1f},{e:.1f}]" for n, s, e in rows))


run("init_off_plus60", [dict(index=0, phoneme=init["phoneme"], offset=60)])
run("init_off_minus60", [dict(index=0, phoneme=init["phoneme"], offset=-60)])
run("final_off_minus40", [dict(index=1, phoneme=final["phoneme"], offset=-40)])
run("both_init60_final60", [dict(index=0, phoneme=init["phoneme"], offset=60),
                            dict(index=1, phoneme=final["phoneme"], offset=60)])
