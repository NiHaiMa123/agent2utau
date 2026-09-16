"""Regressions for the unusable September 16 audition, without downloads."""
from types import SimpleNamespace
import hashlib
import numpy as np
import pytest
import soundfile as sf


def test_fcpe_unvoiced_polarity_and_native_clock(tmp_path, monkeypatch):
    import torch
    from agent2utau.analysis import f0
    path = tmp_path / "input.wav"
    sf.write(path, np.zeros(44100, np.float32), 44100)

    class FakeFcpe:
        def get_model_sr(self): return 16000
        def get_hop_size(self): return 160
        def infer(self, wav, **kw):
            assert kw["output_interp_target_length"] == 101
            assert kw["interp_uv"] is False
            hz = torch.full((1, 101, 1), 440.)
            unvoiced = torch.zeros_like(hz)
            unvoiced[:, :50] = 1
            return hz, unvoiced

    monkeypatch.setattr(f0, "_fcpe", lambda device: FakeFcpe())
    result = f0.extract_f0(path)
    assert not result["voiced"][:50].any()
    assert result["voiced"][50:].all()
    assert (result["f0_hz"][:50] == 0).all()
    assert result["times"][-1] == pytest.approx(1.0)
    assert result["frame_ms"] == pytest.approx(10.0)


def test_whisper_array_is_resampled_before_transcription(tmp_path, monkeypatch):
    from agent2utau.analysis import lyrics
    path = tmp_path / "input.wav"
    sf.write(path, np.zeros((44100 * 3, 2), np.float32), 44100)

    class FakeWhisper:
        feature_extractor = SimpleNamespace(sampling_rate=16000)
        def transcribe(self, wav, **kw):
            assert wav.ndim == 1 and len(wav) == 16000
            word = SimpleNamespace(word="春", start=0.2, end=0.8)
            seg = SimpleNamespace(start=0.2, end=0.8, text="春",
                                  words=[word], avg_logprob=-0.1)
            return iter([seg]), None

    monkeypatch.setattr(lyrics, "_model", lambda name: FakeWhisper())
    result = lyrics.transcribe(path, t0=1.0, t1=2.0)
    char = result["segments"][0]["chars"][0]
    assert char["start"] == pytest.approx(1.2)
    assert char["end"] == pytest.approx(1.8)


def test_recording_match_not_title_match(tmp_path, monkeypatch):
    from agent2utau.analysis import lyrics
    import yaml
    monkeypatch.setattr(lyrics, "_REPO_LYRICS", tmp_path)
    src = tmp_path / "年轮-other.flac"
    src.write_bytes(b"different recording")
    (tmp_path / "known.lrc").write_text("[00:01]春", encoding="utf-8")
    index = tmp_path / "index.yaml"
    index.write_text("年轮: known.lrc", encoding="utf-8")
    assert lyrics.find_lyrics(src) is None
    index.write_text(yaml.safe_dump({"recordings": [{
        "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "file": "known.lrc"}]}), encoding="utf-8")
    assert lyrics.find_lyrics(src) == (tmp_path / "known.lrc", "source-sha256")
    src.write_bytes(b"changed recording")
    assert lyrics.find_lyrics(src) is None


def test_blank_lrc_ends_singing_before_interlude(tmp_path):
    from agent2utau.analysis.align import load_lrc
    path = tmp_path / "lyrics.lrc"
    path.write_text("[00:01]春夏\n[00:03]\n[00:12]秋冬\n[00:14]\n", encoding="utf-8")
    lines = load_lrc(str(path))
    assert [(x["start"], x["end"]) for x in lines] == [(1, 3), (12, 14)]


def test_alignment_trims_silence_without_changing_lyric_order():
    from agent2utau.analysis.align import trim_aligned_chars
    ts = np.arange(0, 3, .01)
    f0 = {"times": ts, "voiced": ((ts >= 1) & (ts < 1.4)) | ((ts >= 2) & (ts < 2.4))}
    result = trim_aligned_chars([
        {"char": "春", "start": 0.0, "end": 1.5},
        {"char": "夏", "start": 1.5, "end": 3.0}], f0)
    assert [c["char"] for c in result] == ["春", "夏"]
    assert result[0]["start"] == pytest.approx(.95)
    assert result[1]["start"] == pytest.approx(1.95)
    assert result[-1]["end"] < 2.5


def test_pitch_glitch_does_not_split_a_syllable():
    from agent2utau.analysis.notes import build_notes
    ts = np.arange(0, 1, .01)
    hz = np.full(len(ts), 440.)
    hz[49:51] *= 2
    notes, _ = build_notes([{"char": "春", "start": .1, "end": .9}],
                           {"times": ts, "f0_hz": hz, "voiced": np.ones(len(ts), bool)})
    assert len(notes) == 1 and notes[0]["tone"] == 69


def test_mix_restores_quiet_vocal_and_preserves_timeline(tmp_path):
    from agent2utau.audio.mix import mix
    sr = 16000
    ts = np.arange(sr * 4) / sr
    active = (ts >= 1) & (ts < 3)
    vocal = .02 * np.sin(2 * np.pi * 440 * ts) * active
    accomp = np.column_stack([.15 * np.sin(2 * np.pi * 220 * ts)] * 2)
    reference = vocal * 8
    for name, signal in [("v", vocal), ("a", accomp), ("r", reference)]:
        sf.write(tmp_path / f"{name}.wav", signal, sr, subtype="FLOAT")
    rep = mix(tmp_path / "v.wav", tmp_path / "a.wav", tmp_path / "out.wav",
              reference_vocal=tmp_path / "r.wav")
    assert rep["vocal_gain_db"] == pytest.approx(20 * np.log10(8), abs=.1)
    assert rep["balance"]["vocal_to_accomp_after_db"] >= -3.1
    out, out_sr = sf.read(tmp_path / "out.wav")
    assert out_sr == sr and len(out) == len(ts)
    assert np.max(np.abs(out)) <= 10 ** (-1 / 20) + 1e-4
    # Intro is still accompaniment alone; no shifted singing at time zero.
    assert np.max(np.abs(out[:sr] - accomp[:sr])) < 1e-4


def test_pitch_selection_cannot_improve_by_dropping_notes():
    from agent2utau.pipeline import _better
    old = {"n_evaluated": 100, "coverage": 1., "accuracy_all_notes_100c": .8,
           "median_abs_cents": 45.}
    sparse = {"n_evaluated": 10, "coverage": .1, "accuracy_all_notes_100c": .1,
              "frac_within_100c": 1., "median_abs_cents": 0.}
    assert not _better(sparse, old)


def test_ustx_shared_endpoints_never_overlap_or_break_extenders(tmp_path):
    from agent2utau.openutau.build import build_project
    import yaml
    # These boundaries exercise opposite rounding of position and duration.
    bounds = [18.71, 18.82, 18.94, 19.42, 19.6, 19.8, 20.18]
    notes = [{"lyric": "春" if i == 0 else "+", "tone": 65,
              "start": a, "end": b, "dur": round(b - a, 4)}
             for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
    out = tmp_path / "x.ustx"
    build_project("test", [{"start_sec": bounds[0], "notes": notes}], out)
    part = yaml.safe_load(out.read_text(encoding="utf-8"))["voice_parts"][0]
    for a, b in zip(part["notes"], part["notes"][1:]):
        assert a["position"] + a["duration"] == b["position"]


def test_ustx_rejects_real_overlap(tmp_path):
    from agent2utau.openutau.build import build_project
    notes = [{"lyric": "春", "tone": 60, "start": 0., "dur": 1.},
             {"lyric": "夏", "tone": 62, "start": .5, "dur": 1.}]
    with pytest.raises(ValueError, match="Overlapping"):
        build_project("test", [{"start_sec": 0., "notes": notes}], tmp_path / "x.ustx")
