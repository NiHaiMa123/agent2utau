"""P1.2-B: does a larger search budget change the window conclusions?

``no_valid_candidate`` used to mean "the first K candidates were all
illegal", which is a statement about the search budget, not about the
constraints.  This probe re-runs the frozen songs with a much larger budget
and checks whether the per-window decisions and the legal option counts stay
the same.  A window whose conclusion depends on the budget is reported as
``search_budget_exhausted`` and must not be presented as "no solution".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import MappingConfig, build_evidence, map_syllables_to_notes  # noqa: E402
from agent2utau.alignment.lyrics import parse_locked_lyrics  # noqa: E402
from agent2utau.alignment.notes import normalize_notes  # noqa: E402
from agent2utau.alignment.observations import (  # noqa: E402
    EXACT_LEVELS,
    confirmed_note_ids,
    load_hfa_observations,
    match_observations,
)

RUN_ID = "phoneme-alignment-p1.2-20261031"
OUT = REPO_ROOT / "runs" / "production" / RUN_ID / "window_budget"

SONGS = {
    "nianlun": {
        "game": "runs/production/nianlun-from-scratch-20261028/observation/game.json",
        "hfa": "runs/production/nianlun-from-scratch-20261028/hfa/hfa_summary.json",
    },
    "lastpage": {
        "game": "runs/production/zuihouyiye-from-scratch-20261027/observation/game.json",
        "hfa": "runs/production/zuihouyiye-from-scratch-20261027/hfa/hfa_summary.json",
    },
    "yuai": {
        "game": "runs/production/yuai-from-source-20261014/inputs/game.json",
        "hfa": "runs/production/phoneme-alignment-p1.1-20261031/yuai/hfa_observations.json",
    },
}

BUDGETS = [
    {"max_paths": 60, "max_options": 8, "label": "default"},
    {"max_paths": 600, "max_options": 40, "label": "large"},
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "question": "do the window decisions depend on the search budget?",
              "songs": {}}
    for song_id, cfg in SONGS.items():
        lyrics = json.loads(
            (REPO_ROOT / "runs/production/phoneme-alignment-p1.1-20261031" / song_id /
             "lyrics_locked.json").read_text(encoding="utf-8"))
        syllables = parse_locked_lyrics([row["text"] for row in lyrics["lines"]])
        raw_notes = json.loads((REPO_ROOT / cfg["game"]).read_text(encoding="utf-8"))
        notes = normalize_notes(raw_notes["notes"] if isinstance(raw_notes, dict) else raw_notes)
        observations = load_hfa_observations(REPO_ROOT / cfg["hfa"])
        matched, _ = match_observations(observations, syllables, source="hfa")
        evidence = build_evidence(syllables, matched)
        trusted = [o for o in matched.values() if o.level in EXACT_LEVELS]
        confirmed = confirmed_note_ids(notes, trusted)

        runs = []
        for budget in BUDGETS:
            config = MappingConfig(max_paths=budget["max_paths"],
                                   max_options=budget["max_options"])
            mapping = map_syllables_to_notes(syllables, notes, evidence, config,
                                             song_id=song_id, confirmed_note_ids=confirmed)
            runs.append({
                "label": budget["label"],
                "max_paths": budget["max_paths"],
                "max_options": budget["max_options"],
                "windows": [{
                    "window_id": w["window_id"],
                    "decision": w["decision"],
                    "option_count": w["option_count"],
                    "alternative_count": w["alternative_count"],
                    "search_complete": w["search_complete"],
                    "text": w["text"],
                } for w in mapping["windows"]],
                "coverage": mapping["coverage"],
            })
        default, large = runs
        by_id = {w["window_id"]: w for w in large["windows"]}
        changed = []
        for window in default["windows"]:
            other = by_id.get(window["window_id"])
            if other is None:
                continue
            if window["decision"] != other["decision"]:
                changed.append({"window_id": window["window_id"], "text": window["text"],
                                "kind": "decision_changed",
                                "default": window, "large": other})
            elif window["option_count"] != other["option_count"]:
                changed.append({"window_id": window["window_id"], "text": window["text"],
                                "kind": "option_count_grew",
                                "default": window, "large": other})
        decisions_changed = [c for c in changed if c["kind"] == "decision_changed"]
        report["songs"][song_id] = {
            "runs": runs,
            "changed_windows": changed,
            "stable": not decisions_changed,
            "decision_stable": not decisions_changed,
            "option_count_stable": not changed,
            "note": "a decision that depends on the budget would be reported as "
                    "search_budget_exhausted; a growing option count only means the "
                    "delivered list was capped",
            "decision_counts_default": {
                decision: sum(1 for w in default["windows"] if w["decision"] == decision)
                for decision in sorted({w["decision"] for w in default["windows"]})
            },
            "decision_counts_large": {
                decision: sum(1 for w in large["windows"] if w["decision"] == decision)
                for decision in sorted({w["decision"] for w in large["windows"]})
            },
        }
        print(f"{song_id}: windows {len(default['windows'])} -> {len(large['windows'])}, "
              f"decision changed {len(decisions_changed)}, option counts changed "
              f"{len(changed) - len(decisions_changed)}, decision stable {not decisions_changed}")
    (OUT / "window_budget.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
