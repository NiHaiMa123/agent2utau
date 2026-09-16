"""Decode arbitrary audio to WAV preserving the original timeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

SAMPLE_RATE = 44100


def decode(src: str | Path, out_wav: Path, mono: bool = False,
           sample_rate: int = SAMPLE_RATE) -> Path:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
           "-ar", str(sample_rate), "-ac", "1" if mono else "2",
           "-c:a", "pcm_s16le", str(out_wav)]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {p.stderr.strip()}")
    return out_wav


def probe_duration(path: str | Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {p.stderr.strip()}")
    return float(p.stdout.strip())
