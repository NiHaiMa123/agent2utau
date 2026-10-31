"""Do the GAME model files still match the hashes recorded with the observation?

The stability study has to rule out "the models changed under us" before it
can say anything about the model's own randomness.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.resources.config import load_config  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    cfg = load_config()
    recorded = json.loads(
        (REPO_ROOT / "runs/production/nianlun-from-scratch-20261028/observation/game.json")
        .read_text(encoding="utf-8"))["models"]
    model_dir = Path(cfg["openutau_dir"]) / "Dependencies" / "game"
    current = {p.name: sha256(p) for p in sorted(model_dir.glob("*.onnx"))}
    print("model file            recorded(2026-10-28)  now                verdict")
    changed = []
    for name, digest in sorted(current.items()):
        before = [value for path, value in recorded.items() if path.endswith(name)]
        verdict = "SAME" if before and before[0] == digest else "CHANGED"
        if verdict == "CHANGED":
            changed.append(name)
        print(f"{name:22} {before[0][:16] if before else '-':18} {digest[:16]}  {verdict}")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
