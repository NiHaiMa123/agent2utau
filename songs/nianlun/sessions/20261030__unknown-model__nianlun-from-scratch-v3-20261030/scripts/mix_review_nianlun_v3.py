"""年轮 v3：混音 -> 试听切片 -> 带证据的复检（ledger/plan/intent-lock 全绑定）。"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
COMPILED = V3 / "compiled"
RENDER = V3 / "render"
OBS = V3 / "observation"
SCRATCH = ROOT / "scratch"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
sys.path.insert(0, str(ROOT / "src"))
from agent2utau.audio.mix import mix

RENDER.mkdir(parents=True, exist_ok=True)
vocal_vocal = RENDER / "vocal_vocal.wav"
if not vocal_vocal.exists():
    vocal_vocal = RENDER / "vocal.wav"

accomp = OBS / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
mix_path = RENDER / "nianlun_lingyuan_cover_mix_v3.wav"
# 人声/伴奏比例对齐原唱：原唱干声 -19.19dB vs 原伴奏 -17.88dB（相对 -1.31dB），
# 成品人声 -24.03dB；伴奏 -4dB 时混音里的比例是 -2.15dB，故人声补 +0.8dB。
vg, ag = 0.8, -4.0
while True:
    try:
        mix_res = mix(vocal_vocal, accomp, mix_path, vocal_gain_db=vg, accomp_gain_db=ag)
        if mix_res["peak"] <= 0.92:
            break
        vg = round(vg - 1.0, 2)
        ag = round(ag - 1.0, 2)
    except ValueError:
        vg = round(vg - 1.5, 2)
        ag = round(ag - 1.5, 2)
print("mix:", json.dumps(mix_res, ensure_ascii=False))

mix_audio, sr = sf.read(str(mix_path), dtype="float32")
voc_audio, _ = sf.read(str(vocal_vocal), dtype="float32")
if voc_audio.ndim > 1:
    voc_audio = voc_audio.mean(axis=1)
slices = [("verse1", 18.0, 35.0), ("chorus1", 70.0, 97.0),
          ("chorus2", 157.0, 185.0), ("chorus3", 206.0, 243.0)]
for name, a, b in slices:
    sf.write(str(SCRATCH / f"nianlun_v3_{name}_vocal.wav"), voc_audio[int(a * sr):int(b * sr)], sr)
    sf.write(str(SCRATCH / f"nianlun_v3_{name}_mix.wav"), mix_audio[int(a * sr):int(b * sr)], sr)
    print("slice", name, round(b - a, 1), "s")

out = RENDER / "execution-review"
if out.exists():
    shutil.rmtree(out)
# review_execution 自己要求输出目录不存在，所以这里不要预先创建
cmd = [PY, "-m", "agent2utau.cli", "review-execution",
       "--project", str(COMPILED / "project.ustx"),
       "--inventory", str(DESIGN / "review-inventory.json"),
       "--out", str(out),
       "--native-pitch", str(COMPILED / "pitch.json"),
       "--phonemes", str(COMPILED / "phones.json"),
       "--provenance", str(COMPILED / "native_provenance.json"),
       "--ledger", str(DESIGN / "ledger.json"),
       "--plan", str(DESIGN / "plan.json"),
       "--intent-lock", str(DESIGN / "intent_lock.json"),
       "--reviews", str(DESIGN / "review_records.json"),
       "--musical-critique", str(DESIGN / "musical_critique.json")]
r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
print("review-execution rc:", r.returncode)
if r.returncode != 0:
    print("STDERR:", (r.stderr or "")[-2000:])
rv = out / "review.json"
if rv.exists():
    data = json.loads(rv.read_text(encoding="utf-8"))
    print("--- review summary ---")
    for k in ("technical_execution_complete", "workflow_review_complete", "production_execution_complete"):
        print(" ", k, "=", data.get(k))
    ic = data.get("inventory_coverage", {})
    print("  inventory_coverage:", ic.get("status"), "failures:", len(ic.get("failures", [])))
    for f in ic.get("failures", [])[:8]:
        print("     ", json.dumps(f, ensure_ascii=False)[:200])
    ae = data.get("action_execution", {})
    print("  action_execution:", ae.get("status"), "checks:", len(ae.get("checks", [])))
    from collections import Counter
    print("     by status:", Counter(c.get("status") for c in ae.get("checks", [])))
    mr = data.get("musical_review", {})
    print("  musical_review:", mr.get("status"), "intent:", mr.get("intent_execution"),
          "discrimination:", mr.get("discrimination"))
    print("     failed gestures:", len(mr.get("failed_gestures", [])),
          "nondiscriminating:", len(mr.get("nondiscriminating_gestures", [])))
    lvr = data.get("local_visual_review", {})
    print("  local_visual_review:", lvr.get("status"), lvr.get("completed"), "/", lvr.get("denominator"))
    print("  choice_review:", data.get("choice_review", {}).get("status"))
