import numpy as np

from agent2utau.expression.contour import ContourSignal, PitchEvent
from agent2utau.expression.contour_qa import event_shape_gate


def _sig(cents, source):
    cents = np.asarray(cents, dtype=float)
    n = len(cents)
    t = np.arange(n) * 0.01
    return ContourSignal(
        times=t,
        cents=cents,
        raw_cents=cents.copy(),
        voiced=np.ones(n, dtype=bool),
        confidence=np.ones(n, dtype=float),
        note_idx=np.zeros(n, dtype=int),
        phoneme_idx=None,
        source=source,
        extractor="synthetic",
        segment_id=np.zeros(n, dtype=int),
    )


def _event():
    return PitchEvent(
        "portamento", [0, 1], 0.20, 0.80, 1.0,
        params={"from_note": 0, "to_note": 1,
                "trajectory_type": "linear"},
    )


def test_edge_uncertain_scores_reliable_core_not_raw_edge():
    t = np.arange(101) * 0.01
    src = 6000.0 + 300.0 * np.clip((t - 0.20) / 0.60, 0, 1)
    # Deliberately wrong on the uncertain leading edge; identical on core.
    ren = src.copy()
    m = (t >= 0.20) & (t < 0.40)
    ren[m] = 6400.0 - 500.0 * (t[m] - 0.20)
    neu = 6000.0 + 300.0 * np.clip((t - 0.20) / 0.60, 0, 1)

    ev = _event()
    rep = event_shape_gate(
        [ev], [ev], _sig(neu, "neutral"), _sig(src, "source"),
        _sig(ren, "render"),
        source_core_bounds={
            0: {"side": "start", "reliable_core_s": [0.40, 0.80]}})

    row = rep["events"][0]
    assert row["class"] == "source_edge_uncertain"
    assert not row["blocking"]
    assert row["reliable_core_s"] == [0.4, 0.8]
    assert row["trimmed_start_ms"] == 200.0
    assert row["raw_cn_rmse_clean"] is not None
    assert row["raw_cn_rmse_clean"] > row["cn_rmse_clean"]
    assert row["cn_rmse_clean"] < 0.05


def test_edge_uncertain_does_not_hide_core_distortion():
    t = np.arange(101) * 0.01
    src = 6000.0 + 300.0 * np.clip((t - 0.20) / 0.60, 0, 1)
    ren = src.copy()
    # Core itself is wrong: hold near its start value instead of rising.
    m = (t >= 0.40) & (t <= 0.80)
    ren[m] = src[np.argmin(np.abs(t - 0.40))]
    neu = src.copy()

    ev = _event()
    rep = event_shape_gate(
        [ev], [ev], _sig(neu, "neutral"), _sig(src, "source"),
        _sig(ren, "render"),
        source_core_bounds={
            0: {"side": "start", "reliable_core_s": [0.40, 0.80]}})

    row = rep["events"][0]
    assert row["class"] == "distortion"
    assert row["blocking"]
    assert row["cn_rmse_clean"] > 0.35


def test_too_short_core_is_not_allowed_to_override_raw_window():
    t = np.arange(101) * 0.01
    src = 6000.0 + 300.0 * np.clip((t - 0.20) / 0.60, 0, 1)
    ren = src.copy()
    m = (t >= 0.20) & (t <= 0.78)
    ren[m] += 250.0
    ev = _event()

    rep = event_shape_gate(
        [ev], [ev], _sig(src, "neutral"), _sig(src, "source"),
        _sig(ren, "render"),
        source_core_bounds={
            0: {"side": "end", "reliable_core_s": [0.78, 0.80]}})

    row = rep["events"][0]
    assert row["reliable_core_s"] is None
    assert row["class"] == "distortion"
    assert row["blocking"]
