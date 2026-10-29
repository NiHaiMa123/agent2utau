"""年轮 v2 画线：逐句从源实测生成中心线/连接/字腹动作 + 每句发声层。

与 v1 的根本差别：
  * 中心线不再用"平台 + 固定 ±12c 微凹 + 40ms 垂直台阶"，而是：
      音符电平取源实测（双检测器一致口径），字腹取源在该字内的真实残差（缩放 0.75），
      字间连接是 70-250ms 的平滑斜坡（带轻微承接/过冲），不是垂直落差。
  * 动作组件不再给每个字套同一个 ±52c 鼓包：
      长字且源有周期性 -> oscillation（深度/频率取自源）；源有单次明显拐点 -> finite_return；
      源内该字无独立走势 -> 不加组件，判为贴合源线的 hold/center，并写明理由。
  * 发声层按句实测（源句 RMS/音高区间）逐句给 VOIC/TENC/BREC/DYN，不再只有 7 种区间。
  * 检查改为可证伪：range 绑定源实测跨度、direction 绑定到达方向、cycles 绑定源周期数。

顺序：score 加发声曲线 -> 重导原生 -> inventory -> context -> intent brief -> freeze
      -> plan -> ledger。plan 生成前不写任何数值。
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")

from agent2utau.openutau.ustx import TempoMap, load_ustx, save_ustx, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.evaluation.execution_review import build_inventory, validate_inventory, digest
from agent2utau.evaluation.musical_review import freeze_intent
from agent2utau.resources.config import load_config

V2 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
DESIGN = V2 / "design"
SCORE = DESIGN / "score.ustx"
TICK_S = 60.0 / (120.0 * 480)


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


# ---------------- 源观测 ----------------
zf = np.load(V2 / "observation" / "fcpe.npz")
zr = np.load(V2 / "observation" / "rmvpe.npz")
t_f, f0_f = zf["times"].astype(float), zf["f0_hz"].astype(float)
t_r, f0_r = zr["times"].astype(float), zr["f0_hz"].astype(float)
c_f = np.where(f0_f > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)
c_r = np.where(f0_r > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_r, 1e-6) / 440.0), np.nan)
rf = np.interp(t_f, t_f, c_f)
rr = np.interp(t_f, t_r, c_r)
agree = np.isfinite(rf) & np.isfinite(rr) & (np.abs(rf - rr) <= 120)
c_all = np.where(agree, (rf + rr) / 2.0, np.nan)

stem, sr = sf.read(str(V2 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"), dtype="float32")
if stem.ndim > 1:
    stem = stem.mean(axis=1)

hfa = rj(V2 / "hfa" / "hfa_summary.json")
hfa_by_pid = {p["phrase_id"]: p for p in hfa["phrases"]}

doc = load_ustx(SCORE)
tm = TempoMap.from_doc(doc)
cfg = load_config()


def src_track(a, b):
    m = (t_f >= a) & (t_f < b) & agree
    if m.sum() < 3:
        return None
    return t_f[m], c_all[m]


def phrase_of_part(pi):
    return hfa["phrases"][pi]


# ---------------- 每句的源实测（用于发声层与意图观察） ----------------
def phrase_metrics(a, b):
    seg = stem[int(a * sr):int(b * sr)]
    if len(seg) < 100:
        return None
    rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-12)
    sp = np.abs(np.fft.rfft(seg[: min(len(seg), 32768)]))
    fr = np.fft.rfftfreq(min(len(seg), 32768), 1.0 / sr)
    cen = float((sp * fr).sum() / (sp.sum() + 1e-12))
    m = (t_f >= a) & (t_f < b) & agree
    f0m = float(np.median(c_all[m])) if m.sum() else 6000.0
    return dict(rms_db=20 * np.log10(rms + 1e-12), centroid_hz=cen, f0_cents=f0m)


ROLE = {}
for pi in range(51):
    if pi in (0, 1, 2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 26, 27, 28, 29):
        ROLE[pi] = "verse1" if pi <= 7 else "verse2"
    elif pi in (8, 9, 10, 11, 12, 13, 14, 15, 30, 31, 32, 33, 34, 35, 36, 37):
        ROLE[pi] = "prechorus1" if pi <= 15 else "prechorus2"
    elif pi in (16, 17, 18, 19, 20, 21, 38, 39, 40, 41, 42, 43):
        ROLE[pi] = "chorus1" if pi <= 21 else "chorus2"
    elif pi in (44, 45, 46, 47, 48, 49):
        ROLE[pi] = "chorus3"
    else:
        ROLE[pi] = "outro"

ROLE_BASE = {
    "verse1":   dict(voic=104, brec=6, tenc=0, dyn=0.0),
    "verse2":   dict(voic=103, brec=7, tenc=0, dyn=0.0),
    "prechorus1": dict(voic=109, brec=3, tenc=3, dyn=2.0),
    "prechorus2": dict(voic=108, brec=4, tenc=3, dyn=2.0),
    "chorus1":  dict(voic=115, brec=-3, tenc=7, dyn=4.0),
    "chorus2":  dict(voic=118, brec=-5, tenc=9, dyn=5.5),
    "chorus3":  dict(voic=121, brec=-7, tenc=11, dyn=6.5),
    "outro":    dict(voic=110, brec=2, tenc=4, dyn=3.0),
}

# ---------------- STEP 1: 发声层（每句实测驱动，逐句不同） ----------------
metrics = {}
for pi in range(51):
    vp = doc["voice_parts"][pi]
    notes = vp["notes"]
    a = (vp["position"] + notes[0]["position"]) * TICK_S
    b = (vp["position"] + notes[-1]["position"] + notes[-1]["duration"]) * TICK_S
    metrics[pi] = phrase_metrics(a, b)

# 句级相对电平（源实测 -> 相对段内均值）
by_role = {}
for pi, m in metrics.items():
    by_role.setdefault(ROLE[pi], []).append(m["rms_db"])
role_mean = {k: float(np.mean(v)) for k, v in by_role.items()}

for pi in range(51):
    vp = doc["voice_parts"][pi]
    notes = vp["notes"]
    base = ROLE_BASE[ROLE[pi]]
    m = metrics[pi]
    # 源句电平相对本段均值的偏差 -> 覆盖/支撑强度；音高越高 -> 张力略增
    lvl_dev = m["rms_db"] - role_mean[ROLE[pi]]
    hi = (m["f0_cents"] - 5700.0) / 1200.0
    voic = int(round(base["voic"] + 2.2 * lvl_dev + 1.5 * hi))
    voic = max(100, min(128, voic))
    tenc = int(round(base["tenc"] + 1.2 * hi + 0.5 * lvl_dev))
    tenc = max(0, min(20, tenc))
    brec = int(round(base["brec"] - 0.6 * lvl_dev))
    brec = max(-24, min(12, brec))
    dyn = round(base["dyn"] + 0.35 * lvl_dev, 2)
    dyn = max(-6.0, min(12.0, dyn))
    # 句内逐字：靠前的字稍收，句尾字放开（承接下一句）
    xs, vs, ts, bs = [], [], [], []
    total = len([n for n in notes if n["lyric"] not in ("SP", "AP")])
    idx = 0
    for n in notes:
        if n["lyric"] in ("SP", "AP"):
            continue
        idx += 1
        pos = n["position"]
        dur = n["duration"]
        t_in = pos + int(dur * 0.18)
        t_mid = pos + int(dur * 0.45)
        t_out = pos + int(dur * 0.78)
        end = pos + dur
        frac = idx / max(1, total)
        # 句内渐强 + 字头支撑、字尾回收
        ramp = round(1.0 * frac, 2)
        v_local = int(round(voic + ramp - 1))
        xs.extend([pos, t_in, t_mid, t_out, end])
        vs.extend([v_local, v_local, v_local, max(100, v_local - 2), max(100, v_local - 4)])
        ts.extend([tenc, tenc, tenc, max(0, tenc - 2), max(0, tenc - 3)])
        bs.extend([brec, brec, brec, min(12, brec + 3), min(12, brec + 5)])
    curves = [{"abbr": "voic", "xs": xs, "ys": vs},
              {"abbr": "tenc", "xs": ts and xs, "ys": ts},
              {"abbr": "brec", "xs": xs, "ys": bs}]
    d_xs = [0, notes[0]["position"], notes[0]["position"] + 30,
            notes[-1]["position"] + notes[-1]["duration"] - 30, notes[-1]["position"] + notes[-1]["duration"]]
    curves.append({"abbr": "dyn", "xs": d_xs, "ys": [0, 0, int(dyn * 10), int(dyn * 10), 0]})
    vp["curves"] = curves
    metrics[pi]["voic"] = voic
    metrics[pi]["tenc"] = tenc
    metrics[pi]["brec"] = brec
    metrics[pi]["dyn"] = dyn

save_ustx(doc, SCORE)
score_hash = sha256(SCORE)
print(f"score.ustx updated with per-phrase phonation curves: {score_hash[:12]}")

# ---------------- STEP 2: 重导原生 pitch/phones + provenance ----------------
pitch_path = DESIGN / "baseline_pitch.json"
phones_path = DESIGN / "baseline_phones.json"
prov_path = DESIGN / "native_provenance.json"
rp = run_bridge(cfg, ["export-pitch", "--project", str(SCORE.resolve()), "--out", str(pitch_path.resolve())])
rph = run_bridge(cfg, ["export-phonemes", "--project", str(SCORE.resolve()), "--out", str(phones_path.resolve())])
assert rp.get("ok") and rph.get("ok")
ou = Path(cfg["openutau_dir"])
singer = doc["tracks"][0]["singer"]
prov = dict(schema_version=1, project_sha256=score_hash,
            pitch_sha256=sha256(pitch_path), phonemes_sha256=sha256(phones_path),
            environment=dict(core_sha256=sha256(ou / "OpenUtau.Core.dll"),
                             bridge_sha256=sha256(ou / "a2u-bridge.exe"),
                             singer_config_sha256=sha256(ou / "Singers" / singer / "dsconfig.yaml"),
                             singer_id=singer))
prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
print("native re-export ok:", rp.get("frame_count"), rph.get("phone_count"))

# ---------------- STEP 3: sources.json ----------------
def rel(p):
    return str(Path(p).resolve())


sources = dict(schema_version=1, sources=[
    dict(id="source_flac", role="source_observation", file=dict(path=r"E:\data\music\年轮 - 张碧晨.flac",
         sha256=rj(V2 / "observation" / "request.json")["source_sha256"]),
         description="Original input FLAC audio of 张碧晨《年轮》."),
    dict(id="source_wav", role="source_observation", file=dict(path=rel(V2 / "observation" / "source.wav"),
         sha256=rj(V2 / "observation" / "manifest.json")["files"]["source.wav"]),
         description="Decoded PCM WAV from the original FLAC."),
    dict(id="separated_vocal", role="source_observation",
         file=dict(path=rel(V2 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
                   sha256=rj(V2 / "observation" / "manifest.json")["files"]["stems\\source_(vocals)_vocals_mel_band_roformer.wav"]),
         description="Separated dry vocal stem from MelBand Roformer."),
    dict(id="separated_inst", role="source_observation",
         file=dict(path=rel(V2 / "observation" / "stems" / "source_(other)_vocals_mel_band_roformer.wav"),
                   sha256=rj(V2 / "observation" / "manifest.json")["files"]["stems\\source_(other)_vocals_mel_band_roformer.wav"]),
         description="Separated instrumental backing track stem."),
    dict(id="asr_obs", role="source_observation", file=dict(path=rel(V2 / "observation" / "asr.json"),
         sha256=rj(V2 / "observation" / "manifest.json")["files"]["asr.json"]),
         description="Whisper ASR transcription segments (phrase-level timing cross-check)."),
    dict(id="game_obs", role="source_observation", file=dict(path=rel(V2 / "observation" / "game.json"),
         sha256=rj(V2 / "observation" / "manifest.json")["files"]["game.json"]),
         description="GAME transcription note events (note grid for melisma splits)."),
    dict(id="fcpe_obs", role="source_observation", file=dict(path=rel(V2 / "observation" / "fcpe.npz"),
         sha256=rj(V2 / "observation" / "manifest.json")["files"]["fcpe.npz"]),
         description="FCPE frame-level pitch extraction (10ms)."),
    dict(id="rmvpe_obs", role="source_observation", file=dict(path=rel(V2 / "observation" / "rmvpe.npz"),
         sha256=rj(V2 / "observation" / "manifest.json")["files"]["rmvpe.npz"]),
         description="RMVPE frame-level pitch extraction (10ms, independent detector)."),
    dict(id="hfa_summary", role="source_observation", file=dict(path=rel(V2 / "hfa" / "hfa_summary.json"),
         sha256=sha256(V2 / "hfa" / "hfa_summary.json")),
         description="HubertFA forced alignment word/phone boundaries (identity and count only)."),
    dict(id="score_ustx", role="current_score", file=dict(path=rel(SCORE), sha256=score_hash),
         description="Agent-authored score with 51 phrases and per-phrase phonation curves."),
    dict(id="baseline_pitch", role="native_export", file=dict(path=rel(pitch_path), sha256=sha256(pitch_path)),
         description="Native pitch export of the current score (OpenUtau Core)."),
    dict(id="baseline_phones", role="native_export", file=dict(path=rel(phones_path), sha256=sha256(phones_path)),
         description="Native phoneme export of the current score."),
    dict(id="native_provenance", role="software", file=dict(path=rel(prov_path), sha256=sha256(prov_path)),
         description="Native environment and asset provenance receipt."),
])
(DESIGN / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf-8")
print("sources.json written")

# ---------------- STEP 4: inventory (raw) ----------------
raw_inv_path = Path("scratch/raw_inv_nianlun_v2.json")
raw_inv_path.unlink(missing_ok=True)
raw_inv = build_inventory(SCORE, raw_inv_path, pitch_path, phones_path, prov_path, None, DESIGN / "sources.json")
raw_units = {u["id"]: u for u in raw_inv["units"]}
print("raw inventory units:", len(raw_units))

# ---------------- STEP 5: context.json（每单元条件与阶段） ----------------
def unit_condition(u):
    a, b = u["support_s"]
    tr = src_track(a + 0.02, b - 0.02)
    if tr is None:
        return dict(status="observed", evidence_ids=["fcpe_obs", "rmvpe_obs", "hfa_summary"],
                    observation=f"Vowel {u.get('symbol')} spanning {a:.3f}s to {b:.3f}s",
                    interpretation="Source track unavailable in this window; keep the nominal level and hold.",
                    reliability="uncertain")
    tt, vv = tr
    span = float(vv.max() - vv.min())
    med = float(np.median(vv))
    return dict(status="observed", evidence_ids=["fcpe_obs", "rmvpe_obs", "game_obs", "hfa_summary"],
                observation=(f"Vowel {u.get('symbol')} ({u.get('lyric')}) {a:.3f}-{b:.3f}s; "
                             f"dual-detector median {med:.0f}c, in-window span {span:.0f}c, {len(vv)} frames"),
                interpretation=("Source shows an independent in-vowel shape (span>35c); keep the source's own contour"
                                if span > 35 else
                                "Source is essentially flat inside this vowel; hold the nominal level without a canned bump"),
                reliability="high")


ctx_units = []
for uid, u in raw_units.items():
    a, b = u["support_s"]
    ctx_units.append(dict(id=uid, condition=unit_condition(u),
                           stages=[dict(id=f"{uid}:body", kind="body",
                                        support_s=[round(a + 0.005, 6), round(b - 0.005, 6)], required=True)]))
ctx = dict(schema_version=1, units=ctx_units)
(DESIGN / "context.json").write_text(json.dumps(ctx, ensure_ascii=False, indent=1), encoding="utf-8")

inv_path = DESIGN / "review-inventory.json"
inv_path.unlink(missing_ok=True)
build_inventory(SCORE, inv_path, pitch_path, phones_path, prov_path, DESIGN / "context.json", DESIGN / "sources.json")
inv = validate_inventory(inv_path)
print("inventory units:", len(inv["units"]), "regions:", len(inv["regions"]))
json.dump(dict(metrics={str(k): v for k, v in metrics.items()}, role=ROLE),
          open(DESIGN / "phrase_metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("stage A done")
