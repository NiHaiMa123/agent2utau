"""M2.4 SAFE Repair Engine — plan/apply split, copy-on-write on Candidate 0.

v1 scope (plan2 §6.1): single existing-note written-pitch retune ONLY.
Split/merge/insert/delete/boundary/lyric/PITD patches are never applied —
a valid human structure selection is preserved but `blocked_structure`.

Two legal inputs (§6.2):
  A. machine-safe — frozen upstream `state.decision == "repair_candidate"`
     packets only; M2.4 verifies the frozen authorization, never
     re-computes B scores/margins/thresholds.
  B. human-selected — `review.render.repair_authorized_decision()`; the
     already-reviewed `selected_score_patch` snapshot is consumed
     verbatim (no OPTION re-interpretation, no B/C re-derivation).

Candidate 0 is immutable: planning never mutates it and apply writes
only `runs/<diag>/repair/` artifacts.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPAIR_SCHEMA = "m24-2"
REPAIR_DIRNAME = "repair"
TONE_EPS_ST = 0.05        # ~5 cents: below this a "retune" is a no-op
MIDI_MIN, MIDI_MAX = 0.0, 127.0

PATCH_OK = "eligible"
BLOCKED_STRUCTURE = "blocked_structure"
BLOCKED_CONFLICT = "blocked_conflict"
REJECTED = "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _sha(obj) -> str:
    if isinstance(obj, (dict, list)):
        obj = _canon(obj).encode("utf-8")
    return hashlib.sha256(obj).hexdigest()


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def _note_index(note_id: str) -> int:
    return int(note_id.rsplit("_", 1)[1])


def _span_of(note) -> list[float]:
    return [float(note["start"]), float(note["start"]) + float(note["dur"])]


# ------------------------------------------------------------- patch shape

def validate_retune_patch(patch, notes) -> tuple[bool, str]:
    """v1 patch-shape gate (§6.3/§7.1). Returns (ok, reason).

    Legal: retune of exactly one existing Candidate-0 note — same note
    identity/span, finite in-range tone materially different from the
    baseline tone. Anything structure-shaped -> blocked_structure.
    """
    typ = (patch or {}).get("type")
    if typ in ("split", "merge", "insert", "delete", "boundary_shift",
               "move", "lyric", "pitd"):
        return False, BLOCKED_STRUCTURE
    if typ != "retune":
        return False, f"out_of_scope:{typ}"
    ids = patch.get("note_ids") or []
    if len(ids) != 1:
        return False, "not_single_note"
    try:
        idx = _note_index(ids[0])
    except (ValueError, AttributeError):
        return False, "bad_note_id"
    if not (0 <= idx < len(notes)):
        return False, "note_not_in_candidate0"
    to = patch.get("to")
    if not isinstance(to, (int, float)) or not math.isfinite(to) or \
            not (MIDI_MIN <= float(to) <= MIDI_MAX):
        return False, "tone_invalid"
    if abs(float(to) - float(notes[idx]["tone"])) < TONE_EPS_ST:
        return False, "tone_unchanged"
    frm = patch.get("from")
    if frm is not None and abs(float(frm) - float(notes[idx]["tone"])) \
            >= TONE_EPS_ST:
        return False, "patch_from_mismatch"
    return True, "ok"


# --------------------------------------------------------- machine adapter

def machine_candidates(packets) -> list[dict]:
    """Frozen-upstream adapter (§6.2-A): verify the finalized
    `repair_candidate` authorization, never re-adjudicate.

    Each entry: {source_type, note_id, patch, gate refs}. Packets whose
    frozen artifacts don't satisfy every gate are skipped — their blocker
    was already decided upstream.
    """
    out = []
    for p in packets:
        st = p.get("state") or {}
        if st.get("decision") != "repair_candidate":
            continue
        b = p.get("pitch_adjudication") or {}
        c = p.get("structure_adjudication") or {}
        gate = p.get("repair_gate") or {}
        tone = b.get("winning_hypothesis")
        ok = (
            st.get("separation_state") != "sensitive"
            and not (p.get("separation") or {}).get("separation_sensitive")
            and gate.get("eligible") is True
            and b.get("status") == "resolved_change"
            and not b.get("provisional")
            and not b.get("invalidated_by_structure")
            and b.get("status") != "invalidated"
            and p.get("structure_change_candidate") is None
            and (c.get("status") in ("resolved_keep", "not_needed")
                 or p.get("final_structure_clear"))
            and isinstance(tone, (int, float)) and math.isfinite(tone)
        )
        if not ok:
            continue
        out.append({
            "source_type": "machine_safe",
            "note_id": p["id"],
            "patch": {"type": "retune", "note_ids": [p["id"]],
                      "from": float(p["game_tone"]), "to": float(tone)},
            "authority": {
                "packet_id": p["id"],
                "b_status": b.get("status"),
                "winning_hypothesis": tone,
                "repair_gate": gate,
                "c_status": c.get("status"),
                "final_structure_clear":
                    bool(p.get("final_structure_clear")),
            },
        })
    return out


def human_candidates(run_dir: Path) -> list[dict]:
    """D-authority adapter (§6.2-B): every registered review item through
    the single repair gate. Non-candidate decisions contribute nothing —
    a valid structure selection yields a blocked_structure entry so the
    authority is preserved, not dropped (§6.3)."""
    from .review.decisions import load_packages
    from .review.render import repair_authorized_decision
    out = []
    for iid in sorted(load_packages(run_dir)):
        rev = repair_authorized_decision(run_dir, iid)
        if rev is None:
            continue
        patch = rev.get("selected_score_patch") or {}
        entry = {
            "source_type": "human_selected",
            "note_id": (patch.get("note_ids") or [None])[0],
            "patch": patch,
            "authority": {
                "review_item_id": iid,
                "target_key": rev.get("target_key"),
                "revision_id": rev["revision_id"],
                "audio_package_hash": rev["audio_package_hash"],
                "selected_option_id": rev.get("selected_option_id"),
                "selected_provenance": rev.get("selected_provenance"),
                "selected_wav_sha256": rev.get("selected_wav_sha256"),
            },
        }
        out.append(entry)
    return out


# ------------------------------------------------------------------- plan

def _repair_id(run_id, c0_sha, cand, note) -> str:
    """Stable identity (§6.5): same evidence → same repair_id. No
    timestamps — content only."""
    a = cand["authority"]
    return "rp-" + _sha({
        "schema": REPAIR_SCHEMA,
        "run_id": run_id, "candidate0_sha256": c0_sha,
        "source_type": cand["source_type"],
        "authority_id": a.get("revision_id") or a.get("packet_id"),
        "note_id": cand["note_id"],
        "before": {"start": note["start"], "end": _span_of(note)[1],
                   "tone": note["tone"]},
        "after_tone": cand["patch"].get("to"),
    })[:24]


def build_plan(run_dir: Path, *, run_id=None, packets=None, notes=None,
               triage_sha=None, song_sha256=None, write=True) -> dict:
    """Read-only planning (§6.4): collect both paths, shape-validate,
    dedupe/conflict-detect, bind upstream artifacts. Candidate 0 is
    never touched. Returns the plan dict (also written to
    runs/<diag>/repair/repair_plan.json when `write`)."""
    run_dir = Path(run_dir)
    run_id = run_id or run_dir.name
    c0_path = run_dir / "diagnostic" / "baseline_game.json"
    if packets is None or notes is None:
        diag = run_dir / "diagnostic"
        packets = json.loads((diag / "residual_triage.json")
                             .read_text(encoding="utf-8"))
        notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]
        triage_sha = _file_sha(diag / "residual_triage.json")
        if song_sha256 is None:
            rep = json.loads((run_dir / "report.json")
                             .read_text(encoding="utf-8"))
            song_sha256 = rep["cache"]["source_sha256"]
    # §6.3/§6.4-D (pre-M2.5): the plan binds BOTH the semantic notes
    # hash and the exact baseline_game.json artifact bytes — without
    # the exact artifact there is nothing to bind and NO plan may be
    # produced (fail-closed, never a sha=None plan).
    if not c0_path.exists():
        raise FileNotFoundError(
            f"{c0_path} missing — cannot bind the exact Candidate-0 "
            "artifact; refusing to build a repair plan")
    c0_sha = _sha(notes)
    c0_file_sha = _file_sha(c0_path)

    cands = machine_candidates(packets) + human_candidates(run_dir)
    entries, per_note = [], {}
    for c in cands:
        nid = c["note_id"]
        note = None
        if nid is not None:
            try:
                note = notes[_note_index(nid)]
            except (ValueError, IndexError):
                note = None
        ok, why = (False, "note_not_in_candidate0") if note is None \
            else validate_retune_patch(c["patch"], notes)
        e = {
            "repair_id": _repair_id(run_id, c0_sha, c, note)
            if note is not None else None,
            "note_id": nid, "source_type": c["source_type"],
            "patch": c["patch"], "authority": c["authority"],
            "before": {"start": note["start"], "end": _span_of(note)[1],
                       "tone": note["tone"]} if note else None,
            "after": {"start": note["start"], "end": _span_of(note)[1],
                      "tone": c["patch"].get("to")} if note else None,
            "status": PATCH_OK if ok else
            (BLOCKED_STRUCTURE if why == BLOCKED_STRUCTURE else REJECTED),
            "blocked_reason": None if ok else why,
        }
        entries.append(e)
        if nid is not None:
            per_note.setdefault(nid, []).append(e)

    # §6.6 conflict policy — no silent precedence. Same note + same after
    # tone dedupes (provenance kept); different after tone blocks ALL.
    for nid, group in per_note.items():
        elig = [e for e in group if e["status"] == PATCH_OK]
        if len(elig) <= 1:
            continue
        tones = {round(float(e["patch"]["to"]), 4) for e in elig}
        if len(tones) == 1:
            keep = elig[0]
            keep["provenance_refs"] = [e["authority"] for e in elig[1:]]
            for e in elig[1:]:
                e["status"] = "deduped"
                e["blocked_reason"] = f"duplicate_of:{keep['repair_id']}"
        else:
            for e in elig:
                e["status"] = BLOCKED_CONFLICT
                e["blocked_reason"] = "same_note_conflicting_after_tone"

    plan = {
        "schema": REPAIR_SCHEMA,
        "created_at": _now(),
        "diagnostic_run_id": run_id,
        "candidate0_sha256": c0_sha,
        "candidate0_notes_sha256": c0_sha,
        "candidate0_file_sha256": c0_file_sha,
        "song_sha256": song_sha256,
        "bindings": {
            "residual_triage_sha256": triage_sha,
            "candidate0_notes_sha256": c0_sha,
            "candidate0_file_sha256": c0_file_sha,
            "review_authority": {"schema": "d3",
                                 "identity_schema": "review-target-v1"},
            "human_revisions": {e["authority"]["review_item_id"]: {
                "revision_id": e["authority"]["revision_id"],
                "audio_package_hash": e["authority"]["audio_package_hash"],
            } for e in entries if e["source_type"] == "human_selected"},
        },
        "repairs": entries,
        "summary": {},
    }
    for e in entries:
        plan["summary"][e["status"]] = plan["summary"].get(e["status"], 0) + 1
    plan["plan_hash"] = _sha({
        "schema": plan["schema"], "run_id": run_id,
        "candidate0_sha256": c0_sha, "bindings": plan["bindings"],
        "repairs": [{k: e[k] for k in
                     ("repair_id", "note_id", "source_type", "patch",
                      "status", "blocked_reason")} for e in entries]})
    if write:
        _atomic_write(run_dir / REPAIR_DIRNAME / "repair_plan.json", plan)
    return plan


# ------------------------------------------------------------------ apply

def _eligible_entries(plan, only=None, exclude=None):
    elig = [e for e in plan["repairs"] if e["status"] == PATCH_OK]
    if only is not None:
        keep = set(only)
        elig = [e for e in elig if e["repair_id"] in keep]
    if exclude:
        drop = set(exclude)
        elig = [e for e in elig if e["repair_id"] not in drop]
    return elig


def apply_repairs(notes, entries) -> list:
    """Deterministic copy-on-write apply (§6.8): returns a NEW note list;
    `notes` is never mutated. Subset/zero repair ids rebuild correctly."""
    out = [dict(n) for n in notes]
    for e in entries:
        idx = _note_index(e["note_id"])
        out[idx] = dict(out[idx], tone=float(e["patch"]["to"]))
    return out


def corrected_score(notes, applied_ids, c0_sha,
                    c0_file_sha=None) -> dict:
    return {"schema": REPAIR_SCHEMA,
            "base_candidate0_sha256": c0_sha,
            "base_candidate0_notes_sha256": c0_sha,
            "base_candidate0_file_sha256": c0_file_sha,
            "notes": notes,
            "applied_repairs": list(applied_ids),
            "corrected_score_sha256": _sha({"notes": notes,
                                            "applied": list(applied_ids)})}


def verify_freshness(run_dir: Path, plan) -> list[str]:
    """§6.9/§6.10 — every binding must still hold at apply time."""
    from .review.render import repair_authorized_decision
    run_dir = Path(run_dir)
    stale = []
    # §6.4-D (pre-M2.5): fail-closed schema + dual-binding gate. A
    # legacy m24-1 plan (or any plan missing either Candidate-0 hash)
    # can never authorize apply — it must be regenerated, never
    # silently migrated by backfilling current hashes.
    if plan.get("schema") != REPAIR_SCHEMA:
        stale.append(f"unsupported_plan_schema:{plan.get('schema')}")
    if not plan.get("candidate0_notes_sha256"):
        stale.append("missing_candidate0_notes_sha256")
    if not plan.get("candidate0_file_sha256"):
        stale.append("missing_candidate0_file_sha256")
    diag = run_dir / "diagnostic"
    c0_path = diag / "baseline_game.json"
    if stale or not c0_path.exists():
        if not c0_path.exists():
            stale.append("candidate0_file_missing")
        return stale
    notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]
    if _sha(notes) != plan["candidate0_notes_sha256"]:
        stale.append("candidate0_notes_changed")
    if _file_sha(c0_path) != plan["candidate0_file_sha256"]:
        stale.append("candidate0_file_changed")
    if plan["bindings"].get("residual_triage_sha256") and \
            _file_sha(diag / "residual_triage.json") != \
            plan["bindings"]["residual_triage_sha256"]:
        stale.append("residual_triage_changed")
    # machine path: re-run the adapter; every applied machine repair_id
    # must still be authorized by the SAME frozen upstream artifact
    now = {e["note_id"]: e for e in machine_candidates(packets=json.loads(
        (diag / "residual_triage.json").read_text(encoding="utf-8")))}
    for e in plan["repairs"]:
        if e["status"] != PATCH_OK:
            continue
        if e["source_type"] == "machine_safe":
            cur = now.get(e["note_id"])
            if cur is None or \
                    cur["patch"].get("to") != e["patch"].get("to"):
                stale.append(f"machine_auth_changed:{e['note_id']}")
        else:
            rev = repair_authorized_decision(
                run_dir, e["authority"]["review_item_id"])
            if rev is None:
                stale.append(f"human_auth_lost:{e['authority']['review_item_id']}")
            elif rev["revision_id"] != e["authority"]["revision_id"] or \
                    rev["audio_package_hash"] != \
                    e["authority"]["audio_package_hash"] or \
                    rev.get("selected_score_patch") != e["patch"]:
                stale.append(f"human_rev_superseded:{e['authority']['review_item_id']}")
    return stale


def apply_plan(run_dir: Path, plan=None, only=None, exclude=None) -> dict:
    """Consume a verified repair_plan (§6.4/§6.9). Refuses stale plans,
    writes corrected_score.json + repair_manifest.json, and re-verifies
    integrity. Candidate 0 on disk is never written."""
    run_dir = Path(run_dir)
    if plan is None:
        plan = json.loads((run_dir / REPAIR_DIRNAME / "repair_plan.json")
                          .read_text(encoding="utf-8"))
    stale = verify_freshness(run_dir, plan)
    if stale:
        raise RuntimeError(f"repair plan stale — regenerate: {stale}")
    diag = run_dir / "diagnostic"
    c0_path = diag / "baseline_game.json"
    c0_bytes_sha = _file_sha(c0_path)
    notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]

    elig = _eligible_entries(plan, only=only, exclude=exclude)
    new_notes = apply_repairs(notes, elig)
    applied = [e["repair_id"] for e in elig]
    score = corrected_score(new_notes, applied,
                            plan["candidate0_notes_sha256"],
                            c0_file_sha=plan["candidate0_file_sha256"])

    # ---- post-apply integrity verification (§6.9): no re-adjudication
    checks = {
        "note_count_same": len(new_notes) == len(notes),
        "order_same": all(new_notes[i]["start"] == notes[i]["start"] and
                          new_notes[i]["dur"] == notes[i]["dur"]
                          for i in range(len(notes))),
        "only_target_tone_changed": True,
        "candidate0_file_unchanged": _file_sha(c0_path) == c0_bytes_sha,
    }
    touched = {_note_index(e["note_id"]) for e in elig}
    for i, (a, b) in enumerate(zip(notes, new_notes)):
        if i in touched:
            if {k: v for k, v in a.items() if k != "tone"} != \
                    {k: v for k, v in b.items() if k != "tone"}:
                checks["only_target_tone_changed"] = False
        elif a != b:
            checks["only_target_tone_changed"] = False
    if not all(checks.values()):
        raise RuntimeError(f"post-apply integrity failed: {checks}")

    rdir = run_dir / REPAIR_DIRNAME
    manifest = {
        "schema": REPAIR_SCHEMA, "created_at": _now(),
        "diagnostic_run_id": plan["diagnostic_run_id"],
        "plan_hash": plan["plan_hash"],
        "candidate0_sha256": plan["candidate0_sha256"],
        "candidate0_notes_sha256": plan.get("candidate0_notes_sha256"),
        "candidate0_file_sha256": plan.get("candidate0_file_sha256"),
        "corrected_score_sha256": score["corrected_score_sha256"],
        "applied_repairs": applied,
        "repairs": [{
            "repair_id": e["repair_id"],
            "repair_schema_version": REPAIR_SCHEMA,
            "note_id": e["note_id"], "region": e["before"],
            "before": e["before"], "after": e["after"],
            "source_type": e["source_type"],
            "authority": e["authority"],
            "provenance_refs": e.get("provenance_refs"),
            "gates_passed": ["upstream_frozen", "patch_shape",
                             "plan_freshness", "integrity"],
            "blocked_reason": e.get("blocked_reason"),
            "rollback": "rebuild from Candidate 0 + repair ids; "
                        "never derives from corrected score",
        } for e in elig],
        "integrity_checks": checks,
        "blocked": [{
            "repair_id": e["repair_id"],
            "note_id": e["note_id"],
            "source_type": e["source_type"],
            "patch_type": (e.get("patch") or {}).get("type"),
            "status": e["status"],
            "blocked_reason": e["blocked_reason"],
            "authority": e["authority"],
        } for e in plan["repairs"]
            if e["status"] not in (PATCH_OK, "deduped")],
    }
    manifest["manifest_sha256"] = _sha({k: v for k, v in manifest.items()
                                        if k not in ("manifest_sha256",
                                                     "created_at")})
    _atomic_write(rdir / "corrected_score.json", score)
    _atomic_write(rdir / "repair_manifest.json", manifest)
    return {"plan": plan, "score": score, "manifest": manifest}
