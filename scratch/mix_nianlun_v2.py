"""年轮 v2：人声 + 伴奏混合 -> 试听切片。"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")
from agent2utau.audio.mix import mix

V2 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
RENDER = V2 / "render"
SCRATCH = Path(r"E:\project\agent2utau\scratch")

vocal = RENDER / "vocal_vocal.wav"
if not vocal.exists():
    vocal = RENDER / "vocal.wav"
accomp = V2 / "observation" / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
mix_path = RENDER / "nianlun_lingyuan_cover_mix_v2.wav"
vg, ag = 0.0, -4.0
while True:
    try:
        mix_res = mix(vocal, accomp, mix_path, vocal_gain_db=vg, accomp_gain_db=ag)
        if mix_res["peak"] <= 0.92:
            break
        vg = round(vg - 1.0, 2)
        ag = round(ag - 1.0, 2)
    except ValueError:
        vg = round(vg - 1.5, 2)
        ag = round(ag - 1.5, 2)
print("mix:", json.dumps(mix_res, ensure_ascii=False))

mix_audio, sr = sf.read(str(mix_path), dtype="float32")
voc_audio, _ = sf.read(str(vocal), dtype="float32")
if voc_audio.ndim > 1:
    voc_audio = voc_audio.mean(axis=1)
for name, a, b in [("verse1", 18.0, 35.0), ("chorus1", 70.0, 97.0),
                   ("chorus2", 157.0, 185.0), ("chorus3", 206.0, 243.0)]:
    sf.write(str(SCRATCH / f"nianlun_v2_{name}_vocal.wav"), voc_audio[int(a * sr):int(b * sr)], sr)
    sf.write(str(SCRATCH / f"nianlun_v2_{name}_mix.wav"), mix_audio[int(a * sr):int(b * sr)], sr)
    print("slice", name)
print("vocal rms %.1f dB" % (20 * np.log10(np.sqrt(np.mean(voc_audio ** 2)) + 1e-12)))
