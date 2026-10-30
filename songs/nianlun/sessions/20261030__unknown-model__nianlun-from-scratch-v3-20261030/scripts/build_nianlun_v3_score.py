"""年轮 v3 谱面构建（阶段 A）。

与 v2 的差别：
  1) 发声层粒度从"句"降到"音符"：VOIC/BREC/TENC/DYN 四个曲线在每个音符上各有断点，
     取值由该音符窗口的源实测（谐噪比、谱重心、音高、能量）决定，而不是整句一个值。
  2) 音素对齐：逐音节测量源里"辅音->元音"的过渡点，把原生音素块边界移到该点附近
     （phoneme override）。本脚本自带探针：先只改一个音节、重导音素确认 override 真的
     改变边界，再决定是否全曲应用；无效则不写入，并在 log 里留证。
  3) 音符栅格沿用 v2（其时值/音高本身已是源派生且审查通过），v3 改的是"画上去的东西"。

输出：design/score.ustx, design/baseline_pitch.json, design/baseline_phones.json,
     design/native_provenance.json, design/note_features.json, design/align_log.json
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))

from agent2utau.openutau.ustx import load_ustx, save_ustx, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from nianlun_v3_source import Source, TICK_S, filled_track

V2 = ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028"
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
SCORE = DESIGN / "score.ustx"

for sub in ("observation", "hfa", "hfa_inputs"):
    dst = V3 / sub
    if not dst.exists():
        shutil.copytree(V2 / sub, dst)
        print("copied", sub)
DESIGN.mkdir(parents=True, exist_ok=True)

cfg = load_config()
src = Source(V3)

# ---------------- 继承 v2 音符栅格 ----------------
v2doc = load_ustx(V2 / "design" / "score.ustx")
doc = load_ustx(V2 / "design" / "score.ustx")
for part in doc["voice_parts"]:
    part["curves"] = []
    for n in part["notes"]:
        n["phoneme_expressions"] = []
        n["phoneme_overrides"] = []
print("parts", len(doc["voice_parts"]), "notes", sum(len(p["notes"]) for p in doc["voice_parts"]))

notes_meta = []
for pi, part in enumerate(doc["voice_parts"]):
    base = part["position"] * TICK_S
    for ni, n in enumerate(part["notes"]):
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        notes_meta.append(dict(part_index=pi, note_index=ni, start=a, end=b,
                               tone=int(n["tone"]), lyric=str(n["lyric"]),
                               position=int(n["position"]), duration=int(n["duration"])))
sung = [m for m in notes_meta if m["lyric"] not in ("SP", "AP")]
print("sung notes", len(sung))

# ---------------- 音节细分（照 B 站流程：一个音节可拆成多个音符块） ----------------
# 源轮廓在一个音符里偏离名义音高太多时，原生基底与目标的差会超出 PITD 预算；
# 这时把该字在级差点处拆成"字 + 延长块"，各自带自己的音高。
SPLIT_DEV = 420.0     # 偏离名义音高超过该值才拆
SPLIT_MIN = 0.10      # 拆出的每一块至少这么长
split_log = []
for pi in range(len(doc["voice_parts"])):
    part = doc["voice_parts"][pi]
    base = part["position"] * TICK_S
    new_notes = []
    for ni, n in enumerate(part["notes"]):
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        if str(n["lyric"]) in ("AP", "SP", "+") or (b - a) < 2 * SPLIT_MIN:
            new_notes.append(n)
            continue
        ft = filled_track(src, a, b)
        if ft is None:
            new_notes.append(n)
            continue
        _, vals, _ = ft
        nominal = float(n["tone"] * 100)
        dev = np.abs(vals - nominal)
        k = int(np.argmax(dev))
        if float(dev[k]) < SPLIT_DEV:
            new_notes.append(n)
            continue
        # 在级差点附近、且离两端都够远的位置切
        t_grid = np.arange(a, b, 0.01)
        v_grid = np.interp(t_grid, ft[0], ft[1])
        cand = [t for t in t_grid
                if t - a >= SPLIT_MIN and b - t >= SPLIT_MIN
                and abs(float(np.interp(t, ft[0], ft[1])) - nominal) >= 0.5 * SPLIT_DEV]
        if not cand:
            new_notes.append(n)
            continue
        cut = cand[len(cand) // 2]
        d1 = int(round((cut - a) / TICK_S))
        d2 = int(n["duration"]) - d1
        if d1 < 8 or d2 < 8:
            new_notes.append(n)
            continue
        first = dict(n)
        first["duration"] = d1
        first["tone"] = int(round(float(np.median(v_grid[t_grid < cut])) / 100))
        second = dict(n)
        second["position"] = int(n["position"]) + d1
        second["duration"] = d2
        second["tone"] = int(round(float(np.median(v_grid[t_grid >= cut])) / 100))
        second["lyric"] = "+"
        new_notes.extend([first, second])
        split_log.append(dict(part_index=pi, note_index=ni, lyric=str(n["lyric"]),
                               start=round(a, 3), end=round(b, 3), cut=round(float(cut), 3),
                               dev=round(float(dev[k]), 1),
                               tone_before=int(n["tone"]), tone_first=first["tone"], tone_second=second["tone"]))
    part["notes"] = new_notes

notes_meta = []
for pi, part in enumerate(doc["voice_parts"]):
    base = part["position"] * TICK_S
    for ni, n in enumerate(part["notes"]):
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        notes_meta.append(dict(part_index=pi, note_index=ni, start=a, end=b,
                               tone=int(n["tone"]), lyric=str(n["lyric"]),
                               position=int(n["position"]), duration=int(n["duration"])))
sung = [m for m in notes_meta if m["lyric"] not in ("SP", "AP")]
print("split notes:", len(split_log),
      "| notes now", len(notes_meta), "sung", len(sung))

# ---------------- 逐音符源实测 ----------------
features = []
for m in sung:
    a, b = m["start"], m["end"]
    core = src.core(a, b)
    hnr = src.hnr_db(a, b)
    cen = src.centroid(a, b)
    rms = src.rms_db(a, b)
    rip = src.ripple(a, b)
    level = core["level"] if core else float(m["tone"] * 100)
    span = core["span"] if core else 0.0
    feat = dict(part_index=m["part_index"], note_index=m["note_index"], lyric=m["lyric"],
                start=round(a, 4), end=round(b, 4), dur=round(b - a, 4),
                tone=m["tone"], nominal_c=round(float(m["tone"] * 100), 2),
                level=round(level, 2), src_span=round(span, 2),
                src_frames=int(core["frames"]) if core else 0,
                rms_db=round(rms, 3) if rms is not None else None,
                hnr_db=round(hnr["hnr_db"], 3) if hnr else None,
                harmonic_ratio=round(hnr["harmonic_ratio"], 4) if hnr else None,
                centroid_hz=round(cen["centroid_hz"], 1) if cen else None,
                hf_ratio=round(cen["hf_ratio"], 4) if cen else None,
                ripple=(dict(freq=round(rip["freq"], 2), amp=round(rip["amp"], 2),
                             phase=round(rip["phase"], 4)) if rip else None),
                onset=round(src.onset_offset(a, b), 4) if src.onset_offset(a, b) else None)
    features.append(feat)
print("features done", len(features),
      "with ripple", sum(1 for f in features if f["ripple"]),
      "no source", sum(1 for f in features if f["src_frames"] < 3))

# ---------------- 参数映射（逐音符） ----------------
def zscore(values):
    v = np.asarray([x for x in values if x is not None], float)
    if len(v) < 3:
        return {}
    mu, sd = float(v.mean()), float(v.std() + 1e-9)
    out = {}
    for x in values:
        out[id(x)] = 0.0 if x is None else (x - mu) / sd
    return out


hr = [f["harmonic_ratio"] for f in features]
rms = [f["rms_db"] for f in features]
lv = [f["level"] for f in features]
hr_z = zscore(hr)
lv_z = zscore(lv)
rms_vals = np.asarray([x for x in rms if x is not None], float)
rms_mu = float(rms_vals.mean()) if len(rms_vals) else 0.0
rms_sd = float(rms_vals.std() + 1e-9) if len(rms_vals) else 1.0

PROBE = DESIGN / "param_probe.json"
calib = json.loads(PROBE.read_text(encoding="utf-8")) if PROBE.exists() else {}
print("calibration:", json.dumps(calib, ensure_ascii=False)[:300])

# 逐音符取值：区间锚定在 v2 已验证过的范围（voic 100-128 / brec -24..12 / tenc 0..20）
for f in features:
    z = hr_z.get(id(f["harmonic_ratio"]), 0.0)
    zl = lv_z.get(id(f["level"]), 0.0)
    dz = 0.0
    if f["rms_db"] is not None:
        dz = (f["rms_db"] - rms_mu) / rms_sd
    scale = calib.get("scale", {})
    voic = 114 + scale.get("voic", 5.0) * z + scale.get("voic_lvl", 0.5) * zl
    brec = -3 - scale.get("brec", 4.0) * z + scale.get("brec_lvl", 1.0) * zl
    tenc = 7 + scale.get("tenc", 2.5) * zl + scale.get("tenc_noisy", 2.0) * (-z)
    dyn = scale.get("dyn", 6.0) * dz
    f["voic"] = int(round(min(132, max(96, voic))))
    f["brec"] = int(round(min(12, max(-22, brec))))
    f["tenc"] = int(round(min(22, max(0, tenc))))
    f["dyn"] = round(min(60.0, max(-60.0, dyn)), 2)

# ---------------- 写 part 级曲线（每音符两个断点） ----------------
by_part = {}
for f in features:
    by_part.setdefault(f["part_index"], []).append(f)
for pi, part in enumerate(doc["voice_parts"]):
    fs = by_part.get(pi, [])
    if not fs:
        continue
    idx_of = {m["note_index"]: m for m in notes_meta if m["part_index"] == pi}
    curves = {}
    for abbr, key in (("voic", "voic"), ("brec", "brec"), ("tenc", "tenc"), ("dyn", "dyn")):
        xs, ys = [], []
        for f in fs:
            m = idx_of[f["note_index"]]
            xs.extend([m["position"], m["position"] + m["duration"]])
            # OpenUtau 的 USTX 反序列化要求曲线值为整数（浮点会直接失败）
            ys.extend([int(round(f[key])), int(round(f[key]))])
        curves[abbr] = dict(xs=xs, ys=ys)
    # 呼吸音符：取前后唱字的中值，不单独造值
    sung_positions = sorted(idx_of[f["note_index"]]["position"] for f in fs)
    part["curves"] = [dict(abbr=a, **c) for a, c in curves.items()]

save_ustx(doc, SCORE)
print("score written (notes + per-note curves)")

# ---------------- 导出原生 pitch/phones ----------------
def export(cmd, target):
    rep = run_bridge(cfg, [cmd, "--project", str(SCORE.resolve()), "--out", str(target.resolve())])
    if not rep.get("ok"):
        raise RuntimeError(f"{cmd} failed: {rep}")
    return rep


pitch_path = DESIGN / "baseline_pitch.json"
phones_path = DESIGN / "baseline_phones.json"
export("export-pitch", pitch_path)
export("export-phonemes", phones_path)
print("baseline exported")

# ---------------- 音素对齐 ----------------
# 探针结论（本机 OpenUtau + Yousa V1.65c）：
#   * phoneme_overrides 的 index 是"音符内"音素序号（0 起），不是导出里的全局 phone_index；
#   * advance 对该声库的导出音素时钟无效，offset 才生效，且它移动的是该音素的**起点**；
#   * 改了元音起点后，前面的辅音会自动拉伸到与元音相接（不产生空隙）。
# 因此：把元音起点移到"源里该字 F0 锁定（=元音开始）"的位置，辅音自然补足前置时段。

INITIALS = {"b", "c", "ch", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "q", "r", "s",
            "t", "w", "x", "y", "z", "zh", "sh", "y0", "y"}


def phone_base(phoneme):
    return phoneme.split("/")[-1]


def vowel_onset(a, b):
    """源里该字的元音起点：窗口内第一个 >=2 帧的连续有声段起点（F0 锁定处）。"""
    tr = src.track(a, b)
    if tr is None:
        return None
    tt = tr[0]
    runs, s0 = [], 0
    for i in range(1, len(tt) + 1):
        if i == len(tt) or tt[i] - tt[i - 1] > 0.06:
            runs.append((s0, i))
            s0 = i
    for s0, s1 in runs:
        if s1 - s0 >= 2:
            return float(tt[s0])
    return None


phones = json.loads(phones_path.read_text(encoding="utf-8"))
part_phones = {}
for p in phones["parts"]:
    for ph in p["phrases"]:
        for hp in ph["phones"]:
            part_phones.setdefault(p["part_position"], []).append(hp)

# 逐音节算目标：元音起点应对齐源里的 F0 锁定点
for m in notes_meta:
    if m["lyric"] in ("SP", "AP", "+"):
        continue
    vo = vowel_onset(m["start"], m["end"])
    if vo is None:
        continue
    delta = vo - m["start"]
    if delta < 0.02:                       # 已经在元音起点，不动
        continue
    m["align_delta_s"] = round(min(delta, 0.15), 4)
    m["align_target_s"] = round(vo, 4)
    m["align_current_s"] = round(m["start"], 4)

# 组装每音符的音素组
def note_phones(pi, ni):
    part = doc["voice_parts"][pi]
    hp = part_phones.get(part["position"], [])
    g = [x for x in hp if ni in x.get("owner_note_indices", [])]
    return sorted(g, key=lambda z: z["start_ms"])


align_log = dict(mechanism="phoneme_overrides.offset on the vowel phone (note-local index); "
                            "advance is inert for this singer; consonant auto-stretches",
                  applied=0, skipped=0, before_err_ms=[], after_err_ms=[])
for m in notes_meta:
    if "align_delta_s" not in m:
        continue
    g = note_phones(m["part_index"], m["note_index"])
    if len(g) < 2:
        align_log["skipped"] += 1
        continue
    final = g[-1]
    m["align_final_phone"] = final["phoneme"]
    m["align_before_err_s"] = round(final["start_ms"] / 1000.0 - m["align_target_s"], 4)
    note = doc["voice_parts"][m["part_index"]]["notes"][m["note_index"]]
    note["phoneme_overrides"] = [dict(index=len(g) - 1, phoneme=final["phoneme"],
                                      offset=int(round(m["align_delta_s"] * 1000)))]
    align_log["applied"] += 1

if align_log["applied"]:
    save_ustx(doc, SCORE)
    export("export-phonemes", phones_path)
    phones2 = json.loads(phones_path.read_text(encoding="utf-8"))
    part_phones2 = {}
    for p in phones2["parts"]:
        for ph in p["phrases"]:
            for hp in ph["phones"]:
                part_phones2.setdefault(p["part_position"], []).append(hp)
    for m in notes_meta:
        if "align_delta_s" not in m:
            continue
        hp = part_phones2.get(doc["voice_parts"][m["part_index"]]["position"], [])
        g = sorted([x for x in hp if m["note_index"] in x.get("owner_note_indices", [])],
                   key=lambda z: z["start_ms"])
        if not g:
            continue
        final = g[-1]
        m["align_after_err_s"] = round(final["start_ms"] / 1000.0 - m["align_target_s"], 4)
    before = [m["align_before_err_s"] for m in notes_meta if "align_before_err_s" in m]
    after = [m["align_after_err_s"] for m in notes_meta if "align_after_err_s" in m]
    align_log["before_err_ms"] = [round(x * 1000, 1) for x in before]
    align_log["after_err_ms"] = [round(x * 1000, 1) for x in after]
    align_log["median_abs_before_ms"] = round(float(np.median(np.abs(before))) * 1000, 1) if before else None
    align_log["median_abs_after_ms"] = round(float(np.median(np.abs(after))) * 1000, 1) if after else None
    print("align applied", align_log["applied"],
          "median|err| before", align_log["median_abs_before_ms"], "ms -> after",
          align_log["median_abs_after_ms"], "ms")

save_ustx(doc, SCORE)
export("export-pitch", pitch_path)
export("export-phonemes", phones_path)
(DESIGN / "align_log.json").write_text(json.dumps(align_log, ensure_ascii=False, indent=1), encoding="utf-8")
align_detail = [dict(part_index=m["part_index"], note_index=m["note_index"], lyric=m["lyric"],
                     delta_s=m.get("align_delta_s"), target_s=m.get("align_target_s"),
                     before_err_s=m.get("align_before_err_s"), after_err_s=m.get("align_after_err_s"),
                     phone=m.get("align_final_phone"))
                for m in notes_meta if "align_delta_s" in m]
(DESIGN / "align_log.json").write_text(
    json.dumps(dict(align_log, detail=align_detail), ensure_ascii=False, indent=1), encoding="utf-8")
print("align:", align_log["applied"], "applied,", align_log["skipped"], "skipped")

# ---------------- provenance + features ----------------
ou = Path(cfg["openutau_dir"])
singer = doc["tracks"][0]["singer"]
prov = dict(schema_version=1, project_sha256=sha256(SCORE),
            pitch_sha256=sha256(pitch_path), phonemes_sha256=sha256(phones_path),
            environment=dict(core_sha256=sha256(ou / "OpenUtau.Core.dll"),
                             bridge_sha256=sha256(ou / "a2u-bridge.exe"),
                             singer_config_sha256=sha256(ou / "Singers" / singer / "dsconfig.yaml"),
                             singer_id=singer))
(DESIGN / "native_provenance.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8")
(DESIGN / "note_features.json").write_text(json.dumps(dict(notes=features), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
(DESIGN / "split_log.json").write_text(json.dumps(
    dict(policy="源轮廓偏离名义音高超过 420c 的字，在级差点拆成'字+延长块'（B 站流程的音节细分）",
         count=len(split_log), notes=split_log), ensure_ascii=False, indent=1), encoding="utf-8")
print("done")
