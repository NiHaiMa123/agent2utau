"""GAME (Generative Adaptive MIDI Extractor) via the OpenUtau ONNX package.

Direct Python port of OpenUtau.Core/Analysis/GameOnnxBackend.cs running the
official openvpi oudep models (encoder → segmenter D3PM loop → bd2dur →
estimator). Unlike the bundled OpenUtau path, this port exposes the
segmenter's `known_boundaries` input so supplied lyric/char boundaries can
condition decoding (diagnostic Variant C).

Models: <OpenUtau>/Dependencies/game/{encoder,segmenter,bd2dur,estimator}.onnx
config.json: samplerate 44100, timestep 0.01s, languages {en:1,ja:2,yue:3,zh:4}
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .slicer import slice_audio

TIMESTEP = 0.01  # seconds per frame at the model's frame axis


class GameOnnx:
    def __init__(self, model_dir: str | Path, providers=None):
        import onnxruntime as ort
        d = Path(model_dir)
        self.config = json.loads((d / "config.json").read_text(
            encoding="utf-8"))
        providers = providers or ["CPUExecutionProvider"]
        self.sr = int(self.config.get("samplerate", 44100))
        self.languages = self.config.get("languages") or {}
        self.loop = bool(self.config.get("loop", True))
        self.sessions = {
            name: ort.InferenceSession(str(d / f"{name}.onnx"),
                                       providers=providers)
            for name in ("encoder", "segmenter", "bd2dur", "estimator")}

    def _lang_id(self, code: str | None) -> np.ndarray | None:
        if not self.languages:
            return None
        return np.array([self.languages.get(code, 0)], dtype=np.int64)

    def infer_chunk(self, wav: np.ndarray, *, language: str | None = None,
                    nsteps: int = 8, seg_threshold: float = 0.2,
                    radius: int = 2, est_threshold: float = 0.2,
                    known_boundary_frames: np.ndarray | None = None,
                    seed: int | None = None) -> list[dict]:
        """wav: mono float32 at self.sr. Returns sequential notes
        [{'start','dur','tone','voiced'}] with start/dur in seconds,
        covering the whole chunk (rests included)."""
        rng = np.random.default_rng(seed)
        wav = np.asarray(wav, dtype=np.float32)[None, :]
        dur = np.array([wav.shape[1] / self.sr], dtype=np.float32)
        enc = self.sessions["encoder"]
        out = enc.run(None, {"waveform": wav, "duration": dur})
        names = [o.name for o in enc.get_outputs()]
        x_seg, x_est, mask_t = (out[names.index(n)]
                                for n in ("x_seg", "x_est", "maskT"))
        T = x_seg.shape[1]
        known = np.zeros((1, T), dtype=bool)
        if known_boundary_frames is not None:
            idx = known_boundary_frames.astype(int)
            known[0, idx[(idx >= 0) & (idx < T)]] = True
        # official GAME d3pm init: boundaries start at known_boundaries
        # (openvpi/GAME me_infer.py), NOT zeros — matters when known≠∅
        boundaries = known.copy()
        lang = self._lang_id(language)
        lang_in = {} if lang is None else {"language": lang}
        thr = np.array(seg_threshold, dtype=np.float32)
        rad = np.array(radius, dtype=np.int64)
        seg = self.sessions["segmenter"]
        steps = nsteps if self.loop else 1
        for i in range(steps):
            t = np.array([i / nsteps], dtype=np.float32)
            inputs = {"x_seg": x_seg, "known_boundaries": known,
                      "maskT": mask_t, "threshold": thr, "radius": rad,
                      **lang_in}
            if self.loop:
                inputs["prev_boundaries"] = boundaries
                inputs["t"] = t
            boundaries = seg.run(None, inputs)[0]
        bd = self.sessions["bd2dur"]
        durations, mask_n = bd.run(
            None, {"boundaries": boundaries, "maskT": mask_t})
        est = self.sessions["estimator"]
        presence, scores = est.run(None, {
            "x_est": x_est, "boundaries": boundaries, "maskT": mask_t,
            "maskN": mask_n,
            "threshold": np.array(est_threshold, dtype=np.float32)})
        notes, t = [], 0.0
        for i in range(durations.shape[1]):
            if not mask_n[0, i]:
                break
            d = float(durations[0, i])
            notes.append({"start": t, "dur": d, "tone": float(scores[0, i]),
                          "voiced": bool(presence[0, i])})
            t += d
        return notes

    def infer(self, wav: np.ndarray, *, chunk: bool = True, **kw
              ) -> list[dict]:
        """Slice on silence (OpenUtau AudioSlicer port) and infer per chunk.
        known_boundary_sec kwarg accepts absolute seconds; they are mapped to
        per-chunk relative frames."""
        known_abs = kw.pop("known_boundary_sec", None)
        notes = []
        chunks = slice_audio(wav) if chunk else [(0.0, wav)]
        for off_ms, c in chunks:
            kb = None
            if known_abs is not None:
                rel = np.asarray(known_abs) - off_ms / 1000.0
                kb = np.round(rel / TIMESTEP).astype(int)
            for n in self.infer_chunk(c, known_boundary_frames=kb, **kw):
                n = dict(n)
                n["start"] += off_ms / 1000.0
                notes.append(n)
        return notes


def default_model_dir() -> Path:
    import os
    for root in (os.environ.get("OPENUTAU_DIR"),
                 r"E:\software\OpenUtau-win-x64 (6)"):
        if root:
            p = Path(root) / "Dependencies" / "game"
            if (p / "encoder.onnx").exists():
                return p
    raise FileNotFoundError("GAME onnx package not installed")
