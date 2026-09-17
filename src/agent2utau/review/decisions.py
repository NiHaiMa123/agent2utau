"""Human-review decision store (§6.11-§6.14).

Decisions are append-only revisions bound to review_item_id + exact
package_hash. A package change automatically invalidates (stales) older
decisions. The store never modifies Candidate 0 or any machine lane.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .build import REVIEW_SCHEMA

DECISIONS_NAME = "decisions.json"

# selection -> semantics (§6.13). OPTION_* resolves via the manifest's
# baseline_option mapping; the reviewer never enters pitch values.
SEMANTICS_BASELINE = "human_resolved_keep"
SEMANTICS_CANDIDATE = "human_selected_candidate"
SEMANTICS_EQUIVALENT = "human_no_preference"
SEMANTICS_REJECTED = "human_rejected_all"
MANUAL_FOLLOWUP = "manual_followup_required"

# choices accepted at the CLI other than OPTION_i
SPECIAL_CHOICES = ("equivalent", "none_correct")

MAX_GENERATION = 2

# decision states that must never enter M2.4 (§9)
REPAIR_BLOCKED = {
    SEMANTICS_EQUIVALENT,
    SEMANTICS_REJECTED,
    MANUAL_FOLLOWUP,
    "pending",
    "provisional",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DecisionStore:
    """Append-only decisions.json with revision history and staleness."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"schema": REVIEW_SCHEMA, "decisions": {}}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(self.path)  # atomic — a crash must not lose history

    def revisions(self, item_id: str) -> list[dict]:
        return self.data["decisions"].get(item_id, [])

    def latest(self, item_id: str):
        revs = [r for r in self.revisions(item_id) if not r["superseded"]]
        return revs[-1] if revs else None

    def is_stale(self, item_id: str, package_hash: str) -> bool:
        d = self.latest(item_id)
        return bool(d) and d["package_hash"] != package_hash

    def record(self, item_id, choice, package_hash, manifest,
               generation=1):
        """Append one revision; the previous active revision is superseded.

        choice: 'OPTION_i' or 'equivalent' / 'none_correct'.
        """
        revs = self.data["decisions"].setdefault(item_id, [])
        for r in revs:
            if not r["superseded"]:
                r["superseded"] = True
                r["superseded_at"] = _now()
        if choice.startswith("OPTION_"):
            opt = next((o for o in manifest["options"]
                        if o["option_id"] == choice), None)
            if opt is None:
                raise ValueError(f"unknown option {choice}")
            semantics = SEMANTICS_BASELINE \
                if opt["candidate_id"] == "baseline" else SEMANTICS_CANDIDATE
            candidate_id = opt["candidate_id"]
        elif choice == "equivalent":
            semantics, candidate_id = SEMANTICS_EQUIVALENT, "baseline"
        elif choice == "none_correct":
            semantics = MANUAL_FOLLOWUP if generation >= MAX_GENERATION \
                else SEMANTICS_REJECTED
            candidate_id = None
        else:
            raise ValueError(f"unknown choice {choice!r}")
        rev = {"selected": choice, "candidate_id": candidate_id,
               "semantics": semantics, "review_item_id": item_id,
               "package_hash": package_hash,
               "review_generation": generation,
               "created_at": _now(), "superseded": False}
        revs.append(rev)
        self.save()
        return rev

    def item_status(self, item_id, package_hash):
        """(state, stale, latest_revision). 'pending' when no decision."""
        d = self.latest(item_id)
        if d is None:
            return "pending", False, None
        stale = d["package_hash"] != package_hash
        return d["semantics"], stale, d

    def batch_status(self, items):
        """Progress summary over manifest dicts [{item_id,package_hash}]."""
        out = {"total": len(items), "pending": 0, "stale": 0,
               SEMANTICS_BASELINE: 0, SEMANTICS_CANDIDATE: 0,
               SEMANTICS_EQUIVALENT: 0, SEMANTICS_REJECTED: 0,
               MANUAL_FOLLOWUP: 0}
        regen, follow = [], []
        for it in items:
            state, stale, _ = self.item_status(
                it["item_id"], it["package_hash"])
            if stale:
                out["stale"] += 1
            if state == "pending":
                out["pending"] += 1
            else:
                out[state] = out.get(state, 0) + 1
            if state == SEMANTICS_REJECTED:
                regen.append(it["item_id"])
            if state == MANUAL_FOLLOWUP:
                follow.append(it["item_id"])
        out["regeneration_queue"] = regen
        out["manual_followup"] = follow
        out["reviewed"] = out["total"] - out["pending"]
        return out

    def pending_items(self, items):
        """Items still needing review (no decision, or stale decision)."""
        out = []
        for it in items:
            state, stale, _ = self.item_status(
                it["item_id"], it["package_hash"])
            if state == "pending" or stale:
                out.append(it["item_id"])
        return out
