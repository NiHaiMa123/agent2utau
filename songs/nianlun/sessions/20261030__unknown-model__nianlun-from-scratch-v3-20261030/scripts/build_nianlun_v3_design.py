"""年轮 v3 设计阶段（阶段 B）：逐单元条件 + 源清单 + 复检库存。

与 v2 的差别：条件描述里给出"该单元在源里的实测跨度/涟漪"，供下游画线与判据使用；
库存来自 v3 自己的原生 pitch/phones（音素对齐已生效）。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))

from agent2utau.openutau.ustx import load_ustx, sha256
from agent2utau.evaluation.execution_review import build_inventory, validate_inventory
from nianlun_v3_source import Source

V2 = ROOT / "runs" / "production" / "nianlun-from-scratch-v2-20261028"
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
SCORE = DESIGN / "score.ustx"
TICK_S = 60.0 / (120.0 * 480)

src = Source(V3)
doc = load_ustx(SCORE)
feat = json.loads((DESIGN / "note_features.json").read_text(encoding="utf-8"))["notes"]


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------------- 源清单 ----------------
def rel(p):
    return str(Path(p).resolve())


manifest = rj(V3 / "observation" / "manifest.json")
sources = dict(schema_version=1, sources=[
    dict(id="source_flac", role="source_observation",
         file=dict(path=r"E:\data\music\年轮 - 张碧晨.flac",
                   sha256=rj(V3 / "observation" / "request.json")["source_sha256"]),
         description="Original input FLAC audio of 张碧晨《年轮》."),
    dict(id="source_wav", role="source_observation",
         file=dict(path=rel(V3 / "observation" / "source.wav"),
                   sha256=manifest["files"]["source.wav"]),
         description="Decoded PCM WAV from the original FLAC."),
    dict(id="separated_vocal", role="source_observation",
         file=dict(path=rel(V3 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
                   sha256=manifest["files"]["stems\\source_(vocals)_vocals_mel_band_roformer.wav"]),
         description="Separated dry vocal stem from MelBand Roformer (原唱人声干声)."),
    dict(id="separated_inst", role="source_observation",
         file=dict(path=rel(V3 / "observation" / "stems" / "source_(other)_vocals_mel_band_roformer.wav"),
                   sha256=manifest["files"]["stems\\source_(other)_vocals_mel_band_roformer.wav"]),
         description="Separated instrumental backing stem."),
    dict(id="asr_obs", role="source_observation", file=dict(path=rel(V3 / "observation" / "asr.json"),
         sha256=manifest["files"]["asr.json"]), description="Whisper ASR transcription (phrase timing cross-check)."),
    dict(id="game_obs", role="source_observation", file=dict(path=rel(V3 / "observation" / "game.json"),
         sha256=manifest["files"]["game.json"]), description="GAME note events (melisma split reference)."),
    dict(id="fcpe_obs", role="source_observation", file=dict(path=rel(V3 / "observation" / "fcpe.npz"),
         sha256=manifest["files"]["fcpe.npz"]), description="FCPE frame-level pitch (10ms)."),
    dict(id="rmvpe_obs", role="source_observation", file=dict(path=rel(V3 / "observation" / "rmvpe.npz"),
         sha256=manifest["files"]["rmvpe.npz"]), description="RMVPE frame-level pitch (10ms, independent detector)."),
    dict(id="hfa_summary", role="source_observation", file=dict(path=rel(V3 / "hfa" / "hfa_summary.json"),
         sha256=sha256(V3 / "hfa" / "hfa_summary.json")),
         description="HubertFA forced alignment word/phone boundaries (identity and count only)."),
    dict(id="score_ustx", role="current_score", file=dict(path=rel(SCORE), sha256=sha256(SCORE)),
         description="v3 谱面：继承 v2 音符栅格 + 逐音符 VOIC/BREC/TENC/DYN + 音素对齐 override。"),
    dict(id="baseline_pitch", role="native_export",
         file=dict(path=rel(DESIGN / "baseline_pitch.json"), sha256=sha256(DESIGN / "baseline_pitch.json")),
         description="Native pitch export of the v3 score (OpenUtau Core)."),
    dict(id="baseline_phones", role="native_export",
         file=dict(path=rel(DESIGN / "baseline_phones.json"), sha256=sha256(DESIGN / "baseline_phones.json")),
         description="Native phoneme export of the v3 score (音素对齐已应用)."),
    dict(id="native_provenance", role="software",
         file=dict(path=rel(DESIGN / "native_provenance.json"), sha256=sha256(DESIGN / "native_provenance.json")),
         description="Native environment and asset provenance receipt."),
    dict(id="note_features", role="current_score",
         file=dict(path=rel(DESIGN / "note_features.json"), sha256=sha256(DESIGN / "note_features.json")),
         description="v3 逐音符源实测（RMS/HNR/亮度/音高/涟漪频率幅度相位/发声取值）."),
])
(DESIGN / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf-8")
print("sources.json written")

# ---------------- 逐单元条件 ----------------
raw_inv_path = ROOT / "scratch" / "raw_inv_nianlun_v3.json"
raw_inv_path.unlink(missing_ok=True)
raw_inv = build_inventory(SCORE, raw_inv_path, DESIGN / "baseline_pitch.json", DESIGN / "baseline_phones.json",
                          DESIGN / "native_provenance.json", None, DESIGN / "sources.json")
raw_units = {u["id"]: u for u in raw_inv["units"]}
print("raw units", len(raw_units))

feat_by_note = {(f["part_index"], f["note_index"]): f for f in feat}


def unit_condition(u):
    a, b = u["support_s"]
    tr = src.track(a + 0.005, b - 0.005)
    notes = [n for n in u["musical_stages"]]
    f_list = []
    for n in notes:
        pi, ni = u["part_index"], int(n["note_id"].split(":n")[1])
        f = feat_by_note.get((pi, ni))
        if f:
            f_list.append(f)
    rip = [f["ripple"]["amp"] for f in f_list if f["ripple"]]
    if tr is None:
        return dict(status="observed", evidence_ids=["fcpe_obs", "rmvpe_obs", "hfa_summary"],
                    observation=(f"Vowel {u.get('symbol')} ({u.get('lyric')}) {a:.3f}-{b:.3f}s；"
                                 f"源在该窗口无一致 F0（双检测器不足），按名义音高保持"),
                    interpretation="源证据不足：不虚构字腹运动，按名义音高保持",
                    reliability="uncertain")
    tt, vv = tr
    span = float(vv.max() - vv.min())
    med = float(np.median(vv))
    rip_txt = f"，涟漪幅度 {max(rip):.0f}c" if rip else ""
    return dict(status="observed", evidence_ids=["fcpe_obs", "rmvpe_obs", "game_obs", "hfa_summary"],
                observation=(f"Vowel {u.get('symbol')} ({u.get('lyric')}) {a:.3f}-{b:.3f}s; "
                             f"dual-detector median {med:.0f}c, in-window span {span:.0f}c, {len(vv)} frames"
                             + rip_txt),
                interpretation=("源在该元音内有独立走向（span>35c）且带涟漪：照源画，不套模板"
                                if span > 35 else
                                "源在该元音内基本平直：保持贴合源线，不加与源无关的鼓包"),
                reliability="high" if len(vv) >= 6 else "uncertain")


ctx_units = []
for uid, u in raw_units.items():
    a, b = u["support_s"]
    ctx_units.append(dict(id=uid, condition=unit_condition(u),
                           stages=[dict(id=f"{uid}:body", kind="body",
                                        support_s=[round(a + 0.005, 6), round(b - 0.005, 6)], required=True)]))
(DESIGN / "context.json").write_text(json.dumps(dict(schema_version=1, units=ctx_units),
                                                ensure_ascii=False, indent=1), encoding="utf-8")

inv_path = DESIGN / "review-inventory.json"
inv_path.unlink(missing_ok=True)
build_inventory(SCORE, inv_path, DESIGN / "baseline_pitch.json", DESIGN / "baseline_phones.json",
                DESIGN / "native_provenance.json", DESIGN / "context.json", DESIGN / "sources.json")
inv = validate_inventory(inv_path)
print("inventory units", len(inv["units"]), "regions", len(inv["regions"]),
      "unknown regions", sum(1 for r in inv["regions"] if r["region_type"] == "unknown"))

# ---------------- 句级汇总 ----------------
metrics = {}
for pi in range(len(doc["voice_parts"])):
    part = doc["voice_parts"][pi]
    base = part["position"] * TICK_S
    notes = part["notes"]
    a = base + notes[0]["position"] * TICK_S
    b = base + (notes[-1]["position"] + notes[-1]["duration"]) * TICK_S
    fs = [f for f in feat if f["part_index"] == pi]
    rms = [f["rms_db"] for f in fs if f["rms_db"] is not None]
    hnr = [f["hnr_db"] for f in fs if f["hnr_db"] is not None]
    spans = [f["src_span"] for f in fs]
    rip = [f["ripple"]["amp"] for f in fs if f["ripple"]]
    metrics[str(pi)] = dict(
        start_s=round(a, 3), end_s=round(b, 3), notes=len(fs),
        rms_db=round(float(np.mean(rms)), 2) if rms else None,
        rms_spread_db=round(float(np.std(rms)), 2) if rms else None,
        hnr_db=round(float(np.mean(hnr)), 2) if hnr else None,
        src_span_median_c=round(float(np.median(spans)), 1) if spans else None,
        src_span_max_c=round(float(np.max(spans)), 1) if spans else None,
        ripple_notes=len(rip),
        ripple_amp_median_c=round(float(np.median(rip)), 1) if rip else None,
        voic=int(np.median([f["voic"] for f in fs])) if fs else None,
        brec=int(np.median([f["brec"] for f in fs])) if fs else None,
        tenc=int(np.median([f["tenc"] for f in fs])) if fs else None,
        dyn=round(float(np.median([f["dyn"] for f in fs])), 2) if fs else None)
(DESIGN / "phrase_metrics.json").write_text(json.dumps(dict(metrics=metrics), ensure_ascii=False, indent=1),
                                             encoding="utf-8")
print("phrase metrics written")
