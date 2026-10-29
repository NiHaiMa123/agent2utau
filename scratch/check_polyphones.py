from pathlib import Path
from agent2utau.openutau.build import build_project
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
import json

cfg = load_config()

test_seg = [{
    "start_sec": 1.0,
    "notes": [
        {"start": 1.0, "end": 1.5, "dur": 0.5, "tone": 62, "lyric": "数"},
        {"start": 1.5, "end": 2.0, "dur": 0.5, "tone": 62, "lyric": "都"},
        {"start": 2.0, "end": 2.5, "dur": 0.5, "tone": 62, "lyric": "曾"},
        {"start": 2.5, "end": 3.0, "dur": 0.5, "tone": 62, "lyric": "没"},
        {"start": 3.0, "end": 3.5, "dur": 0.5, "tone": 62, "lyric": "倒"},
        {"start": 3.5, "end": 4.0, "dur": 0.5, "tone": 62, "lyric": "勒"},
    ]
}]

test_ustx = Path("scratch/test_polyphones.ustx")
build_project("test_polyphones", test_seg, test_ustx)

out_phones = Path("scratch/test_polyphones.json")
res = run_bridge(cfg, [
    "export-phonemes",
    "--project", str(test_ustx.resolve()),
    "--out", str(out_phones.resolve()),
])
print("Bridge res:", json.dumps(res, indent=2))

if out_phones.exists():
    data = json.loads(out_phones.read_text(encoding="utf-8"))
    for ph in data["parts"][0]["phones"]:
        print(f"Phone {ph['phoneme']:6s} at note {ph.get('note_index')}")
