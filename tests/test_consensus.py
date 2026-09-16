from agent2utau.diagnostic.consensus import (build_consensus,
                                             consensus_stats,
                                             event_as_note)


def _n(start, dur=0.3, tone=60.0):
    return {"start": start, "dur": dur, "tone": tone, "voiced": True}


def test_stable_event():
    runs = [[_n(1.000 + i * 0.005)] for i in range(5)]
    evs = build_consensus(runs)
    assert len(evs) == 1
    e = evs[0]
    assert e["stability"] == "GAME_STABLE"
    assert e["presence_rate"] == 1.0
    assert e["tone_agreement"] == 1.0
    assert e["run_note_counts"] == [1, 1, 1, 1, 1]


def test_unstable_low_presence():
    runs = [[_n(1.0)], [_n(1.02)], [], [], [_n(1.01)]]
    evs = build_consensus(runs)
    assert evs[0]["stability"] == "GAME_UNSTABLE"
    assert evs[0]["presence_rate"] == 0.6


def test_pitch_disagreement_variable():
    runs = [[_n(1.0, tone=60)], [_n(1.0, tone=60)], [_n(1.0, tone=62)],
            [_n(1.0, tone=60)], [_n(1.0, tone=60)]]
    evs = build_consensus(runs)
    assert evs[0]["stability"] == "GAME_VARIABLE"
    assert evs[0]["tone_agreement"] == 0.8


def test_split_merge_structure():
    # run 4 splits the [1.0,1.6] span into two notes: the event now has
    # run_note_counts [1,1,1,1,2] -> explicit structure disagreement
    runs = [[_n(1.0, dur=0.6)], [_n(1.0, dur=0.6)], [_n(1.0, dur=0.6)],
            [_n(1.0, dur=0.6)],
            [_n(1.0, dur=0.3), _n(1.3, dur=0.3)]]
    evs = build_consensus(runs)
    multi = [e for e in evs if 2 in e["run_note_counts"]]
    assert multi, "split notes should union into one event"
    assert all(e["structure_varies"] for e in multi)
    assert any(e["stability"] == "GAME_UNSTABLE" for e in multi)


def test_two_distinct_events_not_merged():
    runs = [[_n(1.0), _n(2.0)] for _ in range(5)]
    evs = build_consensus(runs)
    assert len(evs) == 2
    assert all(e["stability"] == "GAME_STABLE" for e in evs)


def test_fast_adjacent_notes_not_merged():
    # two 80ms-apart notes must stay distinct in every run
    runs = [[_n(1.0, dur=0.08, tone=60), _n(1.08, dur=0.08, tone=62)]
            for _ in range(4)]
    evs = build_consensus(runs)
    assert len(evs) == 2


def test_run_order_independent():
    runs = [[_n(1.0), _n(2.0, tone=61)], [_n(1.01), _n(2.02, tone=63)],
            [_n(0.99), _n(1.99, tone=61)], [], [_n(1.0)]]
    e1 = build_consensus(runs)
    e2 = build_consensus(list(reversed(runs)))
    assert len(e1) == len(e2)
    for a, b in zip(e1, e2):
        assert a["start_median"] == b["start_median"]
        # run indices permute under reversal; the multiset must not
        assert sorted(a["run_note_counts"]) == sorted(b["run_note_counts"])


def test_event_as_note_shape():
    e = build_consensus([[_n(1.0)]])[0]
    n = event_as_note(e)
    assert n["voiced"] and abs(n["start"] - 1.0) < 1e-6
    assert "tone_median" in e and "tone_mode" not in e


def test_stats_count():
    runs = [[_n(1.0), _n(5.0)] for _ in range(5)]
    runs[4] = [_n(1.0)]  # second note absent once -> 4/5 presence
    st = consensus_stats(build_consensus(runs))
    assert st["n_events"] == 2
    assert st["GAME_STABLE"] == 1 and st["GAME_VARIABLE"] == 1
