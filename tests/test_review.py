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
    MANUAL_FOLLOWUP, PENDING_REGEN, PENDING_REVIEW, SEMANTICS_BASELINE,
    SEMANTICS_CANDIDATE, SEMANTICS_EQUIVALENT, SEMANTICS_REJECTED, STALE,
    ReviewLog, all_current_valid_decisions, current_valid_decision,
    pending_items, rebuild_state, register_package,
    regeneration_queue)


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

def test_plan_hash_binds_options_and_phrase():
    kw = dict(item_id="ri-0001", song_sha256="s", run_id="r",
              candidate0_sha256="c0",
              phrase={"start": 1.0, "end": 5.0},
              context_ids=["note_0001"], rph="rp")
    o1 = [{"option_id": "OPTION_0", "candidate_id": "baseline",
           "score_patch": {"type": "identity"}, "provenance": {}}]
    h1 = rb.plan_hash(options=o1, **kw)
    o2 = o1 + [{"option_id": "OPTION_1", "candidate_id": "retune_1",
                "score_patch": {"type": "retune", "to": 62.0},
                "provenance": {}}]
    h2 = rb.plan_hash(options=o2, **kw)
    assert h1 != h2                              # option change → new hash
    kw2 = dict(kw, phrase={"start": 1.0, "end": 5.5})
    assert rb.plan_hash(options=o1, **kw2) != h1      # phrase → new hash


# ------------------------------------------------------ audio_package_hash

_PROV = {"binaries": {"OpenUtau.exe": {"sha256": "a"}},
         "voicebank": {"singer": "YousaV1.65b", "materials": {"m.onnx": "h"}},
         "phonemizer": "zh", "impl": "d2"}
_SRC = {"original_mix": {"sha256": "s1"},
        "separated_vocal": {"sha256": "s2"}}
_WAVS = {"OPTION_0": {"wav_sha256": "w0"},
         "OPTION_1": {"wav_sha256": "w1"}}


def test_audio_package_hash_stable_same_bytes():
    a = rb.audio_package_hash("ph", _SRC, _WAVS, _PROV)
    b = rb.audio_package_hash("ph", dict(_SRC), dict(_WAVS), dict(_PROV))
    assert a == b


@pytest.mark.parametrize("field,val", [
    ("src", {"original_mix": {"sha256": "CHANGED"},
             "separated_vocal": {"sha256": "s2"}}),
    ("src", {"original_mix": {"sha256": "s1"},
             "separated_vocal": {"sha256": "CHANGED"}}),
    ("wavs", {"OPTION_0": {"wav_sha256": "CHANGED"},
              "OPTION_1": {"wav_sha256": "w1"}}),
    ("prov", {**_PROV, "voicebank": {"singer": "YousaV1.65b",
                                     "materials": {"m.onnx": "NEW"}}}),
    ("prov", {**_PROV, "binaries": {"OpenUtau.exe": {"sha256": "NEW"}}}),
    ("prov", {**_PROV, "impl": "d3"}),
])
def test_audio_package_hash_changes_on_material_change(field, val):
    base = rb.audio_package_hash("ph", _SRC, _WAVS, _PROV)
    kw = {"src": _SRC, "wavs": _WAVS, "prov": _PROV, field: val}
    assert rb.audio_package_hash("ph", kw["src"], kw["wavs"],
                                 kw["prov"]) != base


def test_audio_package_hash_plan_binding():
    a = rb.audio_package_hash("ph-a", _SRC, _WAVS, _PROV)
    b = rb.audio_package_hash("ph-b", _SRC, _WAVS, _PROV)
    assert a != b  # same audio bytes but different plan → different hash


def test_render_profile_is_neutral():
    rp = rb.render_profile()
    assert rp["voice_color"] is None and rp["pitd"] == "none"
    assert rp["loudness"] == "shared_gain" and rp["bpm"] == 120
    assert rb.render_profile_hash(rp) == rb.render_profile_hash(dict(rp))


# ------------------------------------------------------------------ decisions

def _manifest(item_id="ri-0001", aph="aph1", n=3, gen=1, state="valid"):
    return {"review_item_id": item_id, "audio_package_hash": aph,
            "plan_hash": f"ph-{item_id}", "package_state": state,
            "review": {"generation": gen}, "review_batch_id": "rb-1",
            "baseline_option": "OPTION_0",
            "options": [{"option_id": f"OPTION_{i}",
                         "candidate_id": "baseline" if i == 0 else f"c{i}",
                         "score_patch": {"type": "identity", "to": 60 + i},
                         "provenance": {"kind": "b_hypothesis"},
                         "wav": f"OPTION_{i}.wav",
                         "wav_sha256": f"w{i}",
                         "sample_rate": 44100, "frames": 100}
                        for i in range(n)],
            "source_reference": {"original_mix": {"sha256": "s1"},
                                 "separated_vocal": {"sha256": "s2"}}}


def _run(tmp_path):
    return tmp_path / "diag-x"


def _register(run, item_id, man, batch="rb-1"):
    register_package(run, item_id, batch, man,
                     manifest_path=run / "b" / item_id / "manifest.json")


def test_decision_semantics(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    man = _manifest()
    _register(run, "ri-0001", man)
    r = log.append("ri-0001", "OPTION_0", man, "rb-1")
    assert r["semantics"] == SEMANTICS_BASELINE
    r = log.append("ri-0002", "OPTION_1", _manifest("ri-0002"), "rb-1")
    assert r["semantics"] == SEMANTICS_CANDIDATE
    r = log.append("ri-0003", "equivalent", _manifest("ri-0003"), "rb-1")
    assert r["semantics"] == SEMANTICS_EQUIVALENT
    r = log.append("ri-0004", "none_correct", _manifest("ri-0004"), "rb-1")
    assert r["semantics"] == SEMANTICS_REJECTED


def test_decision_binds_audio_package_hash_with_snapshots(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    man = _manifest(aph="audio-hash-x")
    r = log.append("ri-0001", "OPTION_2", man, "rb-1")
    assert r["audio_package_hash"] == "audio-hash-x"
    assert r["plan_hash"] == "ph-ri-0001"
    assert r["selected_option_id"] == "OPTION_2"
    assert r["selected_score_patch"] == {"type": "identity", "to": 62}
    assert r["selected_provenance"] == {"kind": "b_hypothesis"}
    assert r["selected_wav_sha256"] == "w2"
    assert r["revision_id"] and r["batch_id"] == "rb-1"


def test_unrendered_package_cannot_be_decided(tmp_path):
    man = _manifest()
    man["audio_package_hash"] = None
    man["package_state"] = "unrendered"
    with pytest.raises(ValueError):
        ReviewLog(_run(tmp_path)).append("ri-0001", "OPTION_0", man, "b")


def test_none_correct_gen2_becomes_manual_followup(tmp_path):
    log = ReviewLog(_run(tmp_path))
    r = log.append("ri-0001", "none_correct", _manifest(gen=2), "rb-2")
    assert r["semantics"] == MANUAL_FOLLOWUP


def test_revisions_supersede_never_lose_history(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    man = _manifest()
    log.append("ri-0001", "OPTION_1", man, "rb-1")
    r2 = log.append("ri-0001", "OPTION_2", man, "rb-1")
    revs = log.revisions("ri-0001")
    assert len(revs) == 2
    assert revs[0]["superseded"] and not revs[1]["superseded"]
    assert r2["supersedes_revision_id"] == revs[0]["revision_id"]
    assert log.latest("ri-0001")["selected"] == "OPTION_2"


def test_cross_generation_authoritative_state(tmp_path):
    """gen1 reject → gen2 package → gen2 select: the canonical latest is
    the gen2 decision; gen1 revision stays as audit (§6.2)."""
    run = _run(tmp_path)
    log = ReviewLog(run)
    g1 = _manifest(aph="aph-gen1")
    _register(run, "ri-0003", g1, batch="rb-1")
    log.append("ri-0003", "none_correct", g1, "rb-1")
    st = rebuild_state(run)["items"]["ri-0003"]
    assert st["status"] == PENDING_REGEN
    assert regeneration_queue(run) == ["ri-0003"]
    # gen2 package created (new audio hash) → pending_review again;
    # the gen1 rejection is stale vs the new package but stays audit
    g2 = _manifest(aph="aph-gen2", gen=2)
    _register(run, "ri-0003", g2, batch="rb-1-g2")
    st = rebuild_state(run)["items"]["ri-0003"]
    assert st["status"] == PENDING_REVIEW
    assert st["latest_revision"]["semantics"] == SEMANTICS_REJECTED
    log.append("ri-0003", "OPTION_1", g2, "rb-1-g2")
    st = rebuild_state(run)["items"]["ri-0003"]
    assert st["status"] == SEMANTICS_CANDIDATE
    assert st["latest_revision"]["audio_package_hash"] == "aph-gen2"
    revs = log.revisions("ri-0003")
    assert len(revs) == 2 and revs[0]["superseded"]   # audit preserved


def test_other_items_survive_single_item_gen2_batch(tmp_path):
    """45 decided items must not lose state when a 1-item gen2 batch is
    created (§7.4 item 43) — the run-level store is authoritative."""
    run = _run(tmp_path)
    log = ReviewLog(run)
    for i in range(2):                                # gen1 batch decides two
        man = _manifest(f"ri-{i:04d}", aph=f"a{i}")
        _register(run, f"ri-{i:04d}", man)
        log.append(f"ri-{i:04d}", "OPTION_0", man, "rb-1")
    g1 = _manifest("ri-0002", aph="a2")               # third item rejected
    _register(run, "ri-0002", g1)
    log.append("ri-0002", "none_correct", g1, "rb-1")
    _register(run, "ri-0002", _manifest("ri-0002", aph="a2g2", gen=2),
              batch="rb-1-g2")                        # 1-item gen2 batch
    valids = all_current_valid_decisions(run)
    assert set(valids) == {"ri-0000", "ri-0001"}      # decided, non-stale
    assert current_valid_decision(run, "ri-0002") is None  # gen2 pending
    assert pending_items(run) == ["ri-0002"]


def test_stale_decision_not_in_valid_set(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    man = _manifest(aph="old")
    _register(run, "ri-0001", man)
    log.append("ri-0001", "OPTION_1", man, "rb-1")
    # package regenerated — audio changed → old decision stale
    _register(run, "ri-0001", _manifest(aph="new"))
    st = rebuild_state(run)["items"]["ri-0001"]
    assert st["status"] == STALE
    assert current_valid_decision(run, "ri-0001") is None
    assert all_current_valid_decisions(run) == {}


def test_decision_log_survives_reload(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    _register(run, "ri-0001", _manifest())
    log.append("ri-0001", "OPTION_1", _manifest(), "rb-1")
    st = rebuild_state(run)
    # simulate crash/reload: fresh objects, same files
    log2 = ReviewLog(run)
    assert log2.latest("ri-0001")["selected"] == "OPTION_1"
    st2 = rebuild_state(run)
    assert st2["items"]["ri-0001"]["status"] == st[
        "items"]["ri-0001"]["status"]


def test_pending_and_regen_queues(tmp_path):
    run = _run(tmp_path)
    log = ReviewLog(run)
    for i, ch in enumerate(("OPTION_0", "none_correct", "equivalent")):
        man = _manifest(f"ri-{i:04d}", aph=f"a{i}")
        _register(run, f"ri-{i:04d}", man)
        log.append(f"ri-{i:04d}", ch, man, "rb-1")
    _register(run, "ri-0003", _manifest("ri-0003", aph="a3"))
    assert pending_items(run) == ["ri-0003"]
    assert regeneration_queue(run) == ["ri-0001"]
    st = rebuild_state(run)
    assert st["counts"][SEMANTICS_BASELINE] == 1
    assert st["counts"][SEMANTICS_EQUIVALENT] == 1
    assert st["reviewed"] == 2 and st["pending"] == 2


def test_bad_choice_rejected(tmp_path):
    with pytest.raises(ValueError):
        ReviewLog(_run(tmp_path)).append("ri-0001", "OPTION_9",
                                         _manifest(), "rb-1")


# ------------------------------------------------------ reviewability gate

def test_assess_package_states():
    from agent2utau.review.render import assess_package
    man = _manifest()
    assert assess_package(man) == "valid"
    bad = _manifest()
    bad["options"][1]["render_error"] = "boom"
    assert assess_package(bad) == "invalid"
    bad = _manifest()
    bad["options"][0]["wav_sha256"] = None
    assert assess_package(bad) == "invalid"
    bad = _manifest()
    bad["source_reference"]["original_mix"]["sha256"] = None
    assert assess_package(bad) == "invalid"
    bad = _manifest()
    bad["options"][1]["sample_rate"] = 22050
    assert assess_package(bad) == "invalid"
    un = _manifest()
    un["audio_package_hash"] = None
    assert assess_package(un) == "unrendered"


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
    assert all(it["plan_hash"] for it in planned)
    assert all(it["baseline_option"].startswith("OPTION_")
               for it in planned)
    # context = Candidate-0 notes inside the phrase only
    for it in planned:
        s, e = it["phrase"]["start"], it["phrase"]["end"]
        assert all(s - 0.05 <= n["start"] and n["end"] <= e + 0.05
                   for n in it["context"])
