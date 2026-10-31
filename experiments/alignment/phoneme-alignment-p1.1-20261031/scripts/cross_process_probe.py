"""Cross-process check: does a fresh GAME session give the same result twice?

One inference per process, so the session is used exactly once.  If the
signatures agree, the difference seen between runs (469 / 467 / 468 events)
cannot come from the session's random state and must come from something
outside the process - the ONNX Runtime version, the graph optimisation or the
process-level entropy.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from agent2utau.transcription.game_onnx import GameOnnx  # noqa: E402
from agent2utau.resources.config import load_config  # noqa: E402

VOCALS = (REPO_ROOT / "runs/production/nianlun-from-scratch-20261028/observation/stems/"
          "source_(vocals)_vocals_mel_band_roformer.wav")
OUT = (REPO_ROOT / "runs/production/phoneme-alignment-p1.1-20261031/game_stability/"
       "cross_process.json")


def main() -> int:
    cfg = load_config()
    model_dir = Path(cfg["openutau_dir"]) / "Dependencies" / "game"
    samples, sr = sf.read(VOCALS, dtype="float32")
    samples = samples.mean(axis=1) if samples.ndim > 1 else samples
    game = GameOnnx(model_dir)
    notes = game.infer(samples, chunk=True, language="zh", seed=11)
    payload = json.dumps(notes, sort_keys=True).encode("utf-8")
    record = {
        "pid": __import__("os").getpid(),
        "event_count": len(notes),
        "signature": hashlib.sha256(payload).hexdigest(),
        "first_event": notes[0] if notes else None,
    }
    history = []
    if OUT.is_file():
        history = json.loads(OUT.read_text(encoding="utf-8"))["runs"]
    history.append(record)
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "question": "one fresh GAME session per process - same result?",
        "runs": history,
        "identical_across_processes": len({row["signature"] for row in history}) == 1,
        "event_counts": [row["event_count"] for row in history],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
