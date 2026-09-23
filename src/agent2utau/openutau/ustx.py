"""USTX (YAML) load/save and tempo-map helpers.

The OpenUtau app itself performs version migration (0.7/0.9 -> current) on
load; this module only does structural edits and keeps field order for
diffability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def load_ustx(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"not a ustx yaml document: {path}")
    return doc


def save_ustx(doc: dict[str, Any], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False, width=10_000)


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def semantic_notes_sha256(doc: dict[str, Any],
                          part_name: str = "vocal_pipeline") -> str:
    """Semantic-score hash: canonical (position, duration, tone, lyric)
    per note plus the part anchor — file-format independent.

    This is the upstream written-score identity bound by manifests; it
    ignores expression content (pitch data, vibrato, curves) and YAML
    serialization details, so it changes exactly when the semantic
    score changes.
    """
    part = next(p for p in doc["voice_parts"] if p["name"] == part_name)
    sem = {"part": part_name, "part_position": int(part["position"]),
           "notes": [{"position": int(n["position"]),
                      "duration": int(n["duration"]),
                      "tone": int(n["tone"]),
                      "lyric": str(n["lyric"])}
                     for n in part["notes"]]}
    blob = json.dumps(sem, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class TempoMap:
    """Tick<->milliseconds using the project tempo list (position,bpm)."""

    def __init__(self, tempos: list[dict], resolution: int):
        self.resolution = resolution
        pts = sorted(((int(t["position"]), float(t["bpm"])) for t in tempos),
                     key=lambda t: t[0])
        if not pts or pts[0][0] > 0:
            pts.insert(0, (0, 120.0))
        self._pts = pts  # [(tick, bpm)]
        # cumulative ms at each boundary
        self._ms = [0.0]
        for i in range(1, len(pts)):
            dt = pts[i][0] - pts[i - 1][0]
            self._ms.append(self._ms[-1] + dt * 60000.0 / (pts[i - 1][1] * resolution))

    def tick_to_ms(self, tick: float) -> float:
        pts, ms = self._pts, self._ms
        if tick <= pts[0][0]:
            return ms[0] + (tick - pts[0][0]) * 60000.0 / (pts[0][1] * self.resolution)
        for i in range(1, len(pts)):
            if tick < pts[i][0]:
                return ms[i] + (tick - pts[i - 1][0]) * 60000.0 / (pts[i - 1][1] * self.resolution)
        return ms[-1] + (tick - pts[-1][0]) * 60000.0 / (pts[-1][1] * self.resolution)

    def ms_to_tick(self, ms_: float) -> float:
        pts, ms = self._pts, self._ms
        if ms_ <= ms[0]:
            return pts[0][0] + (ms_ - ms[0]) * (pts[0][1] * self.resolution) / 60000.0
        for i in range(1, len(pts)):
            if ms_ < ms[i]:
                return pts[i - 1][0] + (ms_ - ms[i - 1]) * (pts[i - 1][1] * self.resolution) / 60000.0
        return pts[-1][0] + (ms_ - ms[-1]) * (pts[-1][1] * self.resolution) / 60000.0

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "TempoMap":
        return cls(doc.get("tempos") or [{"position": 0, "bpm": doc.get("bpm", 120)}],
                   int(doc.get("resolution", 480)))


SPECIAL_LYRICS = {"AP", "SP", "+"}


def note_abs_range(part: dict, note: dict) -> tuple[int, int]:
    start = int(part["position"]) + int(note["position"])
    return start, start + int(note["duration"])


def is_sung(note: dict) -> bool:
    """Real lyric note (not AP/SP rest marker or '+' sustain)."""
    return str(note.get("lyric", "")) not in SPECIAL_LYRICS
