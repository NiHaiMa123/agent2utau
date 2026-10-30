import json
from pathlib import Path
from agent2utau.openutau.ustx import sha256

sources_path = Path("runs/production/zuihouyiye-from-scratch-20261027/design/sources.json")
sources = json.loads(sources_path.read_text(encoding="utf-8"))
print("Sources rows:", len(sources))
for s in sources:
    if "score" in s["id"]:
        print(s)
