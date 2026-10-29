import json

phones = json.loads(open("runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/phones.json", encoding="utf-8").read())
for pi in [12, 28, 34]:
    p = phones["parts"][pi]
    print(f"=== Part {pi} ===")
    for phr in p["phrases"]:
        for ph in phr["phonemes"]:
            print(f"  phoneme={ph['phoneme']:6s} [{ph['position_ms']:7.1f}ms - {ph['position_ms']+ph['duration_ms']:7.1f}ms]")
