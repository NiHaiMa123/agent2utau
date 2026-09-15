"""`inspect-reference`: parse reference USTX projects and report structure."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .ustx import TempoMap, is_sung, load_ustx, note_abs_range, sha256


def inspect_project(path: Path) -> dict[str, Any]:
    doc = load_ustx(path)
    tm = TempoMap.from_doc(doc)
    tracks = doc.get("tracks") or []
    parts = doc.get("voice_parts") or []
    waves = doc.get("wave_parts") or []

    track_info = []
    for i, t in enumerate(tracks):
        track_info.append({
            "index": i,
            "track_name": t.get("track_name"),
            "singer": t.get("singer"),
            "phonemizer": t.get("phonemizer"),
            "renderer": (t.get("renderer_settings") or {}).get("renderer"),
            "voice_color_names": t.get("voice_color_names"),
            "mute": t.get("mute", False),
            "solo": t.get("solo", False),
        })

    part_info = []
    for p in parts:
        notes = p.get("notes") or []
        sung = [n for n in notes if is_sung(n)]
        curves = [c.get("abbr") for c in (p.get("curves") or [])]
        abs_ranges = [note_abs_range(p, n) for n in notes]
        part_info.append({
            "name": p.get("name"),
            "track_no": p.get("track_no"),
            "position": p.get("position"),
            "duration": p.get("duration"),
            "position_ms": round(tm.tick_to_ms(int(p["position"])), 1),
            "notes": len(notes),
            "sung_notes": len(sung),
            "curve_abbrs": sorted(set(curves)),
            "note_abs_start": min((r[0] for r in abs_ranges), default=None),
            "note_abs_end": max((r[1] for r in abs_ranges), default=None),
            "lyric_sample": [n.get("lyric") for n in sung[:12]],
        })

    wave_info = []
    base = path.parent
    for w in waves:
        rel = w.get("relative_path")
        resolved = (base / rel).resolve() if rel else None
        wave_info.append({
            "name": w.get("name"),
            "track_no": w.get("track_no"),
            "position": w.get("position"),
            "relative_path": rel,
            "resolved": str(resolved) if resolved else None,
            "exists": resolved.exists() if resolved else False,
        })

    expr_used = Counter()
    for p in parts:
        for n in p.get("notes") or []:
            for pe in n.get("phoneme_expressions") or []:
                expr_used[pe.get("abbr")] += 1
        for c in p.get("curves") or []:
            expr_used[f"curve:{c.get('abbr')}"] += 1

    return {
        "file": str(path),
        "sha256": sha256(path),
        "ustx_version": doc.get("ustx_version"),
        "resolution": doc.get("resolution"),
        "bpm_field": doc.get("bpm"),
        "tempos": doc.get("tempos"),
        "time_signatures": doc.get("time_signatures"),
        "expressions_defined": sorted((doc.get("expressions") or {}).keys()),
        "tracks": track_info,
        "voice_parts": part_info,
        "wave_parts": wave_info,
        "missing_wave_files": sum(1 for w in wave_info if not w["exists"]),
        "expression_usage": dict(expr_used),
    }


def inspect_reference(ref_dir: Path) -> dict[str, Any]:
    files = sorted(ref_dir.glob("*.ustx"))
    return {
        "schema_version": "1",
        "status": "ok" if files else "failed",
        "dir": str(ref_dir),
        "projects": [inspect_project(f) for f in files],
    }
