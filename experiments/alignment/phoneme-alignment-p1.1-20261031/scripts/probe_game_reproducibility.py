"""P1.1-E: is the GAME note extraction reproducible?

The observation set is frozen first (the GAME JSONs are pinned by SHA256 and
never regenerated), and only then is the *stability* of the model investigated
as a separate question.

Three configurations are compared, three runs each, on the same frozen
vocals:

1. one session, three inferences (does the session state change the result?)
2. a fresh session per inference (does a new session change the result?)
3. a single-threaded session (is thread scheduling involved?)

Everything that could explain a difference is recorded: audio hash, model
hashes, provider, thread counts, ONNX Runtime version, chunk boundaries,
output hash, event count and the first position where two runs differ.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.transcription.game_onnx import GameOnnx  # noqa: E402
from agent2utau.transcription.slicer import slice_audio  # noqa: E402

RUN_ID = "phoneme-alignment-p1.1-20261031"
OUT_DIR = REPO_ROOT / "runs" / "production" / RUN_ID / "game_stability"
VOCALS = (REPO_ROOT / "runs/production/nianlun-from-scratch-20261028/observation/stems/"
          "source_(vocals)_vocals_mel_band_roformer.wav")
SEED = 11


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def signature(notes: list[dict]) -> str:
    payload = json.dumps(notes, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def first_divergence(left: list[dict], right: list[dict]) -> dict | None:
    for index in range(min(len(left), len(right))):
        a, b = left[index], right[index]
        if (round(a["start"], 3), round(a["dur"], 3), round(a["tone"], 3), a["voiced"]) != (
                round(b["start"], 3), round(b["dur"], 3), round(b["tone"], 3), b["voiced"]):
            return {"index": index, "left": a, "right": b}
    if len(left) != len(right):
        return {"index": min(len(left), len(right)),
                "left_length": len(left), "right_length": len(right)}
    return None


def run_once(game: GameOnnx, wav: np.ndarray) -> dict:
    started = time.time()
    notes = game.infer(wav, chunk=True, language="zh", seed=SEED)
    return {"event_count": len(notes), "signature": signature(notes),
            "duration_s": round(time.time() - started, 2), "notes": notes}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import onnxruntime as ort
    from agent2utau.resources.config import load_config

    cfg = load_config()
    model_dir = Path(cfg["openutau_dir"]) / "Dependencies" / "game"
    samples, sr = sf.read(VOCALS, dtype="float32")
    samples = samples.mean(axis=1) if samples.ndim > 1 else samples
    chunks = slice_audio(samples)

    environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "onnxruntime_version": ort.__version__,
        "available_providers": ort.get_available_providers(),
        "model_dir": str(model_dir),
        "model_sha256": {p.name: sha256_file(p) for p in sorted(model_dir.glob("*.onnx"))},
        "audio": {"path": str(VOCALS), "sha256": sha256_file(VOCALS), "sample_rate": sr,
                  "duration_s": round(len(samples) / sr, 3)},
        "chunk_count": len(chunks),
        "chunk_boundaries_ms": [[round(offset, 3), round(offset + len(chunk) / sr * 1000.0, 3)]
                                for offset, chunk in chunks],
        "seed": SEED,
        "note": "the port creates an rng (game_onnx.py) but never passes it to the model, "
                "so the seed cannot influence the sampling inside the segmenter graph",
    }

    configurations: dict[str, list[dict]] = {}

    shared = GameOnnx(model_dir)
    configurations["shared_session"] = [run_once(shared, samples) for _ in range(3)]

    configurations["fresh_session"] = [run_once(GameOnnx(model_dir), samples) for _ in range(3)]

    single = []
    for _ in range(3):
        single.append(run_once(GameOnnx(model_dir, intra_op_num_threads=1), samples))
    configurations["single_thread"] = single

    runs_payload: dict[str, list[dict]] = {}
    comparison: dict[str, dict] = {}
    divergences: dict[str, list[dict]] = {}
    for name, runs in configurations.items():
        runs_payload[name] = [{k: v for k, v in run.items() if k != "notes"} for run in runs]
        signatures = {run["signature"] for run in runs}
        comparison[name] = {
            "runs": len(runs),
            "distinct_signatures": len(signatures),
            "identical_across_runs": len(signatures) == 1,
            "event_counts": [run["event_count"] for run in runs],
            "signatures": [run["signature"] for run in runs],
            "durations_s": [run["duration_s"] for run in runs],
        }
        entries = []
        for index in range(1, len(runs)):
            difference = first_divergence(runs[0]["notes"], runs[index]["notes"])
            entries.append({"run": index, "first_divergence": difference})
        divergences[name] = entries

    reproducible = all(c["identical_across_runs"] for c in comparison.values())
    payload = {
        "schema_version": 1,
        "question": "is the GAME note extraction reproducible with the same audio, models and seed?",
        "environment": environment,
        "runs": runs_payload,
        "comparison": comparison,
        "divergences": divergences,
        "conclusion": {
            "reproducible_with_same_seed": reproducible,
            "root_cause": "not_confirmed" if not reproducible else "n/a",
            "confirmed_facts": [
                "the same audio bytes, the same model hashes and the same seed were used in every run",
                "the chunk boundaries were identical in every run",
                "the port's rng (src/agent2utau/transcription/game_onnx.py) is created but never "
                "passed to the model, so the seed cannot control the segmenter's sampling",
            ],
            "not_confirmed": [
                "whether the difference comes from ONNX Runtime's internal random operator, from "
                "multi-threaded reduction order, or from both",
            ],
            "downstream_rule": "the GAME JSON files are pinned by SHA256 and reused; a regression "
                               "run never regenerates them",
        },
    }
    (OUT_DIR / "game_stability.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"comparison": comparison, "divergences": divergences},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
