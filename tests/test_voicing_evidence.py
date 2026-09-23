"""L7 Round-A waveform voicing battery regressions.

All signals are synthetic and deterministic: the battery must separate
phonated spans (harmonic comb at context level) from non-phonated
remnants (decay-level single-bin resonance / noise) using only direct
waveform measurements, and must stay inconclusive in the gray zone.
"""
import numpy as np

from agent2utau.expression.voicing_evidence import (
    REMNANT_DROP_DB, _longest_run, span_features, span_voicing_evidence)

SR = 44100


def _tone(f0, dur, amp, sr=SR, n_harm=5, decay=None, seed=0):
    """Harmonic tone; decay=(tau_s) makes it exponentially decaying."""
    rng = np.random.RandomState(seed)
    t = np.arange(int(dur * sr)) / sr
    sig = np.zeros(len(t))
    for k in range(1, n_harm + 1):
        sig += (amp / k) * np.sin(2 * np.pi * k * f0 * t
                                  + rng.uniform(0, 6.28))
    if decay:
        sig *= np.exp(-t / decay)
    return sig


def _noise(dur, amp, sr=SR, seed=1):
    return np.random.RandomState(seed).randn(int(dur * sr)) * amp


def _ring(f0, dur, amp, sr=SR, tau=0.03):
    """Single-bin decaying resonance — the remnant model."""
    t = np.arange(int(dur * sr)) / sr
    return amp * np.sin(2 * np.pi * f0 * t) * np.exp(-t / tau)


def _scene(disp_sig, sr=SR, ref_f0=300.0):
    """1.0 s segment: [0,0.4) voiced ref tone, [0.4,0.6) disputed content,
    [0.6,1.0) low noise floor.  Returns (seg, disputed, ref_v, ref_u)."""
    v = _tone(ref_f0, 0.4, 0.2, sr)
    u = _noise(0.4, 1e-4, sr)
    seg = np.concatenate([v, disp_sig, u])
    return seg, (0.41, 0.59), (0.03, 0.38), (0.65, 0.95)


def test_phonated_disputed_span_classifies_phonated():
    disp = _tone(415.0, 0.2, 0.15)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=ru, claimed_f0_hz=415.0)
    assert ev["classification"] == "phonated"
    assert ev["consistent_with"] == "claimed"
    assert ev["energy_drop_db"] <= 12.0


def test_decay_ring_is_inconclusive_when_periodicity_survives():
    # A passive single-bin ring is low-energy, but its ACF can remain
    # strongly periodic at exactly the claimed f0.  Waveform evidence
    # alone cannot then prove "no phonated source"; fail closed.
    disp = _ring(417.0, 0.2, 0.002)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=ru, claimed_f0_hz=417.0)
    assert ev["classification"] == "inconclusive"
    assert ev["energy_drop_db"] >= REMNANT_DROP_DB
    assert ev["measured_f0_n_reliable"] > 0


def test_quiet_harmonic_release_is_not_mislabeled_artifact():
    # A genuinely voiced tail can be >20 dB below the earlier vowel while
    # retaining a stable F0.  Absolute h2+ dBFS must not erase it.
    disp = _tone(415.0, 0.2, 0.012)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=ru, claimed_f0_hz=415.0)
    assert ev["energy_drop_db"] >= REMNANT_DROP_DB
    assert ev["classification"] == "phonated"
    assert ev["consistent_with"] == "claimed"
    assert ev["periodic_fraction"] >= 0.5


def test_low_noise_span_is_non_phonated():
    disp = _noise(0.2, 3e-4)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=ru, claimed_f0_hz=400.0)
    assert ev["classification"] == "non_phonated_remnant"


def test_moderate_drop_with_comb_is_inconclusive():
    # 13 dB below the reference but still combed: the gray zone must
    # NOT be forced into either positive verdict
    disp = _tone(400.0, 0.2, 0.045)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=ru, claimed_f0_hz=400.0)
    assert ev["classification"] == "inconclusive"


def test_missing_unvoiced_ref_with_periodic_ring_stays_inconclusive():
    disp = _ring(256.0, 0.2, 0.002)
    seg, ds, rv, ru = _scene(disp)
    ev = span_voicing_evidence(seg, SR, disputed=ds, ref_voiced=rv,
                             ref_unvoiced=None, claimed_f0_hz=256.0)
    assert ev["classification"] == "inconclusive"
    assert ev["h2p_drop_db"] >= 18.0


def test_short_disputed_span_inconclusive():
    seg, ds, rv, ru = _scene(_noise(0.2, 1e-3))
    ev = span_voicing_evidence(seg, SR, disputed=(0.50, 0.51),
                               ref_voiced=rv, ref_unvoiced=ru)
    assert ev["classification"] == "inconclusive"


def test_span_features_measurements_present():
    seg = _tone(300.0, 0.15, 0.2)
    f = span_features(seg, SR, claimed_f0_hz=300.0)
    assert f["acf_med"] > 0.8
    assert f["h2p_max_dbfs"] > -40.0
    assert abs(f["f0_best_med_hz"] - 300.0) < 5.0


def test_longest_run_picks_longest():
    g = np.arange(0.0, 1.0, 0.01)
    m = ((g >= 0.10) & (g <= 0.15)) | ((g >= 0.50) & (g <= 0.80))
    a, b = _longest_run(m, g)
    assert abs(a - 0.50) < 1e-6 and abs(b - 0.81) < 0.011
