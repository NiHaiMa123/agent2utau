"""年轮功能版 09-29: 用泠鸢 dspitch 官方音高预测生成自动音高并渲染。

严格按 OpenUtau 官方语义 (已用最后一页验证):
  NoteBatchEdits.cs:607  x = phrase.position - part.position + result.ticks[i]
  NoteBatchEdits.cs:615  pitchIndex = (x - (phrase.position - part.position - leading)) / 5
  NoteBatchEdits.cs:616  basePitch = phrase.pitchesBeforeDeviation[pitchIndex]
  NoteBatchEdits.cs:617  y = (int)(result.tones[i] * 100 - basePitch)

输入:
  nianlun_func_autopitch.json  = 官方 LoadRenderedPitch 输出 (ticks + tones)
  nianlun_func_pitch.json      = 工程基准线 (before_pitd_cents, 5-tick 网格)
输出:
  scratch/nianlun_func_dspitch/  工程副本 + 渲染音频 + mp3
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
SRC = REPO / "runs" / "nianlun_functional_20260929"
PROJECT = SRC / "nianlun_functional.ustx"
ACCOMP = SRC / "accompaniment.wav"
OUTDIR = REPO / "scratch" / "nianlun_func_dspitch"
PY = REPO / ".venv" / "Scripts" / "python.exe"

OFF = REPO / "scratch" / "nianlun_func_autopitch.json"
PITCH = REPO / "scratch" / "nianlun_func_pitch.json"
PHONES = REPO / "scratch" / "nianlun_func_phones.json"


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    off = json.loads(OFF.read_text(encoding="utf-8"))
    pc = json.loads(PITCH.read_text(encoding="utf-8"))
    ph_doc = json.loads(PHONES.read_text(encoding="utf-8"))

    print("== 1. 生成 PITD (官方公式) ==")
    dst = OUTDIR / "nianlun_functional_dspitch.ustx"
    shutil.copy2(PROJECT, dst)
    proj = yaml.safe_load(dst.read_text(encoding="utf-8"))

    total = 0
    for pi, part in enumerate(proj["voice_parts"]):
        pos = part["position"]
        # 每个 phrase 有**自己的** base 数组 (phrase 之间有 gap, 不能拼接!)
        base_by_pos = {b["position"]: np.asarray(b["before_pitd_cents"], dtype=np.float64)
                       for b in pc["phrases"] if b["part_position"] == pos}

        cand = [p for p in off["phrases"] if p["part_position"] == pos]
        xs, ys = [], []
        for o in cand:
            o_pos = o["position"]
            base = base_by_pos.get(o_pos)
            if base is None or len(base) == 0:
                continue
            # 官方公式 (NoteBatchEdits.cs:615-617):
            #   x = phrase.position - part.position + ticks[i]
            #   pitchIndex = (x - (phrase.position - part.position - leading)) / 5
            #              = (ticks[i] + leading) / 5
            #   y = tones[i]*100 - base[pitchIndex]
            leading = 0
            for t, tone in zip(o["ticks"], o["tones"]):
                x = int(round(o_pos - pos + t))
                pidx = int((t + leading) // 5)
                pidx = max(0, min(len(base) - 1, pidx))
                y = int(round(tone * 100.0 - base[pidx]))
                xs.append(x)
                ys.append(max(-1200, min(1200, y)))
        pairs = sorted(dict(zip(xs, ys)).items())
        curves = [c for c in part.get("curves", []) if c.get("abbr") != "pitd"]
        curves.append({"abbr": "pitd", "xs": [p[0] for p in pairs], "ys": [p[1] for p in pairs]})
        part["curves"] = curves
        total += len(pairs)
    dst.write_text(yaml.safe_dump(proj, allow_unicode=True, sort_keys=False,
                                  default_flow_style=False, width=10_000), encoding="utf-8")
    print(f"   写入点: {total}")

    print("== 2. 渲染 ==")
    res = subprocess.run([str(PY), "-m", "agent2utau.cli", "render-project",
                          "--project", str(dst), "--out", str(OUTDIR / "vocal.wav")],
                         capture_output=True, text=True, cwd=str(REPO))
    if res.returncode != 0:
        print(res.stdout[-1500:]); print(res.stderr[-2500:])
        raise SystemExit("render failed")
    actual = OUTDIR / "vocal_vocal.wav"
    if not actual.exists():
        actual = list(OUTDIR.glob("*.wav"))[0]
    print(f"   产物: {actual}")

    print("== 3. 混伴奏 + 切片 + mp3 ==")
    from agent2utau.audio.mix import mix
    mix_path = OUTDIR / "nianlun_func_dspitch_mix.wav"
    # 原版 (09-29) 用 vocal +12.644dB / accomp 0dB + master -3.921dB
    # mix() 不接受 master gain, 需自己降到不削波: 保持人声/伴奏相对关系
    vg, ag = 12.644 - 3.921, 0.0 - 3.921
    while True:
        try:
            r = mix(actual, ACCOMP, mix_path, vocal_gain_db=vg, accomp_gain_db=ag)
            break
        except ValueError:
            vg = round(vg - 1.0, 2)
            ag = round(ag - 1.0, 2)
    print("   mix:", json.dumps(r, ensure_ascii=False))

    mix_a, sr = sf.read(str(mix_path), dtype="float32")
    voc_a, _ = sf.read(str(actual), dtype="float32")
    if voc_a.ndim > 1:
        voc_a = voc_a.mean(axis=1)
    # 与 09-29 版的 source_support 段落对齐: 副歌在 30s+, 尾段 200s+
    slices = {"head_18_60s": (18.0, 60.0), "chorus_100_135s": (100.0, 135.0),
              "chorus3_200_243s": (200.0, 243.0)}
    for name, (a, b) in slices.items():
        sf.write(str(OUTDIR / f"dspitch_{name}_mix.wav"), mix_a[int(a * sr):int(b * sr)], sr)
        sf.write(str(OUTDIR / f"dspitch_{name}_vocal.wav"), voc_a[int(a * sr):int(b * sr)], sr)
    for f in ["nianlun_func_dspitch_mix.wav"] + [f"dspitch_{n}_mix.wav" for n in slices] \
            + [f"dspitch_{n}_vocal.wav" for n in slices]:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(OUTDIR / f),
                        "-codec:a", "libmp3lame", "-q:a", "2",
                        str(OUTDIR / f.replace(".wav", ".mp3"))], check=True)
    print("   mp3 完成")

    print("== 4. 校验: 渲染读回的 final 是否等于官方 tones ==")
    out2 = OUTDIR / "pitch_check.json"
    subprocess.run([str(PY), "-m", "agent2utau.cli", "export-pitch",
                    "--project", str(dst), "--out", str(out2)],
                   capture_output=True, text=True, cwd=str(REPO))
    pc2 = json.loads(out2.read_text(encoding="utf-8"))
    # 抽查第一个 phrase
    b = pc2["phrases"][0]
    o = [p for p in off["phrases"] if p["position"] == b["position"]][0]
    TICK_MS = 60000.0 / (120.0 * 480.0)
    ph_start = b["times_ms"][0] / 1000.0
    o_ms = ph_start + np.asarray(o["ticks"]) * TICK_MS
    o_c = np.asarray(o["tones"]) * 100.0
    f_t = np.asarray(b["times_ms"]) / 1000.0
    f_c = np.asarray(b["final_cents"])
    o_at = np.interp(f_t, o_ms, o_c)
    d = np.abs(f_c - o_at)
    d = d[np.isfinite(d)]
    print(f"   phrase0: 中位 {np.median(d):.1f}c  p95 {np.percentile(d,95):.1f}c  "
          f"max {d.max():.1f}c  (n={len(d)})")

    # 全曲 final 跳变
    allc = []
    for p in pc2["phrases"]:
        allc.extend(p["final_cents"])
    c = np.asarray(allc)
    dd = np.abs(np.diff(c))
    print(f"   全曲 final 跳变: 中位 {np.median(dd):.0f}c  p99 {np.percentile(dd,99):.0f}c  "
          f"max {dd.max():.0f}c  >100c: {(dd>100).sum()}")

    print("== 5. 与原唱 F0 接近度 ==")
    sys.path.insert(0, str(REPO / "src"))
    from agent2utau.analysis.f0 import extract_f0
    orig = REPO / "runs" / "m2-nianlun" / "audio" / "original_(Vocals)_UVR-MDX-NET-Voc_FT.wav"
    if orig.exists():
        r = extract_f0(orig)
        co = np.where(r["f0_hz"] > 50.0,
                      6900.0 + 1200.0 * np.log2(np.maximum(r["f0_hz"], 1e-6) / 440.0), np.nan)
        ro = extract_f0(actual)
        cv = np.where(ro["f0_hz"] > 50.0,
                      6900.0 + 1200.0 * np.log2(np.maximum(ro["f0_hz"], 1e-6) / 440.0), np.nan)
        g = r["times"][(r["times"] > 18) & (r["times"] < 242)][::37]
        oi = np.interp(g, r["times"], co)
        vi = np.interp(g, ro["times"], cv)
        m = np.isfinite(oi) & np.isfinite(vi)
        print(f"   dspitch版 vs 原唱: 中位 |Δ| = {np.nanmedian(np.abs(vi[m]-oi[m])):.1f} cents")


if __name__ == "__main__":
    main()
