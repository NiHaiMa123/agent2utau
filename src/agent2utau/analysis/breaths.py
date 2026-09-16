"""Insert 'AP' breath-intake notes at phrase starts (reference convention).

Reference projects (有参by白烁) place a short 'AP' note in the gap before a
phrase's first sung note — median ~0.2s, tone borrowed from the next note.
Breaths are only inserted where a real gap exists; they never overlap sung
audio and are excluded from pitch evaluation.
"""

from __future__ import annotations

AP_LYRIC = "AP"
MIN_GAP_SEC = 0.55   # silence needed before a line to fit a breath
AP_MAX_SEC = 0.32    # cap; refs use ~0.09-0.75s, median ~0.2s
AP_TAIL_SEC = 0.06   # small rest between breath end and first sung note
AP_MIN_SEC = 0.08


def insert_breaths(seg_payloads: list[dict]) -> int:
    """Prepend AP notes in-place; returns count inserted.

    Each AP goes at the head of a segment's note list and moves
    seg['part_start_sec'] earlier so part-relative positions stay >= 0.
    """
    n_inserted = 0
    prev_end = 0.0
    for seg in seg_payloads:
        notes = seg.get("notes") or []
        seg.setdefault("part_start_sec", seg["start_sec"])
        if notes:
            first = notes[0]
            gap = first["start"] - prev_end
            dur = min(AP_MAX_SEC, gap - AP_TAIL_SEC)
            if gap >= MIN_GAP_SEC and dur >= AP_MIN_SEC:
                ap = {"lyric": AP_LYRIC,
                      "start": round(first["start"] - AP_TAIL_SEC - dur, 4),
                      "dur": round(dur, 4),
                      "tone": int(first["tone"]),
                      "conf": "breath", "is_breath": True,
                      "voiced_frac": 0.0}
                notes.insert(0, ap)
                seg["part_start_sec"] = ap["start"]
                n_inserted += 1
            prev_end = max(n["start"] + n["dur"] for n in notes)
    return n_inserted
