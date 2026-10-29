import numpy as np
import pytest

from agent2utau.expression.contour import PitchEvent
from agent2utau.expression.lowdof import (
    body_value,
    fit_body_model,
    note_core_window,
    pitd_curve,
    structural_transition,
)


def _note(start=1.0, dur=0.4, tone=60):
    return {"abs_start_s": start, "dur_s": dur, "tone": tone,
            "lyric": "a"}


def test_short_note_core_stays_inside_note():
    note = _note(dur=0.05)
    c0, c1 = note_core_window(note)
    assert note["abs_start_s"] <= c0 < c1 <= note["abs_start_s"] + 0.05


def test_body_rejects_multi_semitone_core_instead_of_clipping():
    note = _note()
    t = np.arange(0.9, 1.5, 0.01)
    y = np.full(len(t), 60 * 100 + 380.0)
    result = fit_body_model(t, y, np.ones(len(t), bool),
                            np.ones(len(t)), note)
    assert not result["reliable"]
    assert result["reason"] == "core_incompatible_with_written_note"


def test_linear_body_uses_one_coordinate_system():
    note = _note(dur=0.8)
    t = np.arange(0.9, 1.9, 0.01)
    rel = 10.0 + 100.0 * (t - 1.4)
    y = note["tone"] * 100 + rel
    result = fit_body_model(t, y, np.ones(len(t), bool),
                            np.ones(len(t)), note)
    assert result["reliable"]
    assert result["model"] == "linear"
    assert abs(body_value(result, 1.4) - 10.0) < 3.0
    assert abs(result["linear_slope_c_s"] - 100.0) < 3.0


def test_structural_transition_uses_measured_departure_arrival():
    prev = _note(start=1.0, dur=0.4, tone=60)
    note = _note(start=1.4, dur=0.5, tone=64)
    event = PitchEvent(
        "portamento", [0, 1], 1.34, 1.46, 0.9,
        params={"from_note": 0, "to_note": 1,
                "arrival_offset_c": 20.0,
                "norm_traj": [0.0, 0.3, 1.0]},
    )
    result = structural_transition(prev, note, event)
    assert result["source_supported"]
    assert result["departure_s"] == 1.34
    assert result["arrival_s"] == 1.46
    assert result["pitch"]["data"][0]["y"] == -40
    assert result["pitch"]["data"][-1]["y"] == 2


def test_pitd_ownership_priority_wins_same_tick():
    knots = [
        {"time_s": 1.0, "value_c": -40, "owner": "body", "priority": 20},
        {"time_s": 1.0, "value_c": 15, "owner": "arrival", "priority": 50},
    ]
    curve, audit = pitd_curve(knots, part_pos_tick=0, tick_ms=1.0)
    assert curve["ys"] == [15]
    assert audit[0]["owner"] == "arrival"


def test_pitd_equal_priority_conflict_fails_closed():
    knots = [
        {"time_s": 1.0, "value_c": -40, "owner": "a", "priority": 50},
        {"time_s": 1.0, "value_c": 15, "owner": "b", "priority": 50},
    ]
    with pytest.raises(ValueError, match="conflicting PITD ownership"):
        pitd_curve(knots, part_pos_tick=0, tick_ms=1.0)
