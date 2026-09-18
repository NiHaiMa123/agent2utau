"""M2.4 SAFE Repair — plan/apply tests (plan2 §7 acceptance matrix).

Pure-logic + tmp-dir file tests; real OpenUtau render is not needed —
corrected_score is a data artifact. Human-path tests build a real d3
review authority with real wav bytes so repair_authorized_decision can
pass its byte-level gate.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from agent2utau.repair import (BLOCKED_CONFLICT, BLOCKED_STRUCTURE,
                               PATCH_OK, REJECTED, apply_plan,
                               apply_repairs, build_plan,
                               corrected_score, machine_candidates,
                               validate_retune_patch)
from agent2utau.review import build as rb
from agent2utau.review.decisions import (ReviewLog, register_package)


# ------------------------------------------------------------------ fixtures

_NOTES = [{"start": 10.0, "dur": 0.4, "tone": 60.0, "voiced": True},
          {"start": 10.5, "dur": 0.5, "tone": 62.0, "voiced": True},
          {"start": 11.0, "dur": 0.4, "tone": 58.15, "voiced": True},
          {"start": 12.0, "dur": 0.5, "tone": 65.3, "voiced": True}]


def _pkt(pid, decision="keep_baseline", tone=60.0, b=None, gate=None,
         scc=None, sep=None, c_status="resolved_keep", final_clear=True):
    p = {"id": pid, "start": 10.0, "dur": 0.4, "game_tone": tone,
         "state": {"decision": decision,
                   "separation_state": "sensitive" if sep else "unknown",
                   "routing_needs": {}},
         "separation": {"separation_sensitive": bool(sep)},
         "pitch_adjudication": b or {"status": "not_needed"},
         "structure_adjudication": {"status": c_status},
         "structure_change_candidate": scc,
         "final_structure_clear": final_clear}
    if gate is not None:
        p["repair_gate"] = gate
    return p


def _machine_pkt(pid="note_0002", tone=58.15, target=70.0, **kw):
    """A frozen-finalized machine-safe retune packet."""
    kw.setdefault("decision", "repair_candidate")
    kw["b"] = {"status": "resolved_change", "winning_hypothesis": target,
               "hypotheses": [{"hypothesis": tone},
                              {"hypothesis": target}]}
    kw["gate"] = {"eligible": True, "gates": ["all"]}
    p = _pkt(pid, tone=tone, **kw)
    return p


def _mk_run(tmp_path, packets=None, notes=None):
    run = tmp_path / "diag-x"
    diag = run / "diagnostic"
    diag.mkdir(parents=True)
    (diag / "residual_triage.json").write_text(
        json.dumps(packets or []), encoding="utf-8")
    (diag / "baseline_game.json").write_text(
        json.dumps({"run_index": 3, "notes": notes or _NOTES}),
        encoding="utf-8")
    (run / "report.json").write_text(json.dumps(
        {"cache": {"source_sha256": "song-sha"}}), encoding="utf-8")
    return run


def _human_decision(run, patch, tag="h"):
    """Real rendered package + real bytes + register + decide → rev."""
    idir = run / "rb" / tag
    idir.mkdir(parents=True)
    wavs = {}
    opts = []
    for i in range(2):
        b = b"wav" + tag.encode() + bytes([i])
        (idir / f"OPTION_{i}.wav").write_bytes(b)
        h = hashlib.sha256(b).hexdigest()
        wavs[f"OPTION_{i}"] = {"wav_sha256": h}
        opts.append({"option_id": f"OPTION_{i}",
                     "candidate_id": "cand" if i == 0 else "baseline",
                     "score_patch": patch if i == 0 else
                     {"type": "identity"},
                     "provenance": {"kind": "b_hypothesis"},
                     "wav": f"OPTION_{i}.wav", "wav_sha256": h,
                     "sample_rate": 44100, "frames": 8})
    srcs = {"original_mix": {"path": "s.wav",
                             "sha256": hashlib.sha256(b"mix").hexdigest()},
            "separated_vocal": {"path": "v.wav",
                                "sha256": hashlib.sha256(b"voc").hexdigest()}}
    (idir / "s.wav").write_bytes(b"mix")
    (idir / "v.wav").write_bytes(b"voc")
    tk = hashlib.sha256(f"tk-{tag}".encode()).hexdigest()
    man = {"schema": "d3", "identity_schema": "review-target-v1",
           "review_item_id": "ri-" + tk[:16], "target_key": tk,
           "plan_hash": f"ph-{tag}", "options": opts,
           "source_reference": srcs, "render_provenance": {"impl": "t"},
           "review": {"generation": 1}, "review_batch_id": "rb-1",
           "baseline_option": "OPTION_1", "package_state": "valid"}
    man["audio_package_hash"] = rb.audio_package_hash(
        man["plan_hash"], srcs, wavs, man["render_provenance"])
    (idir / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    register_package(run, man["review_item_id"], "rb-1", man,
                     manifest_path=idir / "manifest.json")
    rev = ReviewLog(run).append(man["review_item_id"], "OPTION_0", man,
                                "rb-1")
    return rev, man


# ------------------------------------------------------------- §7.1 shape

def test_retune_patch_shape_gate():
    ok, why = validate_retune_patch(
        {"type": "retune", "note_ids": ["note_0002"], "from": 58.15,
         "to": 70.0}, _NOTES)
    assert ok
    for bad, want in [
            ({"type": "split", "note_ids": ["note_0002"],
              "children": []}, BLOCKED_STRUCTURE),
            ({"type": "merge", "note_ids": ["note_0002", "note_0003"],
              "merged": {}}, BLOCKED_STRUCTURE),
            ({"type": "insert"}, BLOCKED_STRUCTURE),
            ({"type": "delete"}, BLOCKED_STRUCTURE),
            ({"type": "boundary_shift"}, BLOCKED_STRUCTURE),
            ({"type": "pitd"}, BLOCKED_STRUCTURE),
            ({"type": "lyric"}, BLOCKED_STRUCTURE),
            ({"type": "unknown_op"}, "out_of_scope"),
            ({"type": "retune", "note_ids": ["note_0002", "note_0003"],
              "to": 70.0}, "not_single_note"),
            ({"type": "retune", "note_ids": ["note_9999"], "to": 70.0},
             "note_not_in_candidate0"),
            ({"type": "retune", "note_ids": ["note_0002"], "to": 200.0},
             "tone_invalid"),
            ({"type": "retune", "note_ids": ["note_0002"],
              "to": float("nan")}, "tone_invalid"),
            ({"type": "retune", "note_ids": ["note_0002"], "to": 58.16},
             "tone_unchanged"),
            ({"type": "retune", "note_ids": ["note_0002"],
              "from": 90.0, "to": 70.0}, "patch_from_mismatch")]:
        ok, why = validate_retune_patch(bad, _NOTES)
        assert not ok and why.startswith(want), (bad, why)


# --------------------------------------------------------- §7.2 machine path

def test_machine_safe_candidate_enters():
    p = _machine_pkt()
    cands = machine_candidates([p])
    assert len(cands) == 1
    c = cands[0]
    assert c["source_type"] == "machine_safe"
    assert c["patch"] == {"type": "retune", "note_ids": ["note_0002"],
                        "from": 58.15, "to": 70.0}
    assert c["authority"]["winning_hypothesis"] == 70.0


@pytest.mark.parametrize("mut", [
    lambda p: p["pitch_adjudication"].update(status="unresolved"),
    lambda p: p["pitch_adjudication"].update(provisional=True),
    lambda p: p["pitch_adjudication"].update(invalidated_by_structure=True),
    lambda p: p["repair_gate"].update(eligible=False),
    lambda p: p.pop("repair_gate"),
    lambda p: p.update(structure_change_candidate={"kind": "split"}),
    lambda p: p.update(structure_adjudication={"status": "unresolved"},
                       final_structure_clear=False),
    lambda p: p["pitch_adjudication"].update(
        winning_hypothesis=float("nan")),
    lambda p: p["state"].update(separation_state="sensitive"),
    lambda p: p["separation"].update(separation_sensitive=True),
    lambda p: p["state"].update(decision="needs_phrase_review"),
    lambda p: p["state"].update(decision="auto_resolved"),
])
def test_machine_gate_fail_closed(mut):
    """§7.2-16..19: provisional/invalidated/unresolved-structure/
    separation-sensitive packets never enter — frozen upstream decides."""
    p = _machine_pkt()
    mut(p)
    assert machine_candidates([p]) == []


def test_no_machine_repairs_on_unresolved_run():
    """The real 年轮 run: 0 repair_candidate → 0 machine repairs (§6.12)."""
    pkts = [_pkt("note_0393", decision="needs_phrase_review"),
            _pkt("note_0414", decision="needs_phrase_review"),
            _pkt("note_0001", decision="keep_baseline")]
    assert machine_candidates(pkts) == []


# ------------------------------------------------------------ §7.4/§7.5 apply

def test_plan_apply_end_to_end_machine(tmp_path):
    """§7.8-73: real packet → adapter → plan → apply → corrected score."""
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    assert plan["summary"] == {"eligible": 1}
    e = plan["repairs"][0]
    assert e["repair_id"].startswith("rp-") and e["note_id"] == "note_0002"
    res = apply_plan(run, plan)
    sc = res["score"]
    assert sc["notes"][2]["tone"] == 70.0          # only target tone
    assert sc["notes"][0]["tone"] == 60.0          # non-target unchanged
    assert len(sc["notes"]) == len(_NOTES)
    c0 = json.loads((run / "diagnostic" / "baseline_game.json")
                    .read_text())["notes"]
    assert c0[2]["tone"] == 58.15                  # Candidate 0 untouched
    m = res["manifest"]["repairs"][0]
    assert m["before"]["tone"] == 58.15 and m["after"]["tone"] == 70.0
    assert m["source_type"] == "machine_safe"
    assert "repair_gate" in m["authority"]


def test_zero_repairs_legal(tmp_path):
    """§7.7-72/§7.8-74: unresolved run → 0 repairs, apply still valid."""
    run = _mk_run(tmp_path, [_pkt("note_0393",
                                  decision="needs_phrase_review")])
    plan = build_plan(run)
    assert plan["repairs"] == []
    res = apply_plan(run, plan)
    assert res["score"]["notes"] == _NOTES         # identical to C0
    assert res["manifest"]["applied_repairs"] == []


def test_repair_id_deterministic_and_dedupe(tmp_path):
    """§7.5-48/49/50: same evidence → same id; identical after-tone
    repairs from two sources dedupe with provenance refs kept."""
    p1 = _machine_pkt()
    p2 = _machine_pkt(pid="note_0002")
    plan1 = build_plan(_mk_run(tmp_path / "a", [p1]))
    plan2 = build_plan(_mk_run(tmp_path / "b", [p2]),
                       run_id="diag-x")
    # same run_id + same evidence → same repair_id
    assert plan1["repairs"][0]["repair_id"] == plan2["repairs"][0]["repair_id"]


def test_conflict_same_note_different_tone_blocked(tmp_path):
    """§7.5-51/52: same note, different after-tone → blocked_conflict,
    no silent precedence."""
    p1 = _machine_pkt(target=70.0)
    # a second machine packet can't share a note id — simulate conflict
    # via a human repair on the same note with a different tone
    run = _mk_run(tmp_path, [p1])
    rev, man = _human_decision(
        run, {"type": "retune", "note_ids": ["note_0002"],
              "from": 58.15, "to": 64.0})
    plan = build_plan(run)
    by = {e["source_type"]: e for e in plan["repairs"]}
    assert by["machine_safe"]["status"] == BLOCKED_CONFLICT
    assert by["human_selected"]["status"] == BLOCKED_CONFLICT
    res = apply_plan(run, plan)
    assert res["score"]["notes"][2]["tone"] == 58.15   # nothing applied


def test_dedupe_same_after_tone(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt(target=70.0)])
    _human_decision(run, {"type": "retune", "note_ids": ["note_0002"],
                          "from": 58.15, "to": 70.0})
    plan = build_plan(run)
    st = [e["status"] for e in plan["repairs"]]
    assert st.count("eligible") == 1 and "deduped" in st
    keep = next(e for e in plan["repairs"] if e["status"] == "eligible")
    assert keep["provenance_refs"]                  # other source kept
    res = apply_plan(run, plan)
    assert res["score"]["notes"][2]["tone"] == 70.0


def test_rollback_subset_and_zero(tmp_path):
    """§7.5-54/55/56: exclude/only rebuilds from Candidate 0 — never
    derives the old tone from the corrected score."""
    pk = [_machine_pkt(pid="note_0000", tone=60.0, target=72.0),
          _machine_pkt(pid="note_0002", tone=58.15, target=70.0)]
    run = _mk_run(tmp_path, pk)
    plan = build_plan(run)
    ids = [e["repair_id"] for e in plan["repairs"]]
    res_all = apply_plan(run, plan)
    assert res_all["score"]["notes"][0]["tone"] == 72.0
    res_ex = apply_plan(run, plan, exclude=[ids[0]])
    assert res_ex["score"]["notes"][0]["tone"] == 60.0    # restored
    assert res_ex["score"]["notes"][2]["tone"] == 70.0
    res_zero = apply_plan(run, plan, only=[])
    assert res_zero["score"]["notes"] == _NOTES
    res_only = apply_plan(run, plan, only=[ids[1]])
    assert res_only["score"]["notes"][2]["tone"] == 70.0
    assert res_only["score"]["notes"][0]["tone"] == 60.0


def test_apply_twice_no_double_change(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    r1 = apply_plan(run, plan)
    r2 = apply_plan(run, plan)
    assert r1["score"]["corrected_score_sha256"] == \
        r2["score"]["corrected_score_sha256"]
    assert r2["score"]["notes"][2]["tone"] == 70.0


# --------------------------------------------------------- §7.3 human path

def test_human_selected_pitch_repair(tmp_path):
    """§7.3-32/33 + §7.8-75: the decision's selected_score_patch snapshot
    is consumed verbatim — no OPTION re-interpretation."""
    run = _mk_run(tmp_path, [_pkt("note_0002",
                                  decision="needs_phrase_review")])
    rev, man = _human_decision(
        run, {"type": "retune", "note_ids": ["note_0002"],
              "from": 58.15, "to": 70.0})
    plan = build_plan(run)
    e = next(e for e in plan["repairs"]
             if e["source_type"] == "human_selected")
    assert e["status"] == PATCH_OK
    assert e["authority"]["revision_id"] == rev["revision_id"]
    assert e["authority"]["audio_package_hash"] == \
        man["audio_package_hash"]
    res = apply_plan(run, plan)
    assert res["score"]["notes"][2]["tone"] == 70.0
    m = res["manifest"]["repairs"][0]
    assert m["authority"]["review_item_id"] == man["review_item_id"]
    assert m["authority"]["target_key"] == man["target_key"]


def test_human_structure_selection_blocked_not_dropped(tmp_path):
    """§7.3-36 + §7.8-77: a valid human split selection is preserved as
    blocked_structure — authority intact for M2.5."""
    run = _mk_run(tmp_path)
    rev, man = _human_decision(
        run, {"type": "split", "note_ids": ["note_0002"],
              "boundary": 10.2,
              "children": [{"start": 10.0, "end": 10.2, "tone": 60.0},
                           {"start": 10.2, "end": 10.4, "tone": 58.0}]})
    plan = build_plan(run)
    e = plan["repairs"][0]
    assert e["status"] == BLOCKED_STRUCTURE
    assert e["authority"]["revision_id"] == rev["revision_id"]
    res = apply_plan(run, plan)
    assert res["score"]["notes"] == _NOTES          # nothing applied


def test_human_non_candidate_never_repairs(tmp_path):
    """§7.3-25..30: only repair_authorized_decision's candidate passes."""
    run = _mk_run(tmp_path)
    # an identity patch passes the authorization gate but shape-validates
    # out_of_scope → rejected, never applied
    rev, man = _human_decision(run, {"type": "identity"}, tag="b")
    plan = build_plan(run)
    # _human_decision selects OPTION_0 = candidate slot holding identity
    # patch — semantics is human_selected_candidate only for non-baseline
    # candidates; an identity patch passes the gate but shape-validates
    # out_of_scope → rejected, never applied.
    e = plan["repairs"][0]
    assert e["status"] == REJECTED
    res = apply_plan(run, plan)
    assert res["score"]["notes"] == _NOTES


def test_stale_plan_refused_at_apply(tmp_path):
    """§7.3-37/38: superseding the human revision or changing the
    upstream artifact between plan and apply → hard refuse."""
    run = _mk_run(tmp_path)
    rev, man = _human_decision(
        run, {"type": "retune", "note_ids": ["note_0002"],
              "from": 58.15, "to": 70.0})
    plan = build_plan(run)
    # supersede the revision after planning
    ReviewLog(run).append(man["review_item_id"], "OPTION_1", man, "rb-1")
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_upstream_artifact_change_stales_plan(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    pk = run / "diagnostic" / "residual_triage.json"
    pk.write_text(pk.read_text() + " ")              # byte change
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_candidate0_change_stales_plan(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    c0 = run / "diagnostic" / "baseline_game.json"
    d = json.loads(c0.read_text())
    d["notes"][0]["tone"] = 99.0
    c0.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_plan_replan_deterministic(tmp_path):
    """§7.8-82/§6.10: re-planning identical evidence → identical content
    (plan_hash excludes created_at)."""
    run = _mk_run(tmp_path, [_machine_pkt()])
    p1 = build_plan(run)
    p2 = build_plan(run)
    assert p1["plan_hash"] == p2["plan_hash"]


# ------------------------------------------------------------- §7.6 audit

def test_manifest_audit_fields(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    rev, man = _human_decision(
        run, {"type": "retune", "note_ids": ["note_0001"],
              "from": 62.0, "to": 74.0})
    plan = build_plan(run)
    res = apply_plan(run, plan)
    m = res["manifest"]
    assert m["manifest_sha256"] and m["plan_hash"] == plan["plan_hash"]
    for e in m["repairs"]:
        assert e["before"] and e["after"]
        assert e["gates_passed"]
        assert e["source_type"] in ("machine_safe", "human_selected")
    human = next(e for e in m["repairs"]
                 if e["source_type"] == "human_selected")
    assert human["authority"]["revision_id"] == rev["revision_id"]
    assert human["authority"]["selected_wav_sha256"]


def test_permanent_regions_no_machine_repair(tmp_path):
    """§7.7-66/67: 189s/202s-style packets (extractor conflict /
    stochastic ambiguity) never produce machine repairs."""
    pk = [_pkt("note_0393", decision="needs_phrase_review",
               tone=58.15),                      # 189.84s pattern
          _pkt("note_0414", decision="needs_phrase_review",
               tone=65.3)]                       # 202.52s pattern
    run = _mk_run(tmp_path, pk)
    plan = build_plan(run)
    assert plan["repairs"] == []
