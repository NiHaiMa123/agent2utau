from agent2utau.diagnostic.consensus import (build_consensus,
                                             consensus_stats,
                                             event_as_note)


def _n(start, dur=0.3, tone=60.0):
    return {"start": start, "dur": dur, "tone": tone, "voiced": True}


def test_stable_event():
    runs = [[_n(1.000 + i * 0.005) for _ in range(1)] for i in range(5)]
    evs = build_consensus(runs)
    assert len(evs) == 1
    e = evs[0]
    assert e["stability"] == "GAME_STABLE"
    assert e["presence_rate"] == 1.0
    assert e["tone_agreement"] == 1.0
    assert e["n_members"] == 5


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
    # run 4 splits the span into two notes -> structure_varies
    runs = [[_n(1.0, dur=0.6)], [_n(1.0, dur=0.6)], [_n(1.0, dur=0.6)],
            [_n(1.0, dur=0.6)],
            [_n(1.0, dur=0.3), _n(1.3, dur=0.3)]]
    evs = build_consensus(runs)
    split_evs = [e for e in evs if e["structure_varies"]]
    assert split_evs and any(e["stability"] == "GAME_UNSTABLE"
                             for e in split_evs)


def test_two_distinct_events_not_merged():
    runs = [[_n(1.0), _n(2.0)] for _ in range(5)]
    evs = build_consensus(runs)
    assert len(evs) == 2
    assert all(e["stability"] == "GAME_STABLE" for e in evs)


def test_event_as_note_shape():
    e = build_consensus([[_n(1.0)]])[0]
    n = event_as_note(e)
    assert n["voiced"] and abs(n["start"] - 1.0) < 1e-6


def test_stats_count():
    runs = [[_n(1.0), _n(5.0)] for _ in range(5)]
    runs[4] = [_n(1.0)]  # second note absent once -> 4/5 presence
    st = consensus_stats(build_consensus(runs))
    assert st["n_events"] == 2
    assert st["GAME_STABLE"] == 1 and st["GAME_VARIABLE"] == 1
