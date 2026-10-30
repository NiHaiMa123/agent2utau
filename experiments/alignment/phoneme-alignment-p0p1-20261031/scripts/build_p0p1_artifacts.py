"""Build the P0/P1 artifacts for 年轮 / 最后一页 / 雨爱.

Reads the locked lyrics, the GAME note events and the HFA observations that
already exist on this machine, and writes the P0/P1 deliverables into the
run directory:

    observations/manifest.json   input bindings, clock origin, model hashes
    <song>/lyrics_locked.json    locked lyrics with stable syllable ids
    <song>/notes_normalized.json GAME events with stable note ids + ticks
    <song>/mapping.v1.json       deterministic mapping + window candidates
    <song>/anomalies.json        clock / observation / mapping anomalies
    <song>/baseline.ustx         baseline score without manual PITD
    samples/                     small windows covering the P0 sample cases
    run_summary.json             one-page index of the whole run

Nothing here touches pitch, voicing or mix, and no existing project is
modified: every file is written into the new run directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import (  # noqa: E402
    MappingConfig,
    build_locked_lyrics_document,
    load_game_notes,
    load_hfa_observations,
    load_locked_lyrics,
    match_observations,
    sha256_file,
)
from agent2utau.alignment.canonical import apply_canonical  # noqa: E402
from agent2utau.alignment.candidates import build_evidence, map_syllables_to_notes  # noqa: E402
from agent2utau.alignment.notes import build_notes_document  # noqa: E402
from agent2utau.alignment.pipeline import run_alignment, write_json  # noqa: E402
from agent2utau.alignment.validator import (  # noqa: E402
    validate_locked_lyrics,
    validate_mapping,
)

RUN_ID = "phoneme-alignment-p0p1-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID
CANONICAL_DIR = RUN_DIR / "canonical_lyrics"

SONGS = {
    "nianlun": {
        "title": "年轮",
        "lyrics_source": "runs/production/nianlun-v3-20261029/lyrics.json",
        "lyrics_kind": "nianlun_phrases",
        "verification": "baidu-baike-canon-corrected",
        "verification_note": "百度百科《年轮》词条为底本，修正 9 处 ASR 错字；未逐字经用户确认",
        "game": "runs/production/nianlun-from-scratch-20261028/observation/game.json",
        "hfa": "runs/production/nianlun-from-scratch-20261028/hfa/hfa_summary.json",
        "asr": "runs/production/nianlun-from-scratch-20261028/observation/asr.json",
        "source_audio": r"E:\data\music\年轮 - 张碧晨.flac",
        "decoded": "runs/production/nianlun-from-scratch-20261028/observation/source.wav",
        "vocals": "runs/production/nianlun-from-scratch-20261028/observation/stems/source_(vocals)_vocals_mel_band_roformer.wav",
        "accompaniment": "runs/production/nianlun-from-scratch-20261028/observation/stems/source_(other)_vocals_mel_band_roformer.wav",
        "hfa_model_sha": None,
    },
    "lastpage": {
        "title": "最后一页",
        "lyrics_source": "runs/lastpage_fresh_source_20261007/lyric_scaffold.json",
        "lyrics_kind": "lastpage_scaffold",
        "verification": "asr-corrected",
        "verification_note": "fresh ASR + Agent 词义纠正；identity_verified_by_listening=false，未逐字经用户确认",
        "game": "runs/production/zuihouyiye-from-scratch-20261027/observation/game.json",
        "hfa": "runs/production/zuihouyiye-from-scratch-20261027/hfa/hfa_summary.json",
        "asr": "runs/lastpage_fresh_source_20261007/fresh_asr.json",
        "source_audio": r"E:\data\music\江语晨+-+最后一页.mp3",
        "decoded": "runs/production/zuihouyiye-from-scratch-20261027/observation/source.wav",
        "vocals": None,
        "accompaniment": None,
        "hfa_model_sha": "478294711591bc391aed03347488df68bf2ffd1d7ec26c8ac6bdb9850d9d9f0b",
    },
    "yuai": {
        "title": "雨爱",
        "lyrics_source": "runs/production/yuai-from-source-20261014/observations/lyric-judgement.json",
        "lyrics_kind": "yuai_judgement",
        "verification": "asr-corrected",
        "verification_note": "fresh ASR + Agent 词义纠正（含英文名词义推断）；未逐字经用户确认",
        "game": "runs/production/yuai-from-source-20261014/inputs/game.json",
        "hfa": "runs/production/yuai-from-source-20261014/observations/HFA.json",
        "asr": None,
        "source_audio": r"E:\data\music\杨丞琳.2010 - Rainie & Love... 雨爱  16441\杨丞琳 - 01.雨爱.flac",
        "decoded": "runs/production/yuai-from-source-20261014/inputs/source.wav",
        "vocals": "runs/production/yuai-from-source-20261014/inputs/source_vocals.wav",
        "accompaniment": "runs/production/yuai-from-source-20261014/inputs/source_backing.wav",
        "hfa_model_sha": None,
    },
}


def load_song_lines(song_id: str, cfg: dict) -> tuple[list[str], list[dict]]:
    """Read the lyric source and return (lines, per-line metadata)."""
    path = REPO_ROOT / cfg["lyrics_source"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    kind = cfg["lyrics_kind"]
    if kind == "nianlun_phrases":
        lines = [p["hanzi"] for p in doc["phrases"]]
        meta = [{"line": i, "hanzi": p["hanzi"], "pinyin": p.get("pinyin", ""),
                 "slice": p.get("slice"), "label": p.get("label")}
                for i, p in enumerate(doc["phrases"])]
        return lines, meta
    if kind == "lastpage_scaffold":
        lines = [row["text"] for row in doc]
        meta = [{"line": row.get("line", i), "hanzi": row["text"],
                 "pinyin": " ".join(row.get("pinyin", [])),
                 "slice": [row.get("start"), row.get("end")],
                 "asr_text": (row.get("asr") or {}).get("text")}
                for i, row in enumerate(doc)]
        return lines, meta
    if kind == "yuai_judgement":
        by_line: dict[int, list[dict]] = {}
        for word in doc["words"]:
            by_line.setdefault(int(word["line"]), []).append(word)
        lines, meta = [], []
        for line_index in sorted(by_line):
            words = sorted(by_line[line_index], key=lambda w: w["syllable_index"])
            text = "".join(
                w["char"] if w.get("language") == "zh" else f" {w['char']} "
                for w in words)
            lines.append(" ".join(text.split()))
            meta.append({"line": line_index, "hanzi": "".join(w["char"] for w in words),
                         "pinyin": " ".join(str(w.get("pinyin") or "") for w in words),
                         "syllable_index": [w["syllable_index"] for w in words],
                         "tokens": [w.get("token") for w in words]})
        return lines, meta
    raise ValueError(f"unknown lyrics kind {kind}")


def normalize_yuai_hfa(song_id: str, cfg: dict, line_meta: list[dict]) -> Path:
    """Join 雨爱's token-only HFA words with the locked lyric characters."""
    hfa_path = REPO_ROOT / cfg["hfa"]
    doc = json.loads(hfa_path.read_text(encoding="utf-8"))
    times = {w["token"]: w for w in doc.get("words", [])}
    locked = json.loads((REPO_ROOT / cfg["lyrics_source"]).read_text(encoding="utf-8"))
    char_by_token = {w["token"]: w["char"] for w in locked["words"]}
    observations = []
    for line in line_meta:
        for token, char in zip(line["tokens"], [c for c in line["hanzi"]]):
            row = times.get(token)
            if row is None:
                continue
            observations.append({
                "text": char_by_token.get(token, char),
                "start": float(row["start"]),
                "end": float(row["end"]),
                "source": "hfa",
                "detail": token,
                "method": "token",
            })
    out = RUN_DIR / song_id / "hfa_observations.json"
    write_json(out, {
        "schema_version": 1,
        "song_id": song_id,
        "source": cfg["hfa"],
        "source_sha256": sha256_file(hfa_path),
        "note": "token-joined HFA words of 雨爱; times are the original recording",
        "observations": observations,
    })
    return out


def environment_block() -> dict:
    """OpenUtau / voicebank facts of this machine (read-only probe)."""
    from agent2utau.resources.config import load_config
    from agent2utau.resources.doctor import probe
    cfg = load_config()
    info = probe(cfg)
    ou = Path(cfg.get("openutau_dir", ""))
    singer = info.get("singer_loaded", {}).get("character", {})
    dsconfig = info.get("singer_loaded", {}).get("dsconfig", {})
    return {
        "openutau_version": info.get("files_found", {}).get("openutau_version"),
        "openutau_dir": str(ou),
        "core_sha256": sha256_file(ou / "OpenUtau.Core.dll") if (ou / "OpenUtau.Core.dll").is_file() else None,
        "bridge_sha256": sha256_file(ou / "a2u-bridge.exe") if (ou / "a2u-bridge.exe").is_file() else None,
        "singer_id": cfg.get("default_singer"),
        "phonemizer": singer.get("default_phonemizer"),
        "singer_subbanks": singer.get("subbanks"),
        "dsconfig": {k: dsconfig.get(k) for k in ("sample_rate", "hop_size", "speakers")},
        "singers_found": info.get("bridge", {}).get("singers_found"),
        "gpu": info.get("gpu"),
        "dotnet_version": info.get("dotnet_version"),
    }


def game_model_hashes(game_path: Path) -> dict:
    doc = json.loads(game_path.read_text(encoding="utf-8"))
    if isinstance(doc, dict) and doc.get("models"):
        return {str(k): v for k, v in doc["models"].items()}
    return {}


def build_song(song_id: str, cfg: dict, environment: dict, created_at: str) -> dict:
    """Build every P0/P1 artifact of one song."""
    song_dir = RUN_DIR / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    lines, line_meta = load_song_lines(song_id, cfg)

    # The published lyric is the authority for the characters; the recording
    # keeps its own phrasing and repetitions.
    canonical_provenance = None
    canonical_report = None
    canonical_path = CANONICAL_DIR / f"{song_id}.json"
    if canonical_path.is_file():
        canonical_doc = json.loads(canonical_path.read_text(encoding="utf-8"))
        lines, canonical_report = apply_canonical(lines, canonical_doc["lines"])
        canonical_provenance = {
            "path": str(canonical_path),
            "sha256": sha256_file(canonical_path),
            "primary_source": canonical_doc.get("primary_source"),
            "cross_check_sources": canonical_doc.get("cross_check_sources"),
            "retrieved_at": canonical_doc.get("retrieved_at"),
            "performer": canonical_doc.get("performer"),
            "credit": canonical_doc.get("credit"),
            "line_count": len(canonical_doc["lines"]),
            "character_count": sum(len(line) for line in canonical_doc["lines"]),
        }
        write_json(song_dir / "lyrics_canonical_diff.json", canonical_report.as_dict())

    verification = cfg["verification"]
    verification_note = cfg["verification_note"]
    if canonical_provenance:
        verification = "public-canonical-lyrics"
        verification_note = (
            "公开权威歌词为正文字符来源（多源交叉一致）；录音自身的分句与重复以录音为准。"
            f"原始来源 {cfg['lyrics_source']} 仅提供录音分句与 ASR 粗时间提示。"
        )

    locked_doc = build_locked_lyrics_document(
        song_id, lines,
        verification=verification,
        source=cfg["lyrics_source"],
        extra={
            "verification_note": verification_note,
            "source_sha256": sha256_file(REPO_ROOT / cfg["lyrics_source"]),
            "line_meta": line_meta,
            "canonical_lyrics": canonical_provenance,
            "canonical_diff": None if canonical_report is None else {
                "aligned_equal": canonical_report.aligned_equal,
                "substitutions": len(canonical_report.substitutions),
                "recording_only": len(canonical_report.recording_only),
                "canonical_only": len(canonical_report.canonical_only),
            },
        })
    lyrics_path = song_dir / "lyrics_locked.json"
    write_json(lyrics_path, locked_doc)
    lyrics_problems = validate_locked_lyrics(locked_doc)

    hfa_path = REPO_ROOT / cfg["hfa"]
    if cfg["lyrics_kind"] == "yuai_judgement":
        hfa_path = normalize_yuai_hfa(song_id, cfg, line_meta)

    report = run_alignment(
        lyrics_path, REPO_ROOT / cfg["game"], song_dir,
        hfa_path=hfa_path,
        asr_path=(REPO_ROOT / cfg["asr"]) if cfg.get("asr") else None,
        song_id=song_id,
        baseline_ustx=song_dir / "baseline.ustx",
        baseline_name=f"{song_id}_baseline_p0p1",
    )

    # observations manifest
    game_path = REPO_ROOT / cfg["game"]
    manifest = {
        "schema_version": 1,
        "song_id": song_id,
        "title": cfg["title"],
        "run_id": RUN_ID,
        "created_at": created_at,
        "clock": {
            "origin": "source_t0",
            "unit": "seconds",
            "note": "GAME, HFA and ASR all start at the decoded source sample 0",
            "offset_s": 0.0,
            "bpm": 120.0,
            "resolution": 480,
            "tick_rate_per_s": 960.0,
            "tempo_note": "fixed 120 BPM / 480 resolution, same grid as openutau/build.py; not an estimated BPM",
        },
        "inputs": {
            "source_audio": {
                "path": cfg["source_audio"],
                "sha256": sha256_file(cfg["source_audio"]) if Path(cfg["source_audio"]).is_file() else None,
                "role": "original recording",
            },
            "decoded_wav": {
                "path": cfg["decoded"],
                "sha256": sha256_file(REPO_ROOT / cfg["decoded"]),
                "role": "decoded source, clock origin",
            },
            "vocals": {
                "path": cfg.get("vocals"),
                "sha256": sha256_file(REPO_ROOT / cfg["vocals"]) if cfg.get("vocals") else None,
                "role": "separated vocals",
            },
            "accompaniment": {
                "path": cfg.get("accompaniment"),
                "sha256": sha256_file(REPO_ROOT / cfg["accompaniment"]) if cfg.get("accompaniment") else None,
                "role": "separated accompaniment",
            },
            "locked_lyrics": {
                "path": str(lyrics_path.relative_to(REPO_ROOT)),
                "sha256": sha256_file(lyrics_path),
                "role": "locked lyrics",
                "verification": verification,
                "verification_note": verification_note,
                "canonical_lyrics": canonical_provenance,
            },
            "game": {
                "path": cfg["game"],
                "sha256": sha256_file(game_path),
                "role": "GAME note events",
            },
            "hfa": {
                "path": str(hfa_path.relative_to(REPO_ROOT)),
                "sha256": sha256_file(hfa_path),
                "role": "original singer syllable observation",
            },
            "asr": {
                "path": cfg.get("asr"),
                "sha256": sha256_file(REPO_ROOT / cfg["asr"]) if cfg.get("asr") else None,
                "role": "ASR hint only, never a lyric source",
            },
        },
        "models": {
            "game": game_model_hashes(game_path),
            "hfa_model_sha256": cfg.get("hfa_model_sha"),
        },
        "environment": environment,
        "outputs": {
            "lyrics_locked": str(lyrics_path.relative_to(REPO_ROOT)),
            "notes_normalized": str((song_dir / "notes_normalized.json").relative_to(REPO_ROOT)),
            "mapping": str((song_dir / "mapping.v1.json").relative_to(REPO_ROOT)),
            "anomalies": str((song_dir / "anomalies.json").relative_to(REPO_ROOT)),
            "baseline_ustx": str((song_dir / "baseline.ustx").relative_to(REPO_ROOT)),
        },
        "coverage": report["coverage"],
        "problems": report["problems"] + lyrics_problems,
    }
    write_json(RUN_DIR / song_id / "observations_manifest.json", manifest)
    report["lyrics_problems"] = lyrics_problems
    report["manifest"] = str((song_dir / "observations_manifest.json").relative_to(REPO_ROOT))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at", default="2026-10-31T01:30:00+08:00")
    args = parser.parse_args()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    environment = environment_block()
    write_json(RUN_DIR / "environment.json", environment)

    reports = {}
    for song_id, cfg in SONGS.items():
        reports[song_id] = build_song(song_id, cfg, environment, args.created_at)
        print(f"{song_id}: {json.dumps(reports[song_id]['coverage'], ensure_ascii=False)}")

    summary = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "created_at": args.created_at,
        "songs": {
            song_id: {
                "coverage": report["coverage"],
                "window_count": report["window_count"],
                "candidate_count": report["candidate_count"],
                "baseline": (report.get("baseline") or {}).get("notes"),
                "problems": report["problems"],
            }
            for song_id, report in reports.items()
        },
        "environment": environment,
    }
    write_json(RUN_DIR / "run_summary.json", summary)
    print(json.dumps(summary["songs"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
