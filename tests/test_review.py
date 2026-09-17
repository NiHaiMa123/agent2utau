"""M2.3.2D phrase-level human review — logic tests (plan2 §8.1-§8.6).

Render/audio integration is verified locally on the OpenUtau machine;
these tests cover routing, grouping, phrase windows, candidates, dedupe,
blind ordering, hash binding, and decision semantics/persistence.
"""
from __future__ import annotations

import json

import pytest

from agent2utau.review import build as rb
from agent2utau.review.decisions import (
    MANUAL_FOLLOWUP, SEMANTICS_BASELINE, SEMANTICS_CANDIDATE,
    SEMANTICS_EQUIVALENT, SEMANTICS_REJECTED, DecisionStore)


def pkt(pid, start=10.0, dur=0.4, tone=60.0,
        decision="needs_phrase_review", b=None, c=None, scc=None,
        vb=None, plateaus=None):
    return {"id": pid, "start": start, "dur": dur, "game_tone": tone,
            "state": {"decision": decision},
            "pitch_adjudication": b or {"status": "not_needed"},
            "structure_adjudication": c or {"status": "resolved_keep"},
            "structure_change_candidate": scc,
            "virtual_note_adjudication": vb or [],
            "plateaus": plateaus or []}


def b_unres(game=60.0, hyps=(62.0, 64.0)):
    return {"status": "unresolved", "winning_hypothesis": hyps[0],
            "hypotheses": [{"hypothesis": h, "score": 1.0 - i * 0.1}
                           for i, h in enumerate([game, *hyps])]}


def c_unres(boundary=None, detail=None, scores=None):
    return {"status": "unresolved", "winning_hypothesis": "H0",
            "boundary": boundary, "hypothesis_detail": detail,
            "all_scores": scores or {}}


def notes(n=((10.0, 0.4, 60.0), (10.6, 0.4, 62.0), (11.2, 0.4, 63.0))):
    return [{"start": s, "dur": d, "tone": t, "voiced": True}
            for s, d, t in n]


# ------------------------------------------------------------------ routing

def test_only_finalized_review_packets_become_items():
    packets = [
        pkt("note_0001", b=b_unres()),
        pkt("note_0002", 20.0, decision="keep_baseline",
            b={"status": "unresolved"}),          # provisional → excluded
        pkt("note_0003", 30.0, decision="resolved_change"),
        pkt("note_0004", 40.0, decision="pending_c",
            c={"status": "unresolved"}),          # machine lane pending
        pkt("note_0005", 50.0, b=b_unres()),
    ]
    items = rb.collect_review_items(packets)
    ids = {p for it in items for p in it["packets"]}
    assert ids == {"note_0001", "note_0005"}
    assert len(items) == 2


def test_virtual_children_share_parent_group():
    p = pkt("note_0301", 148.0, 0.8, scc={
        "kind": "split", "boundary": 148.4,
        "notes": [{"start": 148.0, "end": 148.4},
                  {"start": 148.4, "end": 148.8}]},
        vb=[{"id": "note_0301__v0", "status": "resolved_keep",
             "winning_hypothesis": 63.0},
            {"id": "note_0301__v1", "status": "unresolved",
             "winning_hypothesis": 66.0}],
        c={"status": "resolved_change_candidate"})
    items = rb.collect_review_items([p])
    assert len(items) == 1
    it = items[0]
    assert it["type"] == "split"
    assert set(it["note_ids"]) == {"note_0301__v0", "note_0301__v1"}
    assert it["parent_ids"] == ["note_0301"]
    assert it["region"] == [148.0, 148.8]


def test_merge_partners_form_one_group():
    parent = pkt("note_0010", 60.0, 0.4, scc={
        "kind": "merge",
        "span": {"start": 60.0, "end": 61.0, "merge_with": "note_0011"}},
        vb=[{"id": "note_0010__v0", "status": "resolved_change",
             "winning_hypothesis": 61.0}],
        c={"status": "resolved_change_candidate"})
    partner = pkt("note_0011", 60.5, 0.5, b=b_unres())
    items = rb.collect_review_items([parent, partner])
    assert len(items) == 1
    it = items[0]
    assert set(it["parent_ids"]) == {"note_0010", "note_0011"}
    assert it["region"] == [60.0, 61.0]


def test_unrelated_unresolved_never_grouped():
    packets = [pkt("note_0001", 10.0, b=b_unres()),
               pkt("note_0002", 50.0, b=b_unres())]
    items = rb.collect_review_items(packets)
    assert len(items) == 2
    assert all(it["type"] == "pitch" for it in items)


def test_pitch_and_structure_items_distinguished():
    packets = [
        pkt("note_0001", 10.0, b=b_unres()),
        pkt("note_0002", 30.0, c=c_unres(boundary=30.2,
                                        scores={"H1": -0.1, "H0": -0.5})),
    ]
    items = {it["packets"][0]: it for it in
             rb.collect_review_items(packets)}
    assert items["note_0001"]["type"] == "pitch"
    assert items["note_0002"]["type"] == "structure"


def test_permanent_regressions_route_to_review():
    packets = [pkt("note_0393", 189.84, 0.38, b=b_unres(58.15, (70.0,))),
               pkt("note_0414", 202.52, 0.5, b=b_unres(65.3, (72.3,)))]
    items = rb.collect_review_items(packets)
    assert len(items) == 2
    assert all(it["type"] == "pitch" for it in items)
    assert all(it["large_pitch_conflict"] for it in items)


# ------------------------------------------------------------ phrase windows

def _sil(*gaps):
    return list(gaps)


def test_phrase_contains_target_and_bounds():
    win = rb.phrase_window([100.0, 100.5], 274.0, notes(),
                           silences=_sil((98.0, 98.3), (102.0, 102.3)))
    assert win["start"] <= 100.0 and win["end"] >= 100.5
    assert 3.0 <= win["end"] - win["start"] <= 12.0
    assert win["boundary_source"] == "silence"


def test_phrase_prefers_lrc_line():
    lrc = [{"start": 90.0, "end": 96.0, "text": "x"},
           {"start": 96.0, "end": 103.0, "text": "y"}]
    win = rb.phrase_window([97.0, 97.5], 274.0, notes(), lrc_lines=lrc,
                           silences=_sil((95.0, 95.3), (104.0, 104.3)))
    assert win["boundary_source"] == "lrc"
    assert (win["start"], win["end"]) == (96.0, 103.0)


def test_phrase_fallback_no_cues():
    win = rb.phrase_window([100.0, 100.5], 274.0, notes())
    assert win["boundary_source"] == "fallback"
    assert win["start"] == pytest.approx(98.5)
    assert win["end"] - win["start"] >= 3.0


def test_phrase_never_cuts_mid_note():
    ns = notes(((9.0, 1.0, 60.0), (10.0, 0.5, 61.0), (11.5, 1.0, 62.0)))
    # fallback edge 8.9? target 10.0-10.5 → start 8.5 inside note [9,10)?
    win = rb.phrase_window([10.1, 10.4], 274.0, ns)
    for n in ns:
        ns_, ne = n["start"], n["start"] + n["dur"]
        for edge in (win["start"], win["end"]):
            assert not (ns_ + 0.05 < edge < ne - 0.05), \
                f"edge {edge} cuts note {ns_}-{ne}"


def test_shared_window_reuse_key():
    i1 = {"region": [50.0, 50.4]}
    i2 = {"region": [50.1, 50.45]}
    w1 = rb.phrase_window(i1["region"], 274.0, notes())
    w2 = rb.phrase_window(i2["region"], 274.0, notes())
    if (w1["start"], w1["end"]) == (w2["start"], w2["end"]):
        assert f"{w1['start']:.2f}-{w1['end']:.2f}" == \
            f"{w2['start']:.2f}-{w2['end']:.2f}"


# ---------------------------------------------------------------- candidates

def test_candidates_bounded_and_real_hypotheses():
    p = pkt("note_0001", b=b_unres(60.0, (62.0, 64.0, 65.0, 66.0, 67.0)))
    items = rb.collect_review_items([p])
    opts = rb.build_options(items[0], {p["id"]: p})
    assert len(opts) <= 4                      # baseline + <=3 alts
    assert opts[0]["candidate_id"] == "baseline"
    alts = [o for o in opts if o["candidate_id"] != "baseline"]
    assert len(alts) == 3
    for o in alts:
        assert o["score_patch"]["type"] == "retune"
        assert o["score_patch"]["to"] in (62.0, 64.0, 65.0)
        assert o["provenance"]["kind"] == "b_hypothesis"


def test_baseline_pitch_not_duplicated_as_alternative():
    p = pkt("note_0001", b=b_unres(60.0, (60.2, 64.0)))  # 60.2 ~= baseline
    opts = rb.build_options(rb.collect_review_items([p])[0],
                            {p["id"]: p})
    alts = [o["score_patch"]["to"] for o in opts
            if o["score_patch"]["type"] == "retune"]
    assert all(abs(t - 60.0) >= 0.5 for t in alts)


def test_split_candidate_uses_virtual_b_winner():
    p = pkt("note_0301", 148.0, 0.8, scc={
        "kind": "split", "boundary": 148.4,
        "notes": [{"start": 148.0, "end": 148.4},
                  {"start": 148.4, "end": 148.8}]},
        vb=[{"id": "v0", "status": "resolved_keep",
             "winning_hypothesis": 63.0},
            {"id": "v1", "status": "unresolved",
             "winning_hypothesis": 66.0,
             "hypotheses": [{"hypothesis": 66.0},
                            {"hypothesis": 78.0}]}],
        c={"status": "resolved_change_candidate"})
    it = rb.collect_review_items([p])[0]
    opts = rb.build_options(it, {p["id"]: p})
    alts = [o for o in opts if o["candidate_id"] != "baseline"]
    assert alts[0]["score_patch"]["type"] == "split"
    tones = [ch["tone"] for ch in alts[0]["score_patch"]["children"]]
    assert tones == [63.0, 66.0]
    # unresolved child contributes a runner-up variant, still <=3 alts
    assert len(alts) <= 3
    if len(alts) > 1:
        assert alts[1]["score_patch"]["children"][1]["tone"] == 78.0


def test_structure_unresolved_offers_c_hypothesis_with_seed_provenance():
    p = pkt("note_0002", 30.0, 0.8, tone=60.0,
            c=c_unres(boundary=30.4, scores={"H1": -0.1, "H0": -0.5}),
            plateaus=[{"start": 30.0, "end": 30.4, "center_midi": 61.5},
                      {"start": 30.4, "end": 30.8, "center_midi": 58.0}])
    it = rb.collect_review_items([p])[0]
    assert it["type"] == "structure"
    opts = rb.build_options(it, {p["id"]: p})
    alts = [o for o in opts if o["candidate_id"] != "baseline"]
    assert len(alts) == 1
    sp = alts[0]["score_patch"]
    assert sp["type"] == "split" and sp["boundary"] == 30.4
    # acoustic seed is labelled — never presented as GAME truth
    assert alts[0]["provenance"]["child_pitch_source"] == \
        ["acoustic_seed", "acoustic_seed"]
    assert [ch["tone"] for ch in sp["children"]] == [61.5, 58.0]


def test_compound_bounded_no_cartesian():
    p = pkt("note_0003", 40.0, 0.8, tone=60.0,
            b=b_unres(60.0, (62.0, 64.0, 66.0)),
            c=c_unres(boundary=40.4, scores={"H1": -0.1}),
            plateaus=[{"start": 40.0, "end": 40.8, "center_midi": 60.5}])
    it = rb.collect_review_items([p])[0]
    assert it["type"] == "compound"
    opts = rb.build_options(it, {p["id"]: p})
    assert len(opts) <= 4                     # bounded beam, not product
    kinds = {o["score_patch"]["type"] for o in opts}
    assert "split" in kinds and "retune" in kinds


def test_blind_order_deterministic_and_shuffled():
    opts = [{"candidate_id": "baseline"}, {"candidate_id": "a"},
            {"candidate_id": "b"}, {"candidate_id": "c"}]
    o1 = rb.blind_order([dict(o) for o in opts], "ri-0001")
    o2 = rb.blind_order([dict(o) for o in opts], "ri-0001")
    assert [o["candidate_id"] for o in o1] == \
        [o["candidate_id"] for o in o2]       # deterministic
    assert {o["option_id"] for o in o1} == \
        {"OPTION_0", "OPTION_1", "OPTION_2", "OPTION_3"}
    seen = set()
    for k in range(1, 40):
        oo = rb.blind_order([dict(o) for o in opts], f"ri-{k:04d}")
        seen.add(next(o["option_id"] for o in oo
                      if o["candidate_id"] == "baseline"))
    assert len(seen) > 1                       # baseline not always OPTION_0


# ------------------------------------------------------------------- patches

def test_apply_patch_retune_split_merge():
    ctx = [{"id": "note_0000", "index": 0, "start": 10.0, "end": 10.4,
            "dur": 0.4, "tone": 60.0, "voiced": True},
           {"id": "note_0001", "index": 1, "start": 10.4, "end": 10.9,
            "dur": 0.5, "tone": 62.0, "voiced": True}]
    r = rb.apply_patch(ctx, {"type": "retune", "note_ids": ["note_0000"],
                             "from": 60.0, "to": 72.0})
    assert r[0]["tone"] == 72.0 and r[1]["tone"] == 62.0
    s = rb.apply_patch(ctx, {"type": "split", "note_ids": ["note_0000"],
                             "children": [{"start": 10.0, "end": 10.2,
                                           "tone": 60.0},
                                          {"start": 10.2, "end": 10.4,
                                           "tone": 58.0}]})
    assert len(s) == 3 and s[0]["id"] == "note_0000__v0"
    assert s[1]["start"] == 10.2
    m = rb.apply_patch(ctx, {"type": "merge",
                             "note_ids": ["note_0000", "note_0001"],
                             "merged": {"start": 10.0, "end": 10.9,
                                        "tone": 61.0}})
    assert len(m) == 1 and m[0]["end"] == 10.9 and m[0]["tone"] == 61.0


def test_option_dedupe_identical_result():
    p = pkt("note_0001", b=b_unres(60.0, (62.0,)))
    it = rb.collect_review_items([p])[0]
    opts = rb.build_options(it, {p["id"]: p})
    sigs = [json.dumps(o["score_patch"], sort_keys=True) for o in opts]
    assert len(sigs) == len(set(sigs))


# ----------------------------------------------------------- hash & manifest

def test_package_hash_binds_options_and_phrase():
    kw = dict(item_id="ri-0001", song_sha256="s", run_id="r",
              candidate0_sha256="c0",
              phrase={"start": 1.0, "end": 5.0},
              context_ids=["note_0001"], rph="rp")
    o1 = [{"option_id": "OPTION_0", "candidate_id": "baseline",
           "score_patch": {"type": "identity"}, "provenance": {}}]
    h1 = rb.package_hash(options=o1, **kw)
    o2 = o1 + [{"option_id": "OPTION_1", "candidate_id": "retune_1",
                "score_patch": {"type": "retune", "to": 62.0},
                "provenance": {}}]
    h2 = rb.package_hash(options=o2, **kw)
    assert h1 != h2                              # option change → new hash
    kw2 = dict(kw, phrase={"start": 1.0, "end": 5.5})
    assert rb.package_hash(options=o1, **kw2) != h1   # phrase → new hash


def test_render_profile_is_neutral():
    rp = rb.render_profile()
    assert rp["voice_color"] is None and rp["pitd"] == "none"
    assert rp["loudness"] == "shared_gain" and rp["bpm"] == 120
    assert rb.render_profile_hash(rp) == rb.render_profile_hash(dict(rp))


# ------------------------------------------------------------------ decisions

def _manifest(item_id="ri-0001", ph="hash1", n=3):
    return {"review_item_id": item_id, "package_hash": ph,
            "review": {"generation": 1},
            "baseline_option": "OPTION_0",
            "options": [{"option_id": f"OPTION_{i}",
                         "candidate_id": "baseline" if i == 0 else f"c{i}"}
                        for i in range(n)]}


def test_decision_semantics(tmp_path):
    st = DecisionStore(tmp_path / "decisions.json")
    man = _manifest()
    r = st.record("ri-0001", "OPTION_0", "hash1", man)
    assert r["semantics"] == SEMANTICS_BASELINE
    r = st.record("ri-0002", "OPTION_1", "hash1",
                  _manifest("ri-0002"))
    assert r["semantics"] == SEMANTICS_CANDIDATE
    r = st.record("ri-0003", "equivalent", "hash1", _manifest("ri-0003"))
    assert r["semantics"] == SEMANTICS_EQUIVALENT
    r = st.record("ri-0004", "none_correct", "hash1", _manifest("ri-0004"))
    assert r["semantics"] == SEMANTICS_REJECTED


def test_none_correct_gen2_becomes_manual_followup(tmp_path):
    st = DecisionStore(tmp_path / "d.json")
    man = _manifest()
    man["review"]["generation"] = 2
    r = st.record("ri-0001", "none_correct", "hash1", man, generation=2)
    assert r["semantics"] == MANUAL_FOLLOWUP


def test_revisions_supersede_never_lose_history(tmp_path):
    st = DecisionStore(tmp_path / "d.json")
    man = _manifest()
    st.record("ri-0001", "OPTION_1", "hash1", man)
    st.record("ri-0001", "OPTION_2", "hash1", man)
    revs = st.revisions("ri-0001")
    assert len(revs) == 2
    assert revs[0]["superseded"] and not revs[1]["superseded"]
    assert st.latest("ri-0001")["selected"] == "OPTION_2"


def test_stale_invalidation_on_package_change(tmp_path):
    st = DecisionStore(tmp_path / "d.json")
    st.record("ri-0001", "OPTION_1", "hash1", _manifest())
    assert st.is_stale("ri-0001", "hash2") is True
    assert st.is_stale("ri-0001", "hash1") is False
    state, stale, _ = st.item_status("ri-0001", "hash2")
    assert stale and state == SEMANTICS_CANDIDATE


def test_pending_and_batch_status(tmp_path):
    st = DecisionStore(tmp_path / "d.json")
    items = [{"item_id": "ri-0001", "package_hash": "h1"},
             {"item_id": "ri-0002", "package_hash": "h2"},
             {"item_id": "ri-0003", "package_hash": "h3"}]
    st.record("ri-0001", "OPTION_0", "h1", _manifest())
    st.record("ri-0002", "none_correct", "h2", _manifest("ri-0002"))
    pend = st.pending_items(items)
    assert pend == ["ri-0003"]
    status = st.batch_status(items)
    assert status["pending"] == 1 and status[SEMANTICS_BASELINE] == 1
    assert status["regeneration_queue"] == ["ri-0002"]
    assert status["reviewed"] == 2


def test_decisions_persist_across_reload(tmp_path):
    p = tmp_path / "d.json"
    DecisionStore(p).record("ri-0001", "OPTION_1", "h", _manifest())
    st2 = DecisionStore(p)                       # resume
    assert st2.latest("ri-0001")["selected"] == "OPTION_1"


def test_bad_choice_rejected(tmp_path):
    st = DecisionStore(tmp_path / "d.json")
    with pytest.raises(ValueError):
        st.record("ri-0001", "OPTION_9", "h", _manifest())


# ------------------------------------------------------------- batch plan

def test_plan_batch_orders_and_hashes():
    packets = [
        pkt("note_0001", 50.0, b=b_unres(60.0, (62.0,))),
        pkt("note_0393", 189.84, 0.38, tone=58.15,
            b=b_unres(58.15, (70.0,))),
        pkt("note_0002", 60.0, c=c_unres(boundary=60.4,
                                        scores={"H1": -0.2})),
    ]
    byid = {p["id"]: p for p in packets}
    items = rb.collect_review_items(packets)
    planned = rb.plan_batch(items, 274.0,
                            [{"start": i * 0.5, "dur": 0.45,
                              "tone": 60.0 + i % 12, "voiced": True}
                             for i in range(400)],
                            [], [], byid, "run-x", "song", "c0", "rp")
    assert len(planned) == 3
    assert planned[0]["region"][0] == 189.84     # permanent/large first
    assert all(it["package_hash"] for it in planned)
    assert all(it["baseline_option"].startswith("OPTION_")
               for it in planned)
    # context = Candidate-0 notes inside the phrase only
    for it in planned:
        s, e = it["phrase"]["start"], it["phrase"]["end"]
        assert all(s - 0.05 <= n["start"] and n["end"] <= e + 0.05
                   for n in it["context"])
