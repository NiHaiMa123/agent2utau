"""Migrate a short Yousa lead-vocal phrase from a reference project to the
current singer (YousaV1.65b), producing a minimal valid USTX.

Color semantics (verified against OpenUtau @9699944):
- note-level {abbr: clr, value: i} -> VoiceColorExp.options[i]; options are
  singer subbank colors SORTED ALPHABETICALLY -> remap by name.
- clNN curves -> index into dsSinger.Subbanks (character.yaml order), which
  matches the old 01..05 order -> values kept, descriptor names updated.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .ustx import TempoMap, is_sung, load_ustx, note_abs_range, save_ustx

# character.yaml subbank order (clNN indices are 1-based into this list)
YOUSA_SUBBANK_ORDER = ["Yousa_Bright", "Yousa_Cute", "Yousa_Normal",
                       "Yousa_Whisper", "Yousa_Classic"]
# VoiceColorExp.options = colors sorted alphabetically
YOUSA_CLR_OPTIONS = sorted(YOUSA_SUBBANK_ORDER)

DEFAULT_SINGER = "YousaV1.65b"


def _color_semantic(name: str) -> str:
    n = str(name).strip().lower()
    if ":" in n:  # "01:Bright" -> "bright"
        n = n.split(":", 1)[1].strip()
    if n.startswith("yousa_"):
        n = n[6:]
    return n


def build_clr_map(old_names: list[str], new_options: list[str]) -> dict[int, int]:
    """old clr index -> new clr index, matched by color semantic name."""
    sem_to_new = {_color_semantic(n): i for i, n in enumerate(new_options)}
    mapping: dict[int, int] = {}
    for i, old in enumerate(old_names):
        sem = _color_semantic(old)
        if sem in sem_to_new:
            mapping[i] = sem_to_new[sem]
    return mapping


def remap_note_colors(note: dict, clr_map: dict[int, int]) -> list[str]:
    changed = []
    for pe in note.get("phoneme_expressions") or []:
        if pe.get("abbr") == "clr" and isinstance(pe.get("value"), int):
            old = pe["value"]
            if old in clr_map and clr_map[old] != old:
                pe["value"] = clr_map[old]
                changed.append(f"clr {old}->{pe['value']}")
    return changed


def select_phrase(part: dict, tm: TempoMap, part_index: int = 0,
                  min_notes: int = 8,
                  min_ms: float = 4000, max_ms: float = 12000,
                  max_gap_ms: float = 1500) -> dict[str, Any] | None:
    """Pick a contiguous run of sung notes ~min_ms..max_ms long."""
    notes = part.get("notes") or []
    sung_idx = [i for i, n in enumerate(notes) if is_sung(n)]
    best = None
    i = 0
    while i < len(sung_idx):
        j = i
        while j + 1 < len(sung_idx):
            _, e0 = note_abs_range(part, notes[sung_idx[j]])
            s1, _ = note_abs_range(part, notes[sung_idx[j + 1]])
            if tm.tick_to_ms(s1) - tm.tick_to_ms(e0) > max_gap_ms:
                break
            j += 1
        # run notes[sung_idx[i..j]]
        s_abs, _ = note_abs_range(part, notes[sung_idx[i]])
        _, e_abs = note_abs_range(part, notes[sung_idx[j]])
        ms = tm.tick_to_ms(e_abs) - tm.tick_to_ms(s_abs)
        cnt = j - i + 1
        if cnt >= min_notes and ms >= min_ms:
            cand = {"start_tick": s_abs, "end_tick": e_abs,
                    "ms": ms, "sung_count": cnt, "part_index": part_index,
                    "note_range": (sung_idx[i], sung_idx[j]),
                    "score": -abs(ms - 7000)}
            if best is None or cand["score"] > best["score"]:
                best = cand
            if ms > max_ms:
                # truncate to first notes fitting max_ms
                for k in range(j, i + min_notes - 1, -1):
                    _, ek = note_abs_range(part, notes[sung_idx[k]])
                    if tm.tick_to_ms(ek) - tm.tick_to_ms(s_abs) <= max_ms:
                        best = {"start_tick": s_abs, "end_tick": ek,
                                "ms": tm.tick_to_ms(ek) - tm.tick_to_ms(s_abs),
                                "sung_count": k - i + 1,
                                "part_index": part_index,
                                "note_range": (sung_idx[i], sung_idx[k]),
                                "score": 0}
                        break
                break
        i = j + 1
    return best


def migrate_phrase(src_path: str | Path, out_path: str | Path,
                   track_no: int, phrase: dict[str, Any],
                   new_singer: str = DEFAULT_SINGER,
                   lead_ticks: int = 480, tail_ticks: int = 480,
                   curve_margin: int = 960) -> dict[str, Any]:
    doc = load_ustx(src_path)
    tm = TempoMap.from_doc(doc)
    tracks = doc.get("tracks") or []
    parts = doc.get("voice_parts") or []
    track = tracks[track_no]
    part = parts[phrase["part_index"]]

    old_colors = track.get("voice_color_names") or []
    clr_map = build_clr_map(old_colors, YOUSA_CLR_OPTIONS)
    report: dict[str, Any] = {
        "schema_version": "1",
        "source": str(src_path),
        "track_no": track_no,
        "old_singer": track.get("singer"),
        "new_singer": new_singer,
        "old_colors": old_colors,
        "new_clr_options": YOUSA_CLR_OPTIONS,
        "clr_map": {str(k): v for k, v in clr_map.items()},
        "unmapped_colors": [n for i, n in enumerate(old_colors) if i not in clr_map],
        "phrase": {**phrase,
                   "start_ms": round(tm.tick_to_ms(phrase["start_tick"]), 1),
                   "end_ms": round(tm.tick_to_ms(phrase["end_tick"]), 1)},
        "notes_remapped": [],
        "dropped": {},
    }

    w0, w1 = phrase["start_tick"], phrase["end_tick"]
    new_pos = 0
    shift = (w0 - lead_ticks)  # absolute tick -> new project tick

    # --- new doc skeleton: keep header semantics ---
    out = {
        "name": f"{doc.get('name', 'project')} [a2u phrase]",
        "comment": f"migrated from {Path(src_path).name} track {track_no} "
                   f"ticks {w0}-{w1}",
        "output_dir": "Vocal",
        "cache_dir": "UCache",
        "ustx_version": doc.get("ustx_version"),
        "resolution": doc.get("resolution"),
        "bpm": doc.get("bpm"),
        "beat_per_bar": doc.get("beat_per_bar"),
        "beat_unit": doc.get("beat_unit"),
    }

    # expressions: copy; rename clNN descriptor names to new color names
    exprs = copy.deepcopy(doc.get("expressions") or {})
    for i, new_name in enumerate(YOUSA_SUBBANK_ORDER, start=1):
        abbr = f"cl{i:02d}"
        if abbr in exprs:
            exprs[abbr]["name"] = f"voice color {new_name}"
    out["expressions"] = exprs
    for k in ("exp_selectors", "exp_primary", "exp_secondary", "key",
              "time_signatures", "tempos"):
        if k in doc:
            out[k] = doc[k]

    # --- single migrated track ---
    new_track = copy.deepcopy(track)
    new_track["singer"] = new_singer
    new_track["track_name"] = f"{track.get('track_name', 'vocal')}-yousa"
    new_track["voice_color_names"] = YOUSA_CLR_OPTIONS
    new_track["mute"] = False
    new_track["solo"] = False
    out["tracks"] = [new_track]

    # --- single migrated part ---
    new_part = copy.deepcopy(part)
    new_part["name"] = f"{part.get('name', 'part')}-phrase"
    new_part["track_no"] = 0
    new_part["position"] = new_pos
    new_part["duration"] = (w1 + tail_ticks) - (w0 - lead_ticks)

    kept_notes = []
    for n in part.get("notes") or []:
        s, e = note_abs_range(part, n)
        if s >= w0 - 1 and e <= w1 + 1:  # fully inside window
            nn = copy.deepcopy(n)
            nn["position"] = s - shift
            changed = remap_note_colors(nn, clr_map)
            if changed:
                report["notes_remapped"].append(
                    {"lyric": nn.get("lyric"), "changes": changed})
            kept_notes.append(nn)
    new_part["notes"] = kept_notes
    report["dropped"]["notes_outside_window"] = len(part.get("notes") or []) - len(kept_notes)

    kept_curves = []
    for c in part.get("curves") or []:
        xs = [x for x in c.get("xs") or []]
        ys = list(c.get("ys") or [])
        abbr = c.get("abbr")
        pts = [(x + int(part["position"]), y) for x, y in zip(xs, ys)]  # abs ticks
        inside = [(x, y) for x, y in pts
                  if w0 - curve_margin <= x <= w1 + curve_margin]
        # keep straddling neighbours so interpolation across the cut survives
        before = [(x, y) for x, y in pts if x < w0 - curve_margin]
        after = [(x, y) for x, y in pts if x > w1 + curve_margin]
        sel = (before[-1:] if before else []) + inside + (after[:1] if after else [])
        if len(sel) < 2:
            continue
        xs2 = [x - shift for x, _ in sel]
        ys2 = [y for _, y in sel]
        if abbr == "clr":
            ys2 = [clr_map.get(int(y), int(y)) for y in ys2]
        kept_curves.append({"xs": xs2, "ys": ys2, "abbr": abbr})
    new_part["curves"] = kept_curves
    report["dropped"]["curves"] = [
        c.get("abbr") for c in (part.get("curves") or []) if len(c.get("xs") or []) < 2]

    out["voice_parts"] = [new_part]
    out["wave_parts"] = []  # missing audio references removed intentionally

    save_ustx(out, out_path)
    report["out"] = str(out_path)
    report["notes_kept"] = len(kept_notes)
    report["curves_kept"] = [c["abbr"] for c in kept_curves]
    report["part_duration_ms"] = round(
        tm.tick_to_ms(new_part["duration"]), 1)
    return report
