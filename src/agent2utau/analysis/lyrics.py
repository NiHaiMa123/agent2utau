"""Lyric transcription via faster-whisper (CPU, int8).

Returns segments with per-char timing. Multi-character ASR words are split
evenly as an explicitly approximate fallback; supplied lyrics use acoustic
attention/DTW through force_align instead of onset-count heuristics.
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
_REPO_LYRICS = Path(__file__).resolve().parents[3] / "data" / "lyrics"


def find_lyrics(src_path: str | Path) -> tuple[Path, str] | None:
    """Discover reference lyrics for a source audio without --lyrics.

    Order: explicit sidecar, then an exact source SHA256 binding. A song
    title does not identify a recording/arrangement/timeline.
    """
    src = Path(src_path)
    sidecar = src.with_suffix(".lrc")
    if sidecar.exists():
        return sidecar, "sidecar"
    index = _REPO_LYRICS / "index.yaml"
    if index.exists():
        import yaml
        idx = yaml.safe_load(index.read_text(encoding="utf-8")) or {}
        import hashlib
        digest = None
        for entry in idx.get("recordings", []):
            if not isinstance(entry, dict) or not entry.get("sha256"):
                continue
            if digest is None:
                with src.open("rb") as f:
                    digest = hashlib.file_digest(f, "sha256").hexdigest()
            if entry["sha256"] == digest:
                p = _REPO_LYRICS / entry["file"]
                if p.exists():
                    return p, "source-sha256"
    return None


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


def force_align(wav_path: str | Path, text: str, t0: float, t1: float,
                model: str = DEFAULT_MODEL) -> list[dict]:
    """Align supplied text using Whisper's acoustic attention + DTW.

    This is a constrained alignment, NOT evidence that the supplied lyrics
    match this recording. Callers must bind references to the source audio.
    Probabilities and zero-duration tokens are retained for quality checks.
    The adapter targets the installed faster-whisper 1.x find_alignment API.
    """
    from faster_whisper.tokenizer import Tokenizer
    from faster_whisper.audio import pad_or_trim
    import librosa

    if not 0 < t1 - t0 <= 29:
        raise ValueError("Alignment windows must be in (0, 29] seconds")
    with sf.SoundFile(str(wav_path)) as audio:
        sr = audio.samplerate
        audio.seek(max(0, int(t0 * sr)))
        clip = audio.read(int((t1 - t0) * sr), dtype="float32")
    if clip.ndim > 1:
        clip = clip.mean(axis=1)
    recognizer = _model(model)
    target_sr = recognizer.feature_extractor.sampling_rate
    if sr != target_sr:
        clip = librosa.resample(clip, orig_sr=sr, target_sr=target_sr)
    features = recognizer.feature_extractor(clip)
    frames = min(features.shape[-1] - 1,
                 int(len(clip) / recognizer.feature_extractor.hop_length))
    encoded = recognizer.encode(pad_or_trim(features))
    tokenizer = Tokenizer(recognizer.hf_tokenizer,
                          recognizer.model.is_multilingual,
                          task="transcribe", language="zh")
    words = recognizer.find_alignment(
        tokenizer, [tokenizer.encode(text)], encoded, frames)[0]
    chars = []
    for word in words:
        for char in _char_spans(word["word"], word["start"], word["end"]):
            chars.append({**char, "start": round(t0 + char["start"], 4),
                          "end": round(t0 + char["end"], 4),
                          "probability": float(word["probability"]),
                          "method": "whisper-attention-dtw"})
    return chars
