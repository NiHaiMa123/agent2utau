"""年轮 v2：渲染人声 -> 与伴奏混合 -> 试听切片 -> 带证据的复检。"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")

from agent2utau.audio.mix import mix

V2 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
DESIGN = V2 / "design"
COMPILED = V2 / "compiled"
RENDER = V2 / "render"
OBS = V2 / "observation"
SCRATCH = Path(r"E:\project\agent2utau\scratch")
RENDER.mkdir(parents=True, exist_ok=True)

project = COMPILED / "project.ustx"
vocal = RENDER / "vocal.wav"
print("rendering vocal ...")
import subprocess
py = r"E:\project\agent2utau\.venv\Scripts\python.exe"
res = subprocess.run([py, "-m", "agent2utau.cli", "render-project", "--project", str(project),
                      "--out", str(vocal)], capture_output=True, text=True)
print(res.stdout[-800:] if res.stdout else "")
if res.returncode != 0:
    print("RENDER FAILED:", res.stderr[-2000:])
    raise SystemExit(1)
vocal_vocal = RENDER / "vocal_vocal.wav"
if not vocal_vocal.exists():
    vocal_vocal = vocal
print("vocal:", vocal_vocal, vocal_vocal.exists())

accomp = OBS / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
mix_path = RENDER / "nianlun_lingyuan_cover_mix_v2.wav"
vg, ag = 0.0, -4.0
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
slices = [("verse1", 18.0, 35.0), ("chorus1", 70.0, 97.0), ("chorus2", 157.0, 185.0), ("chorus3", 206.0, 243.0)]
for name, a, b in slices:
    sf.write(str(SCRATCH / f"nianlun_v2_{name}_vocal.wav"), voc_audio[int(a * sr):int(b * sr)], sr)
    sf.write(str(SCRATCH / f"nianlun_v2_{name}_mix.wav"), mix_audio[int(a * sr):int(b * sr)], sr)
    print("slice", name, round(b - a, 1), "s")

# 带证据的复检（ledger/plan/intent-lock 全绑定）
out = RENDER / "execution-review"
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True, exist_ok=True)
cmd = [py, "-m", "agent2utau.cli", "review-execution",
       "--project", str(project),
       "--inventory", str(COMPILED / "review-inventory.json"),
       "--out", str(out),
       "--native-pitch", str(COMPILED / "pitch.json"),
       "--phonemes", str(COMPILED / "phones.json"),
       "--provenance", str(COMPILED / "native_provenance.json"),
       "--ledger", str(DESIGN / "ledger.json"),
       "--plan", str(DESIGN / "plan.json"),
       "--intent-lock", str(DESIGN / "intent_lock.json")]
r = subprocess.run(cmd, capture_output=True, text=True)
print("review-execution rc:", r.returncode)
print((r.stdout or "")[-1500:])
if r.returncode != 0:
    print("REVIEW STDERR:", (r.stderr or "")[-1500:])
rv = out / "review.json"
if rv.exists():
    data = json.loads(rv.read_text(encoding="utf-8"))
    print("--- review summary ---")
    for k in ("technical_execution_complete", "workflow_review_complete", "production_execution_complete"):
        print(" ", k, "=", data.get(k))
    print("  inventory_coverage:", json.dumps(data.get("inventory_coverage"), ensure_ascii=False)[:400])
    print("  action_execution:", json.dumps(data.get("action_execution"), ensure_ascii=False)[:300])
    print("  musical_review:", json.dumps(data.get("musical_review"), ensure_ascii=False)[:500])
    print("  local_visual_review:", json.dumps(data.get("local_visual_review"), ensure_ascii=False)[:300])
