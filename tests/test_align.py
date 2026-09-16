"""Unit tests for deterministic M2 utilities (no model inference)."""

import numpy as np
import pytest

from agent2utau.analysis.align import (
    load_lrc, lyric_chars, distribute, match_blocks)
from agent2utau.analysis.notes import build_notes
from agent2utau.analysis.onsets import voiced_blocks, voiced_extent, gate_voiced
from agent2utau.openutau.build import sec_to_tick


class TestLrc:
    def test_parse(self, tmp_path):
        p = tmp_path / "x.lrc"
        p.write_text(
            "[ti:歌]\n[00:01.50]张碧晨：圆圈勾勒成指纹\n[00:05.25]印在我的嘴唇\n",
            encoding="utf-8")
        lines = load_lrc(str(p))
        assert len(lines) == 2
        assert lines[0]["start"] == pytest.approx(1.5)
        assert lines[0]["text"] == "圆圈勾勒成指纹"
        assert lines[0]["end"] == pytest.approx(5.25)
        assert lines[1]["end"] > lines[1]["start"]

    def test_chars_hanzi_only(self):
        assert lyric_chars("圆圈勾勒成指纹 印在我的嘴唇") == list(
            "圆圈勾勒成指纹印在我的嘴唇")
        assert lyric_chars("abc，。") == []


class TestDistribute:
    def test_exact_onsets(self):
        out = distribute(list("春夏秋冬"), [1.0, 1.5, 2.0, 2.5], 1.0, 3.0)
        assert [c["char"] for c in out] == list("春夏秋冬")
        assert out[0]["start"] == 1.0 and out[-1]["end"] == 3.0
        # contiguous
        for a, b in zip(out, out[1:]):
            assert a["end"] == pytest.approx(b["start"])

    def test_first_onset_pinned(self):
        # many onsets: merge must not delete the first (line start anchor)
        onsets = [1.0] + list(np.linspace(1.05, 2.9, 30))
        out = distribute(list("春夏秋冬"), onsets, 1.0, 3.0)
        assert out[0]["start"] == 1.0
        assert len(out) == 4

    def test_few_onsets_split(self):
        out = distribute(list("春夏秋冬"), [1.0, 2.0], 1.0, 3.0)
        assert len(out) == 4
        assert out[0]["start"] == 1.0 and out[-1]["end"] == 3.0

    def test_no_onsets(self):
        out = distribute(list("春夏"), [], 0.0, 2.0)
        assert len(out) == 2


def _f0(times, hz, voiced=None):
    return {"times": np.asarray(times, np.float32),
            "f0_hz": np.asarray(hz, np.float32),
            "voiced": np.asarray(voiced if voiced is not None
                                 else np.ones(len(times), bool))}


class TestNotes:
    def test_tone_from_median(self):
        ts = np.arange(0, 1.0, 0.01)
        hz = np.full(len(ts), 440.0)  # A4 = 69
        notes, last = build_notes(
            [{"char": "啊", "start": 0.1, "end": 0.5}], _f0(ts, hz))
        assert len(notes) == 1
        assert notes[0]["tone"] == 69
        assert notes[0]["lyric"] == "啊"

    def test_melisma_split(self):
        ts = np.arange(0, 1.0, 0.01)
        hz = np.where(ts < 0.5, 440.0, 660.0)  # A4 then E5 (+7st)
        notes, _ = build_notes(
            [{"char": "啊", "start": 0.05, "end": 0.95}], _f0(ts, hz))
        assert len(notes) >= 2
        assert notes[0]["lyric"] == "啊"
        assert all(n["lyric"] == "+" for n in notes[1:])
        assert notes[-1]["tone"] > notes[0]["tone"]

    def test_unvoiced_fallback(self):
        ts = np.arange(0, 1.0, 0.01)
        hz = np.zeros(len(ts))
        notes, _ = build_notes(
            [{"char": "啊", "start": 0.1, "end": 0.3}],
            _f0(ts, hz, np.zeros(len(ts), bool)), prev_tone=65)
        assert notes[0]["tone"] == 65
        assert notes[0]["conf"] == "weak"


class TestBlocks:
    def test_blocks_merge_gap(self):
        ts = np.arange(0, 5.0, 0.01)
        uv = (ts < 1.0) | ((ts > 2.0) & (ts < 3.0))
        f0 = _f0(ts, np.full(len(ts), 440.0), uv)
        bl = voiced_blocks(f0, gap=0.5, min_len=0.5)
        assert len(bl) == 2
        assert bl[0][0] == pytest.approx(0.0, abs=0.02)
        assert bl[0][1] == pytest.approx(1.0, abs=0.02)
        assert bl[1][0] == pytest.approx(2.0, abs=0.02)
        assert bl[1][1] == pytest.approx(3.0, abs=0.02)
        assert len(voiced_blocks(f0, gap=1.5)) == 1

    def test_gate(self):
        ts = np.arange(0, 1.0, 0.01)
        f0 = _f0(ts, np.full(len(ts), 440.0))
        rms = np.where(ts < 0.5, 0.2, 0.0)
        g = gate_voiced(f0, rms)
        assert g["voiced"].sum() == 50
        assert voiced_extent(g, 0.0, 1.0) is not None
        assert voiced_extent(g, 0.6, 0.9) is None

    def test_match_blocks_equal(self):
        pairs = match_blocks(["aa", "bb"], [(0, 1), (2, 3)])
        assert pairs == [(0, 0), (1, 1)]


class TestTick:
    def test_sec_to_tick_120bpm(self):
        assert sec_to_tick(0.5) == 480   # one beat at 120bpm
        assert sec_to_tick(1.0) == 960
