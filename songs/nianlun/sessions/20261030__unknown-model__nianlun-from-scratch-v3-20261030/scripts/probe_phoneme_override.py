"""探针：phoneme_overrides 的正确写法。

问题：先前用全局 phone_index 写 override，导出音素边界没动。
本探针在同一个音节上分别试：
  A) 全局 phone_index + advance
  B) 音符内索引(0 起) + advance
  C) 音符内索引 + offset
  D) 音符内索引 + advance+offset
每种都重导音素，比较 zh/van 的 start_ms 是否按预期移动。
"""
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
TMP.mkdir(parents=True, exist_ok=True)
cfg = load_config()
base = yaml.safe_load(SCORE.read_text(encoding="utf-8"))
phones = json.loads((V3 / "design" / "baseline_phones.json").read_text(encoding="utf-8"))

part0 = phones["parts"][0]
pos = part0["part_position"]
hp = []
for ph in part0["phrases"]:
    hp.extend(ph["phones"])
# 找第一个有两个音素、且不是 AP 的音符
target = None
for x in hp:
    if x["phoneme"].startswith("zh/") and x["owner_note_indices"]:
        owner = x["owner_note_indices"][0]
        same = [y for y in hp if owner in y.get("owner_note_indices", [])]
        if len(same) >= 2:
            target = (owner, sorted(same, key=lambda z: z["start_ms"]))
            break
owner, group = target
print("owner note", owner, [(g["phone_index"], g["phoneme"], round(g["start_ms"], 1),
                             round(g["end_ms"], 1)) for g in group])
final = group[-1]
cur_start = final["start_ms"]
print("final phoneme", final["phoneme"], "global index", final["phone_index"])


def run(tag, overrides):
    doc = json.loads(json.dumps(base))
    part = doc["voice_parts"][0]
    part["notes"][owner]["phoneme_overrides"] = overrides
    p = TMP / f"probe_{tag}.ustx"
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000)
    out = TMP / f"probe_{tag}_phones.json"
    rep = run_bridge(cfg, ["export-phonemes", "--project", str(p.resolve()), "--out", str(out.resolve())])
    if not rep.get("ok"):
        print(f"{tag:22s} FAILED {rep.get('errors')}")
        return
    d = json.loads(out.read_text(encoding="utf-8"))
    got = None
    for pp in d["parts"]:
        if pp["part_position"] != pos:
            continue
        for ph in pp["phrases"]:
            for x in ph["phones"]:
                if x["phoneme"] == final["phoneme"] and owner in x.get("owner_note_indices", []):
                    got = x
    if got is None:
        print(f"{tag:22s} phone not found")
        return
    print(f"{tag:22s} start={got['start_ms']:.1f} end={got['end_ms']:.1f} "
          f"delta={got['start_ms'] - cur_start:+.1f}ms")


run("A_global_idx_adv", [dict(index=int(final["phone_index"]), phoneme=final["phoneme"], advance=60)])
run("B_local_idx_adv", [dict(index=len(group) - 1, phoneme=final["phoneme"], advance=60)])
run("C_local_idx_off", [dict(index=len(group) - 1, phoneme=final["phoneme"], offset=60)])
run("D_local_both", [dict(index=len(group) - 1, phoneme=final["phoneme"], advance=60, offset=60)])
run("E_local_adv_neg", [dict(index=len(group) - 1, phoneme=final["phoneme"], advance=-60)])
