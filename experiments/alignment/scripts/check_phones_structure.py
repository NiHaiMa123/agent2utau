import json
from pathlib import Path

p = Path("experiments/alignment/data/test_polyphones.json")
data = json.loads(p.read_text(encoding="utf-8"))
if "phrases" in data["parts"][0]:
    for ph in data["parts"][0]["phrases"]:
        print("Phrase:", ph.keys())
        for pho in ph.get("phones", []):
            print("  Phone:", pho)
if "units" in data:
    print("Units count:", len(data["units"]))
    for u in data["units"][:5]:
        print("  Unit:", u)
