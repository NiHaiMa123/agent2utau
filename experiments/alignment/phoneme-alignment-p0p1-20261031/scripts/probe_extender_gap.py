"""Probe: is a '+' sustain note with a real time gap legal in OpenUtau?

P1.1-B asks for the legality of the illegal-gap extender to be judged by the
*actual* post-build result of OpenUtau, not by a threshold.  This probe
builds two tiny projects from the same template - one where the extender
touches the previous note, one where a 160 ms gap sits between them - and
reports what the native Core says about each.

Usage:
    python experiments/alignment/phoneme-alignment-p0p1-20261031/scripts/probe_extender_gap.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402

from agent2utau.openutau.build import RESOLUTION, sec_to_tick  # noqa: E402

OUT_DIR = REPO_ROOT / "runs" / "production" / "phoneme-alignment-p0p1-20261031" / "probes"
TEMPLATE = REPO_ROOT / "configs" / "ustx_template.yaml"


def build(name: str, gap_s: float) -> Path:
    """One part, one character note and one '+' extender, gap_s apart."""
    project = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    anchor = sec_to_tick(42.78)
    first_end = sec_to_tick(43.41)
    second_start = sec_to_tick(43.41 + gap_s)
    notes = [
        {
            "position": anchor - anchor,
            "duration": first_end - anchor,
            "tone": 64,
            "lyric": "声",
            "pitch": {"data": [{"x": -40, "y": 0, "shape": "io"},
                               {"x": 40, "y": 0, "shape": "io"}],
                      "snap_first": True},
            "vibrato": {"length": 0, "period": 175, "depth": 25, "in": 10,
                        "out": 10, "shift": 0, "drift": 0, "vol_link": 0},
            "tuning": 0,
            "phoneme_expressions": [],
            "phoneme_overrides": [],
        },
        {
            "position": second_start - anchor,
            "duration": sec_to_tick(43.76) - second_start,
            "tone": 64,
            "lyric": "+",
            "pitch": {"data": [{"x": -40, "y": 0, "shape": "io"},
                               {"x": 40, "y": 0, "shape": "io"}],
                      "snap_first": True},
            "vibrato": {"length": 0, "period": 175, "depth": 25, "in": 10,
                        "out": 10, "shift": 0, "drift": 0, "vol_link": 0},
            "tuning": 0,
            "phoneme_expressions": [],
            "phoneme_overrides": [],
        },
    ]
    project["name"] = name
    project["bpm"] = 120.0
    project["tempos"] = [{"position": 0, "bpm": 120.0}]
    project["voice_parts"] = [{
        "duration": notes[-1]["position"] + notes[-1]["duration"],
        "name": "seg0",
        "comment": "",
        "track_no": 0,
        "position": anchor,
        "notes": notes,
        "curves": [],
    }]
    project["wave_parts"] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.ustx"
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, width=10 ** 6)
    return out


def build_split_part(name: str) -> Path:
    """Same two notes, but the extender opens its own voice part."""
    project = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    anchor = sec_to_tick(42.78)
    first_end = sec_to_tick(43.41)
    second_start = sec_to_tick(43.57)

    def note(position: int, duration: int, lyric: str) -> dict:
        return {
            "position": position,
            "duration": duration,
            "tone": 64,
            "lyric": lyric,
            "pitch": {"data": [{"x": -40, "y": 0, "shape": "io"},
                               {"x": 40, "y": 0, "shape": "io"}],
                      "snap_first": True},
            "vibrato": {"length": 0, "period": 175, "depth": 25, "in": 10,
                        "out": 10, "shift": 0, "drift": 0, "vol_link": 0},
            "tuning": 0,
            "phoneme_expressions": [],
            "phoneme_overrides": [],
        }

    first_part = {
        "duration": first_end - anchor,
        "name": "seg0",
        "comment": "",
        "track_no": 0,
        "position": anchor,
        "notes": [note(0, first_end - anchor, "声")],
        "curves": [],
    }
    second_part = {
        "duration": sec_to_tick(43.76) - second_start,
        "name": "seg1",
        "comment": "",
        "track_no": 0,
        "position": second_start,
        "notes": [note(0, sec_to_tick(43.76) - second_start, "+")],
        "curves": [],
    }
    project["name"] = name
    project["bpm"] = 120.0
    project["tempos"] = [{"position": 0, "bpm": 120.0}]
    project["voice_parts"] = [first_part, second_part]
    project["wave_parts"] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.ustx"
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, width=10 ** 6)
    return out


def main() -> int:
    probes = {"extender_touching": build("extender_touching", 0.0),
              "extender_gap_160ms": build("extender_gap_160ms", 0.16),
              "split_part_starting_with_plus": build_split_part("split_part_starting_with_plus")}
    summary = {}
    for name, path in probes.items():
        print(f"--- {name}: {path}")
        summary[name] = {"project": str(path),
                         "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest()}
    (OUT_DIR / "extender_gap_probe.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
