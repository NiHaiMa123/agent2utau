import json
from pathlib import Path

p = Path("experiments/alignment/data/test_polyphones.json")
data = json.loads(p.read_text(encoding="utf-8"))
print("Keys:", data.keys())
print("Part 0 keys:", data["parts"][0].keys())
for i, n in enumerate(data["parts"][0].get("notes", [])):
    phs = [p["phoneme"] for p in n.get("phones", [])]
    print(f"  Note {i} lyric='{n.get('lyric')}' -> phones={phs}")
