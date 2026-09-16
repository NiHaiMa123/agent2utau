"""Map supplied lyric lines to detected voiced blocks and onset times.

Assumes lyric text is ordered and roughly one sung line per voiced block.
Within a block, each Hanzi char is assigned to one syllable onset; extra
onsets are merged, missing ones are interpolated into the largest gaps.
"""

from __future__ import annotations

import re
from typing import Any

_HANZI = re.compile(r"[一-鿿・々〆ヶ]")
_LRC_TS = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def lyric_chars(text: str) -> list[str]:
    return [c for c in text if _HANZI.match(c)]


def load_lyrics(path: str) -> list[str]:
    lines = []
    for raw in open(path, encoding="utf-8"):
        s = raw.strip()
        if s and lyric_chars(s):
            lines.append(s)
    return lines


def load_lrc(path: str) -> list[dict]:
    """Parse LRC: [{'start': sec, 'text': str}] sorted by time. Non-lyric
    metadata tags are skipped. Line end = next line's start."""
    out = []
    for raw in open(path, encoding="utf-8"):
        m = _LRC_TS.match(raw.strip())
        if not m:
            continue
        t = int(m.group(1)) * 60 + float(m.group(2))
        text = _LRC_TS.sub("", raw).strip()
        # strip singer prefixes like "张碧晨：" / "合：" (short tag before ：)
        if "：" in text[:5]:
            text = text.split("：", 1)[1]
        if lyric_chars(text):
            out.append({"start": t, "text": text})
    out.sort(key=lambda x: x["start"])
    for i, l in enumerate(out[:-1]):
        l["end"] = out[i + 1]["start"]
    if out:
        out[-1]["end"] = out[-1]["start"] + 8.0
    return out


def match_blocks(lines: list[str], blocks: list[tuple[float, float]],
                 n_chars_per_line: list[int] | None = None
                 ) -> list[tuple[int, int]]:
    """Return (line_idx, block_idx) pairs. Greedy: if counts match, 1:1;
    otherwise assign lines to the largest blocks in order."""
    n_chars = n_chars_per_line or [len(lyric_chars(l)) for l in lines]
    if len(blocks) == len(lines):
        return [(i, i) for i in range(len(lines))]
    pairs = []
    bi = 0
    for li, nc in enumerate(n_chars):
        if bi >= len(blocks):
            break
        pairs.append((li, bi))
        bi += 1
    return pairs


def distribute(chars: list[str], onsets: list[float],
               block_start: float, block_end: float) -> list[dict]:
    """Assign each char an [start,end] window from onset times."""
    n = len(chars)
    if n == 0:
        return []
    o = sorted(onsets)[:] or [block_start]
    # too many onsets: drop the interior boundary with the smallest interval;
    # first onset is pinned (it anchors the line start)
    while len(o) > n and len(o) > 2:
        bounds = [o[0]] + [(o[i] + o[i + 1]) / 2 for i in range(len(o) - 1)] \
                 + [block_end]
        gaps = [(bounds[i + 1] - bounds[i], i) for i in range(1, len(o))]
        _, i = min(gaps)
        del o[i]
    # too few onsets: split the largest intervals until we have n boundaries
    while len(o) < n:
        ends = o[1:] + [block_end]
        gaps = [(ends[i] - o[i], i) for i in range(len(o))]
        g, i = max(gaps)
        o.insert(i + 1, o[i] + g / 2)
        o.sort()
    out = []
    for i, c in enumerate(chars):
        st = o[i]
        en = o[i + 1] if i + 1 < len(o) else block_end
        out.append({"char": c, "start": round(st, 4), "end": round(en, 4)})
    return out


def align_lines(lines: list[str], blocks: list[tuple[float, float]],
                onsets_per_block: list[list[float]]) -> list[dict]:
    """Full alignment: returns flat char list with absolute times, plus
    per-line pairing info."""
    chars_all: list[dict] = []
    pairs = match_blocks(lines, blocks)
    for li, bi in pairs:
        chars = lyric_chars(lines[li])
        if not chars:
            continue
        seg = distribute(chars, onsets_per_block[bi],
                         blocks[bi][0], blocks[bi][1])
        for c in seg:
            c["line"] = li
            c["block"] = bi
        chars_all += seg
    return chars_all
