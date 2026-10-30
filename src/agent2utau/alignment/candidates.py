"""Deterministic syllable <-> note mapping (P1 baseline).

The program owns correctness; the Agent only adjudicates ambiguity.  This
module therefore produces, for every syllable:

* the best *monotonic* assignment of GAME notes (a dynamic program over
  syllable index x note index), and
* for every ambiguous window, several code-generated candidate options with
  exact costs and their evidence.

Hard constraints enforced here and re-checked by ``validator.py``:

* syllable order is complete - no dropped, swapped or invented characters;
* one note never belongs to two syllables; a syllable may own several
  consecutive notes (melisma);
* rests are never handed to a syllable;
* durations stay positive and notes never overlap;
* an assignment that cannot be justified becomes ``unresolved`` instead of a
  guess.

A window candidate only ever redistributes the notes the global optimum gave
to that window: the note budget of the window is fixed, so an option can never
steal a note from a neighbouring syllable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from typing import Sequence

from .lyrics import Syllable
from .notes import NoteEvent
from .observations import LEVEL_WEIGHTS, Observation

SCHEMA_VERSION = 1

#: An extender may not cross a real gap.  Verified with the real Core: a '+'
#: that does not touch its character produces "Unrecognized phoneme" and is
#: left out of the phrase.
MAX_EXTENDER_GAP_TICKS = 1


def _illegal_sustains(spans: dict[str, tuple[int, int]],
                       sung: Sequence[NoteEvent]) -> list[str]:
    """Note ids of sustains that would cross a gap (or a rest) in a candidate."""
    from .baseline import MAX_EXTENDER_GAP_TICKS as limit
    illegal: list[str] = []
    for span in spans.values():
        for index in range(span[0] + 1, span[1] + 1):
            previous = sung[index - 1]
            current = sung[index]
            gap = current.start - previous.end
            gap_ticks = int(round(gap * 960.0))
            if gap_ticks > limit or current.index != previous.index + 1:
                illegal.append(current.note_id)
    return illegal


@dataclass(frozen=True)
class MappingConfig:
    """Weights and thresholds of the deterministic mapping.

    The numbers live in configuration, not in prompts, so a different model
    cannot silently change the baseline.
    """

    max_melisma: int = 3
    """Maximum number of consecutive notes one syllable may own."""

    time_scale_s: float = 0.35
    """Anchor error that costs 1.0."""

    duration_scale_s: float = 0.5
    """Duration error that costs 1.0."""

    duration_cap: float = 1.0
    """Upper bound of the duration penalty: a badly segmented observation must
    not outvote the time anchor."""

    min_expected_dur_s: float = 0.08
    """Observations shorter than this are treated as unreliable and ignored."""

    melisma_cost: float = 0.35
    """Cost of every extra note a syllable owns."""

    skip_cost: float = 0.8
    """Cost of leaving a voiced note without a syllable."""

    unresolved_cost: float = 1.5
    """Cost of declaring a syllable unresolved (must beat a bad fit)."""

    ambiguity_margin: float = 0.3
    """Cost gap below which two assignments count as ambiguous."""

    window_min: int = 5
    window_max: int = 15
    """Ambiguity window size handed to the Agent (5-15 characters)."""

    window_cost_limit: float = 1.5
    """How far above the optimum a window option may cost and still be listed."""

    max_options: int = 8
    """Maximum candidate options per window."""

    max_paths: int = 60
    """Maximum alternative local paths enumerated per window."""

    alternatives_per_syllable: int = 4
    """How many distinct assignments are kept per syllable for margin checks."""

    line_tolerance_s: float = 0.6
    """How far outside its lyric line a syllable may reach for a note.

    A note that starts far outside the line's observed interval would be a
    cross-line mapping without evidence, and is rejected.
    """

    min_line_anchor_ratio: float = 0.5
    """A line with fewer anchored syllables than this is flagged
    ``review_required``: its musical boundary is not established."""


@dataclass
class SyllableEvidence:
    """Time evidence available for one syllable."""

    syllable_id: str
    anchor_s: float | None = None
    anchor_source: str = "none"
    anchor_method: str = "none"
    anchor_level: str = "missing"
    anchor_weight: float = 0.0
    expected_dur_s: float | None = None

    def as_dict(self) -> dict:
        return {
            "syllable_id": self.syllable_id,
            "anchor_s": None if self.anchor_s is None else round(self.anchor_s, 4),
            "anchor_source": self.anchor_source,
            "anchor_method": self.anchor_method,
            "anchor_level": self.anchor_level,
            "anchor_weight": self.anchor_weight,
            "expected_dur_s": None if self.expected_dur_s is None else round(self.expected_dur_s, 4),
        }


def build_evidence(
    syllables: Sequence[Syllable],
    hfa: dict[str, Observation] | None = None,
    asr: dict[str, Observation] | None = None,
) -> dict[str, SyllableEvidence]:
    """Anchor every syllable on the strongest available observation.

    HFA is a singer-side observation and wins over ASR, which is a rough
    speech-side guess.  A syllable with neither stays unanchored and is
    mapped by monotonicity alone.
    """
    evidence: dict[str, SyllableEvidence] = {}
    for syllable in syllables:
        item = SyllableEvidence(syllable_id=syllable.syllable_id)
        hfa_obs = (hfa or {}).get(syllable.syllable_id)
        asr_obs = (asr or {}).get(syllable.syllable_id)
        observation = hfa_obs or asr_obs
        if observation is not None:
            item.anchor_s = observation.start
            item.anchor_source = observation.source
            item.anchor_method = observation.method
            item.anchor_level = getattr(observation, "level", "exact_text")
            item.anchor_weight = LEVEL_WEIGHTS.get(item.anchor_level, 0.35)
            item.expected_dur_s = max(0.0, observation.end - observation.start)
        evidence[syllable.syllable_id] = item
    return evidence


@dataclass
class Assignment:
    """One monotone assignment of syllables to note spans."""

    spans: dict[str, tuple[int, int]] = field(default_factory=dict)
    """syllable_id -> (first note index, last note index) inclusive."""

    unresolved: list[str] = field(default_factory=list)
    cost: float = 0.0
    cursor: list[int] = field(default_factory=list)
    """cursor[i] = first note index available for syllable i in this path."""


def _assign_cost(
    evidence: SyllableEvidence,
    notes: Sequence[NoteEvent],
    first: int,
    count: int,
    config: MappingConfig,
    raw_index: Sequence[int],
) -> float:
    """Cost of giving ``count`` notes starting at ``first`` to one syllable.

    ``inf`` means the assignment is illegal: a syllable may only own notes
    that follow each other in the original event list.  A rest between two
    notes breaks the sustain chain, so the syllable cannot jump over it.
    """
    indices = raw_index[first:first + count]
    for position in range(1, len(indices)):
        if indices[position] != indices[position - 1] + 1:
            return float("inf")
    cost = config.melisma_cost * (count - 1)
    if evidence.anchor_s is not None:
        # A weak observation (residual / positional) must not be able to pull
        # a syllable far away: the smaller the weight, the steeper the scale.
        scale = config.time_scale_s * max(evidence.anchor_weight, 0.05)
        cost += abs(evidence.anchor_s - notes[first].start) / scale
    if (evidence.expected_dur_s is not None
            and evidence.expected_dur_s >= config.min_expected_dur_s):
        actual = sum(notes[i].dur for i in range(first, first + count))
        cost += min(abs(evidence.expected_dur_s - actual) / config.duration_scale_s,
                    config.duration_cap)
    return cost


class _Tables:
    """Suffix/prefix cost tables over (syllable index, note index)."""

    def __init__(self, syllables: Sequence[Syllable], notes: Sequence[NoteEvent],
                 evidence: dict[str, SyllableEvidence], config: MappingConfig,
                 lines: dict[int, dict] | None = None):
        self.syllables = syllables
        self.all_notes = notes
        self.raw_index = [n.index for n in notes if n.voiced]
        self.notes = [n for n in notes if n.voiced]
        self.evidence = evidence
        self.config = config
        self.lines = lines or {}
        self.n_syl = len(syllables)
        self.n_notes = len(self.notes)
        self.suffix: list[list[float]] = []
        self.prefix: list[list[float]] = []
        self.back: list[list[tuple]] = []
        self._build()

    def _line_allowed(self, syllable_index: int, note_start: float) -> bool:
        """A note may only be taken from the syllable's own lyric line."""
        line = self.lines.get(self.syllables[syllable_index].line_index)
        if not line or not line.get("interval_s") or line["interval_s"][0] is None:
            return True
        start, end = line["interval_s"]
        tolerance = self.config.line_tolerance_s
        return (start - tolerance) <= note_start <= (end + tolerance)

    def transitions(self, i: int, j: int) -> list[tuple[str, float, int]]:
        """All transitions out of state (i, j) as (kind, cost, next_note_index)."""
        out: list[tuple[str, float, int]] = []
        cfg = self.config
        if j < self.n_notes:
            out.append(("skip", cfg.skip_cost, j + 1))
        ev = self.evidence[self.syllables[i].syllable_id]
        max_melisma = min(cfg.max_melisma, self.n_notes - j)
        for count in range(1, max_melisma + 1):
            cost = _assign_cost(ev, self.notes, j, count, cfg, self.raw_index)
            if math.isfinite(cost) and not self._line_allowed(i, self.notes[j].start):
                cost = float("inf")
            out.append(("assign", cost, j + count))
        out.append(("unresolved", cfg.unresolved_cost, j))
        return out

    def _build(self) -> None:
        cfg = self.config
        n_syl, n_notes = self.n_syl, self.n_notes
        inf = float("inf")
        suffix = [[inf] * (n_notes + 1) for _ in range(n_syl + 1)]
        back: list[list[tuple]] = [[None] * (n_notes + 1) for _ in range(n_syl + 1)]
        for j in range(n_notes + 1):
            # notes that stay unassigned after the last syllable still cost:
            # otherwise "drop the note" would always beat "sing it as melisma"
            suffix[n_syl][j] = cfg.skip_cost * (n_notes - j)
        for i in range(n_syl - 1, -1, -1):
            for j in range(n_notes, -1, -1):
                best, best_move = inf, None
                for kind, cost, nxt in self.transitions(i, j):
                    if kind == "skip":
                        value = cost + suffix[i][nxt]
                    else:
                        value = cost + suffix[i + 1][nxt]
                    if value < best:
                        best, best_move = value, (kind, cost, nxt)
                suffix[i][j] = best
                back[i][j] = best_move
        self.suffix, self.back = suffix, back

        prefix = [[inf] * (n_notes + 1) for _ in range(n_syl + 1)]
        prefix[0][0] = 0.0
        for i in range(n_syl + 1):
            for j in range(n_notes + 1):
                base = prefix[i][j]
                if base == inf or i == n_syl:
                    continue
                for kind, cost, nxt in self.transitions(i, j):
                    value = base + cost
                    if kind == "skip":
                        if value < prefix[i][nxt]:
                            prefix[i][nxt] = value
                    else:
                        if value < prefix[i + 1][nxt]:
                            prefix[i + 1][nxt] = value
        self.prefix = prefix

    def best_total(self) -> float:
        return min(self.prefix[self.n_syl][j] + self.suffix[self.n_syl][j]
                   for j in range(self.n_notes + 1))

    def best_assignment(self) -> Assignment:
        """Walk the optimal path back into a concrete assignment."""
        i = j = 0
        spans: dict[str, tuple[int, int]] = {}
        unresolved: list[str] = []
        cursor: list[int] = []
        while i < self.n_syl:
            move = self.back[i][j]
            if move is None:
                break
            kind, _cost, nxt = move
            if kind == "skip":
                # a skipped note belongs to no syllable; the cursor of the
                # syllable itself does not move
                j = nxt
                continue
            cursor.append(j)
            if kind == "unresolved":
                unresolved.append(self.syllables[i].syllable_id)
                i += 1
                continue
            spans[self.syllables[i].syllable_id] = (j, nxt - 1)
            i += 1
            j = nxt
        return Assignment(spans=spans, unresolved=unresolved,
                          cost=self.best_total(), cursor=cursor)


def _local_paths(
    tables: _Tables,
    start_syl: int,
    end_syl: int,
    j_start: int,
    j_end: int,
    limit: float,
    max_paths: int,
) -> list[tuple[float, dict[str, tuple[int, int]], list[str]]]:
    """Enumerate alternative assignments inside one window.

    The window keeps the note budget of the global optimum: the same notes in
    ``[j_start, j_end)`` must be distributed over the same syllables.  Every
    returned path carries its exact total cost, computed from the prefix and
    suffix tables - never an invented number.
    """
    results: list[tuple[float, dict[str, tuple[int, int]], list[str]]] = []
    base_cost = tables.prefix[start_syl][j_start]
    if base_cost == float("inf"):
        return results

    def walk(i: int, j: int, acc: float, spans: dict[str, tuple[int, int]],
             unresolved: list[str]):
        if len(results) >= max_paths:
            return
        if i > end_syl:
            if j == j_end:
                results.append((acc + tables.suffix[end_syl + 1][j], dict(spans), list(unresolved)))
            return
        if tables.prefix[i][j] == float("inf"):
            return
        # prune: even the cheapest completion must stay within the limit
        if acc + tables.suffix[i][j] > limit:
            return
        for kind, cost, nxt in tables.transitions(i, j):
            new_acc = acc + cost
            if kind == "assign":
                sid = tables.syllables[i].syllable_id
                spans[sid] = (j, nxt - 1)
                walk(i + 1, nxt, new_acc, spans, unresolved)
                spans.pop(sid, None)
            elif kind == "unresolved":
                unresolved.append(tables.syllables[i].syllable_id)
                walk(i + 1, nxt, new_acc, spans, unresolved)
                unresolved.pop()
            else:
                walk(i, nxt, new_acc, spans, unresolved)

    walk(start_syl, j_start, base_cost, {}, [])
    return results


def line_intervals(
    syllables: Sequence[Syllable],
    evidence: dict[str, SyllableEvidence],
    config: MappingConfig,
) -> dict[int, dict]:
    """Auditable time interval and anchor coverage per lyric line.

    A line is only a musical boundary when its syllables carry enough time
    evidence; otherwise it is flagged ``review_required`` instead of being
    treated as a hard edge.
    """
    by_line: dict[int, list[Syllable]] = {}
    for syllable in syllables:
        by_line.setdefault(syllable.line_index, []).append(syllable)
    out: dict[int, dict] = {}
    for line_index, line in by_line.items():
        anchors = [evidence[s.syllable_id] for s in line]
        timed = [a for a in anchors if a.anchor_s is not None]
        ratio = len(timed) / max(1, len(line))
        if timed:
            start = min(a.anchor_s for a in timed)
            end = max(a.anchor_s + (a.expected_dur_s or 0.0) for a in timed)
        else:
            start = end = None
        out[line_index] = {
            "line_index": line_index,
            "syllable_ids": [s.syllable_id for s in line],
            "syllable_count": len(line),
            "anchored_count": len(timed),
            "anchor_ratio": round(ratio, 4),
            "interval_s": [None if start is None else round(start, 4),
                           None if end is None else round(end, 4)],
            "review_required": ratio < config.min_line_anchor_ratio,
        }
    return out


def map_syllables_to_notes(
    syllables: Sequence[Syllable],
    notes: Sequence[NoteEvent],
    evidence: dict[str, SyllableEvidence],
    config: MappingConfig | None = None,
    *,
    song_id: str = "song",
) -> dict:
    """Build the ``mapping.v1`` document for one song."""
    config = config or MappingConfig()
    sung = [n for n in notes if n.voiced]
    if not sung:
        raise ValueError("No voiced GAME notes to map")
    lines = line_intervals(syllables, evidence, config)
    tables = _Tables(syllables, sung, evidence, config, lines=lines)
    best = tables.best_assignment()
    best_total = tables.best_total()

    # per-syllable alternatives and margins
    per_syllable: dict[str, list[tuple[float, tuple[int, int] | None]]] = {}
    for i, syllable in enumerate(syllables):
        options: list[tuple[float, tuple[int, int] | None]] = []
        for j in range(tables.n_notes + 1):
            if tables.prefix[i][j] == float("inf"):
                continue
            for kind, cost, nxt in tables.transitions(i, j):
                if kind == "skip":
                    continue
                total = tables.prefix[i][j] + cost + tables.suffix[i + 1][nxt]
                if not math.isfinite(total):
                    continue
                options.append((total, (j, nxt - 1) if kind == "assign" else None))
        options.sort(key=lambda item: item[0])
        seen: set[object] = set()
        unique: list[tuple[float, tuple[int, int] | None]] = []
        for total, span in options:
            if span in seen:
                continue
            seen.add(span)
            unique.append((total, span))
            if len(unique) >= config.alternatives_per_syllable:
                break
        per_syllable[syllable.syllable_id] = unique

    ambiguous: list[str] = []
    for syllable in syllables:
        options = per_syllable[syllable.syllable_id]
        if len(options) >= 2 and options[1][0] - options[0][0] < config.ambiguity_margin:
            ambiguous.append(syllable.syllable_id)

    # group ambiguous syllables into windows of 5-15 characters
    index_of = {s.syllable_id: i for i, s in enumerate(syllables)}
    windows: list[tuple[int, int]] = []
    for syllable_id in ambiguous:
        i = index_of[syllable_id]
        if windows and i <= windows[-1][1] + 1:
            windows[-1] = (windows[-1][0], i)
        else:
            windows.append((i, i))
    sized: list[tuple[int, int]] = []
    for start, end in windows:
        while end - start + 1 < config.window_min and end + 1 < len(syllables):
            end += 1
        while end - start + 1 > config.window_max:
            start += 1
        sized.append((start, end))

    candidates: list[dict] = []
    window_records: list[dict] = []
    for w_index, (start, end) in enumerate(sized):
        window_id = f"w{w_index + 1:02d}"
        j_start = best.cursor[start] if start < len(best.cursor) else tables.n_notes
        j_end = best.cursor[end + 1] if end + 1 < len(best.cursor) else tables.n_notes
        if j_end < j_start:
            j_end = j_start
        limit = best_total + config.window_cost_limit
        local = _local_paths(tables, start, end, j_start, j_end, limit, config.max_paths)
        options: list[dict] = []
        seen_keys: set[str] = set()
        window_syllable_ids = [s.syllable_id for s in syllables[start:end + 1]]
        for total, spans, unresolved in sorted(local, key=lambda item: item[0]):
            if not math.isfinite(total):
                continue
            # a candidate may only use syllables and notes of its own window
            if any(sid not in window_syllable_ids for sid in spans):
                continue
            if any(a < j_start or a >= j_end for span in spans.values()
                   for a in range(span[0], span[1] + 1)):
                continue
            key = "|".join(f"{sid}:{s[0]}-{s[1]}" for sid, s in sorted(spans.items()))
            key += "#" + ",".join(sorted(unresolved))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            illegal = _illegal_sustains(spans, sung)
            options.append({
                "candidate_id": f"map:{song_id}:{window_id}:option{len(options) + 1}",
                "window_id": window_id,
                "syllable_ids": window_syllable_ids,
                "assignment": {
                    sid: [sung[a].note_id for a in range(sp[0], sp[1] + 1)]
                    for sid, sp in spans.items()
                },
                "unresolved_syllable_ids": sorted(unresolved),
                "total_cost": round(total, 4),
                "legal": not illegal,
                "reason_code": "illegal_sustain_gap" if illegal else "dp_monotonic_optimum",
                "illegal_sustain_note_ids": illegal,
            })
            if len(options) >= config.max_options:
                break
        legal_options = [o for o in options if o["legal"]]
        best_in_window = {
            sid: list(range(span[0], span[1] + 1))
            for sid, span in best.spans.items()
            if sid in window_syllable_ids
        }
        best_key = json.dumps({k: [sung[i].note_id for i in v] for k, v in sorted(best_in_window.items())},
                              ensure_ascii=False)
        alternatives = [o for o in legal_options
                        if json.dumps(o["assignment"], ensure_ascii=False, sort_keys=True) != best_key]
        if not legal_options:
            decision = "no_valid_candidate"
        elif not alternatives:
            decision = "no_agent_decision_needed"
        else:
            decision = "agent_choice"
        candidates.extend(alternatives)
        window_records.append({
            "window_id": window_id,
            "syllable_ids": window_syllable_ids,
            "text": "".join(s.text for s in syllables[start:end + 1]),
            "option_count": len(legal_options),
            "alternative_count": len(alternatives),
            "decision": decision,
            "note_budget": [j_start, j_end],
            "lines": sorted({s.line_index for s in syllables[start:end + 1]}),
        })

    mapping_rows: list[dict] = []
    unresolved_rows: list[dict] = []
    review_syllables: set[str] = set()
    for window in window_records:
        if window.get("decision") == "no_valid_candidate":
            review_syllables.update(window["syllable_ids"])
    for line in lines.values():
        if line.get("review_required"):
            review_syllables.update(line["syllable_ids"])
    for syllable in syllables:
        sid = syllable.syllable_id
        ev = evidence[sid]
        if sid in best.unresolved:
            row = {
                "syllable_id": sid,
                "text": syllable.text,
                "line_index": syllable.line_index,
                "occurrence": syllable.occurrence,
                "status": "unresolved",
                "note_ids": [],
                "reason_code": "no_acceptable_assignment",
                "evidence": ev.as_dict(),
            }
            mapping_rows.append(row)
            unresolved_rows.append({
                "syllable_id": sid,
                "text": syllable.text,
                "reason_code": "no_acceptable_assignment",
                "detail": "no monotone assignment stayed within the cost budget",
            })
            continue
        span = best.spans[sid]
        note_ids = [sung[i].note_id for i in range(span[0], span[1] + 1)]
        options = per_syllable[sid]
        margin = None
        if len(options) >= 2:
            margin = round(options[1][0] - options[0][0], 4)
        illegal_sustains = _illegal_sustains({sid: span}, sung)
        mapping_rows.append({
            "syllable_id": sid,
            "text": syllable.text,
            "line_index": syllable.line_index,
            "occurrence": syllable.occurrence,
            "status": "mapped",
            "note_ids": note_ids,
            "sustain_note_ids": note_ids[1:],
            "reason_code": "dp_monotonic_optimum",
            "margin": margin,
            "review_required": sid in review_syllables,
            "illegal_sustain_note_ids": illegal_sustains,
            "evidence": ev.as_dict(),
        })

    assigned_notes = {nid for row in mapping_rows for nid in row["note_ids"]}
    mapped_count = sum(1 for row in mapping_rows if row["status"] == "mapped")
    coverage = {
        "syllable_total": len(syllables),
        "syllable_mapped": mapped_count,
        "syllable_unresolved": len(syllables) - mapped_count,
        "coverage_ratio": round(mapped_count / max(1, len(syllables)), 6),
        "success_ratio_excluding_unresolved": round(mapped_count / max(1, len(syllables)), 6),
        "voiced_note_total": len(sung),
        "voiced_note_assigned": len(assigned_notes),
        "voiced_note_unassigned": len(sung) - len(assigned_notes),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "song_id": song_id,
        "mapping": mapping_rows,
        "candidates": candidates,
        "windows": window_records,
        "lines": [lines[key] for key in sorted(lines)],
        "unresolved": unresolved_rows,
        "coverage": coverage,
        "config": {
            "max_melisma": config.max_melisma,
            "time_scale_s": config.time_scale_s,
            "duration_scale_s": config.duration_scale_s,
            "melisma_cost": config.melisma_cost,
            "skip_cost": config.skip_cost,
            "unresolved_cost": config.unresolved_cost,
            "ambiguity_margin": config.ambiguity_margin,
            "window_min": config.window_min,
            "window_max": config.window_max,
        },
        "total_cost": round(best_total, 4),
    }


def mapping_to_ustx_rows(mapping: dict, notes: Sequence[NoteEvent],
                         line_index: dict[str, int] | None = None) -> list[dict]:
    """Turn the chosen mapping into rows the baseline builder can use.

    A syllable's first note carries the character; every further note of the
    same syllable becomes a ``+`` sustain block.  Notes that no syllable owns
    stay visible in ``notes_normalized.json`` as observations.
    """
    by_id = {n.note_id: n for n in notes}
    rows: list[dict] = []
    for row in mapping["mapping"]:
        if row["status"] != "mapped":
            continue
        note_ids = row["note_ids"]
        notes_by_id: dict[str, dict] = {}
        for index, note_id in enumerate(note_ids):
            note = by_id[note_id]
            notes_by_id[note_id] = {
                "start": note.start,
                "end": note.end,
                "dur": note.dur,
                "tone": note.tone,
            }
            rows.append({
                "note_id": note_id,
                "syllable_id": row["syllable_id"],
                "syllable_text": row["text"],
                "lyric": row["text"] if index == 0 else "+",
                "start": note.start,
                "end": note.end,
                "dur": note.dur,
                "tone": note.tone,
                "is_sustain": index > 0,
                "line_index": (line_index or {}).get(row["syllable_id"], row["line_index"]),
                "notes_by_id": notes_by_id,
            })
    rows.sort(key=lambda r: (r["start"], r["note_id"]))
    return rows
