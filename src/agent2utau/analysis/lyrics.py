"""Lyric transcription via faster-whisper (CPU, int8).

Returns segments with per-char timing. Multi-character ASR words are split
evenly as an approximate observation, not an accepted word/phonetic clock.
Use explicit lyric preparation and the current HFA model for alignment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

DEFAULT_MODEL = "large-v3-turbo"  # distilled; much faster than large-v3 on CPU
_HANZI = re.compile(r"[一-鿿]")
_MODEL = None


def _model(name: str):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(name, device="cpu", compute_type="int8")
    return _MODEL


def _is_hanzi(ch: str) -> bool:
    return bool(_HANZI.match(ch))


def _char_spans(text: str, t0: float, t1: float) -> list[dict]:
    """Split a whisper word/segment into Hanzi chars with even timing."""
    chars = [c for c in text if _is_hanzi(c)]
    if not chars:
        return []
    dur = (t1 - t0) / len(chars)
    return [{"char": c, "start": t0 + i * dur, "end": t0 + (i + 1) * dur}
            for i, c in enumerate(chars)]


def transcribe(wav_path: str | Path, model: str = DEFAULT_MODEL,
               t0: float = 0.0, t1: float | None = None,
               beam_size: int = 5) -> dict[str, Any]:
    """Transcribe [t0,t1] of a mono wav. Returns segments with char times."""
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    i0, i1 = int(t0 * sr), (int(t1 * sr) if t1 else len(wav))
    clip = wav[i0:i1]
    recognizer = _model(model)
    target_sr = recognizer.feature_extractor.sampling_rate
    # Arrays bypass faster-whisper's audio decoder/resampler entirely.
    if sr != target_sr:
        import librosa
        clip = librosa.resample(clip, orig_sr=sr, target_sr=target_sr)
    segs, _info = recognizer.transcribe(
        clip, language="zh", beam_size=beam_size,
        word_timestamps=True, vad_filter=False,
        condition_on_previous_text=False)
    out = []
    for s in segs:
        chars = []
        if s.words:
            for w in s.words:
                chars += _char_spans(w.word, w.start, w.end)
        else:
            chars = _char_spans(s.text, s.start, s.end)
        out.append({
            "start": round(t0 + s.start, 3), "end": round(t0 + s.end, 3),
            "text": s.text.strip(),
            "avg_logprob": round(s.avg_logprob, 4),
            "chars": [{**c, "start": round(t0 + c["start"], 3),
                       "end": round(t0 + c["end"], 3)} for c in chars],
        })
    return {
        "schema_version": "1",
        "backend": f"faster-whisper:{model}",
        "device": "cpu:int8",
        "n_segments": len(out),
        "segments": out,
    }
