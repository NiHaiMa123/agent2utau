"""Run-level authoritative human-review state (plan2 §6.2, P0-2).

Canonical append-only revision log at ``runs/<diag>/review/decisions.json``
plus a derived ``review_state.json`` and a ``packages.json`` index of the
current package per review item. Per-batch stores are gone — one item's
history is continuous across batches/generations, and
``latest_batch.json`` is never authoritative.

Decisions bind the post-render ``audio_package_hash`` (§6.1) — a render,
source, voicebank or option-mapping change makes old decisions stale.
The store never modifies Candidate 0 or any machine lane.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REVIEW_DIRNAME = "review"
AUDIT_DIRNAME = "review_d2_audit"    # legacy-authority snapshots (§6.3-A)
LOG_NAME = "decisions.json"          # canonical append-only revision log
STATE_NAME = "review_state.json"     # derived — rebuildable from the log
PACKAGES_NAME = "packages.json"      # item_id -> current package record
AUTH_FILES = (LOG_NAME, PACKAGES_NAME, STATE_NAME)

AUTH_SCHEMA = "d3"
IDENTITY_SCHEMA = "review-target-v1"

# selection -> semantics (§6.13/§6.2). The reviewer never enters pitches.
SEMANTICS_BASELINE = "human_resolved_keep"
SEMANTICS_CANDIDATE = "human_selected_candidate"
SEMANTICS_EQUIVALENT = "human_no_preference"
SEMANTICS_REJECTED = "human_rejected_all"
MANUAL_FOLLOWUP = "manual_followup_required"

SPECIAL_CHOICES = ("equivalent", "none_correct")
MAX_GENERATION = 2

# derived statuses (§6.2 state semantics)
PENDING_REVIEW = "pending_review"
PENDING_REGEN = "pending_regeneration"
STALE = "stale"
INVALID_PACKAGE = "invalid_package"
UNREVIEWABLE = "unrendered"

# decision states that must never enter M2.4 (§9)
REPAIR_BLOCKED = {
    SEMANTICS_EQUIVALENT, SEMANTICS_REJECTED, MANUAL_FOLLOWUP,
    PENDING_REVIEW, PENDING_REGEN, STALE, INVALID_PACKAGE,
    UNREVIEWABLE, "provisional",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def review_dir(run_dir: Path) -> Path:
    return Path(run_dir) / REVIEW_DIRNAME


# ------------------------------------------------- authority schema gate

def _meta() -> dict:
    return {"schema": AUTH_SCHEMA, "identity_schema": IDENTITY_SCHEMA}


def _auth_file_ok(path: Path):
    """None = file absent (clean); True = valid d3 authority; False =
    legacy/mixed/corrupt — must never be read as d3 authority (§6.3)."""
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return d.get("schema") == AUTH_SCHEMA and \
        d.get("identity_schema") == IDENTITY_SCHEMA


def expected_item_id(target_key: str) -> str:
    """§6.6 identity math: review_item_id must equal this exactly."""
    return "ri-" + target_key[:16]


def _id_math_ok(rec) -> bool:
    tk, iid = rec.get("target_key"), rec.get("review_item_id")
    return bool(tk) and iid == expected_item_id(tk)


def ensure_review_authority(run_dir: Path):
    """Fail-closed d2→d3 gate (§6.2/§6.3): runs BEFORE every authority
    entry point. If any existing authoritative file is non-d3,
    missing-schema, wrong identity-schema, unparseable, or the set is
    mixed-schema, the whole ``review/`` directory is archived verbatim to
    ``review_d2_audit/<snapshot>/`` and a clean d3 authority is created.

    Never maps legacy ri-NNNN ids to d3 targets, never edits the archive,
    never reuses a d2 decision for authorization. Atomicity: the rename
    removes the legacy authority in one step; fresh files are written via
    tmp+rename, so a crash can only leave an absent or a clean-partial d3
    authority — never a mixed one. Idempotent on repeat calls.
    """
    rd = review_dir(run_dir)
    if not rd.is_dir():
        return
    if all(_auth_file_ok(rd / f) is not False for f in AUTH_FILES):
        return                                   # already pure d3
    audit = Path(run_dir) / AUDIT_DIRNAME
    audit.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("snapshot-%Y%m%d-%H%M%S")
    dst, n = audit / stamp, 0
    while dst.exists():                          # never overwrite audit
        n += 1
        dst = audit / f"{stamp}-{n}"
    rd.rename(dst)
    rd.mkdir(parents=True, exist_ok=True)
    _atomic_write(rd / LOG_NAME, {**_meta(), "revisions": []})
    _atomic_write(rd / PACKAGES_NAME, {**_meta(), "items": {}})
    _atomic_write(rd / STATE_NAME, {**_meta(), "items": {}, "counts": {},
                                    "reviewed": 0, "pending": 0})


# ------------------------------------------------------------- revision log

class ReviewLog:
    """Canonical append-only decision log for one diagnostic run."""

    def __init__(self, run_dir: Path):
        ensure_review_authority(run_dir)         # schema gate first (§6.2)
        self.dir = review_dir(run_dir)
        self.path = self.dir / LOG_NAME
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {**_meta(), "revisions": []}

    def save(self):
        _atomic_write(self.path, self.data)

    def revisions(self, item_id: str | None = None) -> list[dict]:
        revs = self.data["revisions"]
        if item_id is None:
            return revs
        return [r for r in revs if r["review_item_id"] == item_id]

    def get(self, revision_id: str):
        return next((r for r in self.data["revisions"]
                     if r["revision_id"] == revision_id), None)

    def latest(self, item_id: str):
        revs = [r for r in self.revisions(item_id) if not r["superseded"]]
        return revs[-1] if revs else None

    def append(self, item_id, choice, manifest, batch_id):
        """Append one revision bound to the manifest's audio_package_hash.

        Snapshots the selected option's patch/provenance/wav (§6.3) so the
        decision is a self-contained evidence artifact for M2.4.
        """
        aph = manifest.get("audio_package_hash")
        if not aph:
            raise ValueError("package has no audio_package_hash "
                             "(unrendered or invalid — cannot review)")
        if manifest.get("review_item_id") != item_id or \
                not manifest.get("target_key"):
            raise ValueError("manifest identity mismatch: decision must "
                             "bind the package's review_item_id/target_key")
        if item_id != expected_item_id(manifest["target_key"]):
            raise ValueError(f"forged review_item_id {item_id}: "
                             "!= ri-<target_key[:16]> (§6.6)")
        revs = self.data["revisions"]
        supersedes = None
        for r in revs:
            if r["review_item_id"] == item_id and not r["superseded"]:
                r["superseded"] = True
                r["superseded_at"] = _now()
                supersedes = r["revision_id"]
        generation = manifest["review"]["generation"]
        if choice.startswith("OPTION_"):
            opt = next((o for o in manifest["options"]
                        if o["option_id"] == choice), None)
            if opt is None:
                raise ValueError(f"unknown option {choice}")
            semantics = SEMANTICS_BASELINE \
                if opt["candidate_id"] == "baseline" else SEMANTICS_CANDIDATE
            cand, patch, prov, wav = opt["candidate_id"], \
                opt["score_patch"], opt["provenance"], opt.get("wav_sha256")
        elif choice == "equivalent":
            semantics = SEMANTICS_EQUIVALENT
            cand, patch, prov, wav = "baseline", None, None, None
        elif choice == "none_correct":
            semantics = MANUAL_FOLLOWUP if generation >= MAX_GENERATION \
                else SEMANTICS_REJECTED
            cand, patch, prov, wav = None, None, None, None
        else:
            raise ValueError(f"unknown choice {choice!r}")
        rev = {
            "revision_id": f"rev-{len(revs) + 1:04d}",
            "review_item_id": item_id,
            "target_key": manifest["target_key"],
            "batch_id": batch_id,
            "review_generation": generation,
            "audio_package_hash": aph,
            "plan_hash": manifest.get("plan_hash"),
            "selected": choice,
            "selected_option_id": choice if choice.startswith("OPTION_")
            else None,
            "candidate_id": cand,
            "semantics": semantics,
            "selected_score_patch": patch,
            "selected_provenance": prov,
            "selected_wav_sha256": wav,
            "created_at": _now(),
            "supersedes_revision_id": supersedes,
            "superseded": False,
        }
        revs.append(rev)
        self.save()
        return rev


# ------------------------------------------------------------- package index

def load_packages(run_dir: Path) -> dict:
    ensure_review_authority(run_dir)
    p = review_dir(run_dir) / PACKAGES_NAME
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))["items"]
    return {}


def register_package(run_dir: Path, item_id, batch_id, manifest,
                     manifest_path: Path | None = None):
    """Record the item's CURRENT package (latest wins — this is an index,
    not history; the audit trail lives in the revision log).

    Collision guard (§6.4): the same review_item_id may only ever name
    the same stable target. A same-id package whose target_key differs
    is a hard error — never a silent overwrite.
    """
    ensure_review_authority(run_dir)
    tk = manifest.get("target_key")
    if not tk or manifest.get("review_item_id") != item_id:
        raise ValueError(f"package for {item_id} lacks a matching "
                         "review_item_id/target_key")
    if item_id != expected_item_id(tk):
        raise ValueError(f"forged review_item_id {item_id}: "
                         "!= ri-<target_key[:16]> (§6.6)")
    p = review_dir(run_dir) / PACKAGES_NAME
    data = {**_meta(), "items": load_packages(run_dir)}
    existing = data["items"].get(item_id)
    if existing and existing.get("target_key") not in (None, tk):
        raise ValueError(
            f"review_item_id collision: {item_id} already bound to "
            f"target {existing['target_key'][:12]}…, refusing package "
            f"for {tk[:12]}…")
    data["items"][item_id] = {
        "review_item_id": item_id,
        "target_key": tk,
        "batch_id": batch_id,
        "generation": manifest["review"]["generation"],
        "plan_hash": manifest.get("plan_hash"),
        "audio_package_hash": manifest.get("audio_package_hash"),
        "package_state": manifest.get("package_state"),
        "manifest": str(manifest_path) if manifest_path else None,
        "updated_at": _now(),
    }
    _atomic_write(p, data)


# --------------------------------------------------------- derived state

def _derive_status(pkg, decision, item_id=None):
    """§6.2 state semantics.

    rejected_all is a routing state, not a final decision: a newer-
    generation package consumes it → pending_review. A final human state
    (keep/select/equivalent/followup) whose hash no longer matches the
    current package → stale.
    """
    if pkg is not None and item_id is not None and \
            pkg.get("review_item_id") != item_id:
        pkg = None                            # forged record key binding
    if pkg is None:
        return "no_package" if decision is None else STALE
    if pkg.get("package_state") not in ("valid",):
        return UNREVIEWABLE if pkg.get("audio_package_hash") is None \
            else INVALID_PACKAGE
    if decision is None:
        return PENDING_REVIEW
    # §6.6 identity math: forged/malformed ids or a decision naming a
    # different target can never authorize — stale, never valid.
    if not (_id_math_ok(decision) and _id_math_ok(pkg)) or \
            decision["target_key"] != pkg["target_key"]:
        return STALE
    if decision["audio_package_hash"] != pkg.get("audio_package_hash"):
        if decision["semantics"] == SEMANTICS_REJECTED and \
                pkg.get("generation", 1) > decision["review_generation"]:
            return PENDING_REVIEW     # regen consumed the rejection
        return STALE
    if decision["semantics"] == SEMANTICS_REJECTED:
        return PENDING_REGEN
    return decision["semantics"]


def rebuild_state(run_dir: Path) -> dict:
    """Recompute review_state.json from log + package index (atomic)."""
    ensure_review_authority(run_dir)
    log = ReviewLog(run_dir)
    pkgs = load_packages(run_dir)
    item_ids = set(pkgs) | {r["review_item_id"]
                            for r in log.data["revisions"]}
    items = {}
    for iid in sorted(item_ids):
        d = log.latest(iid)
        pkg = pkgs.get(iid)
        items[iid] = {
            "status": _derive_status(pkg, d, iid),
            "package": pkg,
            "latest_revision": d,
            "n_revisions": len(log.revisions(iid)),
        }
    counts: dict[str, int] = {}
    for v in items.values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    state = {**_meta(), "updated_at": _now(), "items": items,
             "counts": counts,
             "reviewed": sum(1 for v in items.values()
                             if v["status"] in (SEMANTICS_BASELINE,
                                                SEMANTICS_CANDIDATE,
                                                SEMANTICS_EQUIVALENT,
                                                MANUAL_FOLLOWUP)),
             "pending": sum(1 for v in items.values()
                            if v["status"] in (PENDING_REVIEW,
                                               PENDING_REGEN, STALE))}
    _atomic_write(review_dir(run_dir) / STATE_NAME, state)
    return state


def current_valid_decision(run_dir: Path, item_id: str):
    """The item's authoritative decision — None unless it is a final,
    non-stale human state bound to the CURRENT audio_package_hash."""
    state = rebuild_state(run_dir)["items"].get(item_id)
    if not state:
        return None
    if state["status"] in (SEMANTICS_BASELINE, SEMANTICS_CANDIDATE,
                           SEMANTICS_EQUIVALENT, MANUAL_FOLLOWUP):
        return state["latest_revision"]
    return None


def all_current_valid_decisions(run_dir: Path) -> dict:
    """{item_id: revision} for every final, non-stale decision (§6.2)."""
    state = rebuild_state(run_dir)
    return {iid: v["latest_revision"] for iid, v in state["items"].items()
            if v["status"] in (SEMANTICS_BASELINE, SEMANTICS_CANDIDATE,
                               SEMANTICS_EQUIVALENT, MANUAL_FOLLOWUP)
            and v["latest_revision"]}


def pending_items(run_dir: Path) -> list[str]:
    """Items needing review action: current package undecided or stale.
    pending_regeneration items wait for a gen-2 package, not review."""
    state = rebuild_state(run_dir)
    return [iid for iid, v in state["items"].items()
            if v["status"] in (PENDING_REVIEW, STALE)]


def regeneration_queue(run_dir: Path) -> list[str]:
    state = rebuild_state(run_dir)
    return [iid for iid, v in state["items"].items()
            if v["status"] == PENDING_REGEN]
