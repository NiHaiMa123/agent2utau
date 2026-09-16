"""Build a fresh USTX (0.9) from generated notes, using the verified template.

Time axis: fixed tempo 120 bpm at resolution 480 -> 1 tick = 1.0417 ms.
This is an explicitly-labelled fixed tempo (score.json records
tempo_source="fixed"), NOT an estimated real BPM.

Multi-part layout: one voice part per lyric segment; part.position is the
absolute timeline position, so the rendered track aligns with the original
song for mixing.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

RESOLUTION = 480
BPM_FIXED = 120.0
TEMPLATE = Path(__file__).resolve().parents[3] / "configs" / "ustx_template.yaml"


def sec_to_tick(sec: float) -> int:
    return int(round(sec * 1000.0 / (60000.0 / (BPM_FIXED * RESOLUTION))))


def _note(n: dict, part_start_sec: float) -> dict:
    return {
        "position": sec_to_tick(n["start"] - part_start_sec),
        "duration": max(1, sec_to_tick(n["dur"])),
        "tone": int(n["tone"]),
        "lyric": n["lyric"],
        "pitch": {"data": [
            {"x": -40, "y": 0, "shape": "io"},
            {"x": 40, "y": 0, "shape": "io"}],
            "snap_first": True},
        "vibrato": {"length": 0, "period": 175, "depth": 25, "in": 10,
                    "out": 10, "shift": 0, "drift": 0, "vol_link": 0},
        "tuning": 0,
        "phoneme_expressions": [],
        "phoneme_overrides": [],
    }


def build_project(name: str, segments: list[dict], out_ustx: Path,
                  template: Path | None = None,
                  voice_color: str | None = None) -> Path:
    """segments: [{'notes':[...], 'start_sec':float}] — one part per segment."""
    tpl_path = Path(template) if template else TEMPLATE
    project = yaml.safe_load(tpl_path.read_text(encoding="utf-8"))
    project = copy.deepcopy(project)
    project["name"] = name
    project["bpm"] = BPM_FIXED
    project["tempos"] = [{"position": 0, "bpm": BPM_FIXED}]
    if voice_color:
        track = project["tracks"][0]
        colors = track.get("voice_color_names") or []
        if voice_color not in colors:
            raise ValueError(
                f"voice_color '{voice_color}' not in {colors}")
        project["_voice_color_value"] = colors.index(voice_color)
        project["expressions"]["clr"]["options"] = colors
        project["expressions"]["clr"]["max"] = len(colors) - 1
    clr_value = project.pop("_voice_color_value", None)
    parts = []
    for i, seg in enumerate(segments):
        notes = [_note(n, seg["start_sec"]) for n in seg["notes"]]
        if not notes:
            continue
        if clr_value is not None:
            # clr is per-phoneme: write indices 0..7 so every phoneme in the
            # note matches (extra indices are simply never queried)
            for nd in notes:
                nd["phoneme_expressions"] = [
                    {"index": j, "abbr": "clr", "value": clr_value}
                    for j in range(8)]
        part_start = sec_to_tick(seg["start_sec"])
        parts.append({
            "duration": notes[-1]["position"] + notes[-1]["duration"],
            "name": f"seg{i}",
            "comment": "",
            "track_no": 0,
            "position": part_start,
            "notes": notes,
            "curves": seg.get("curves", []),
        })
    project["voice_parts"] = parts
    project["wave_parts"] = []
    out_ustx.parent.mkdir(parents=True, exist_ok=True)
    with open(out_ustx, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False,
                       width=10 ** 6)
    return out_ustx
