import json

phones = json.loads(open("runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/phones.json", encoding="utf-8").read())
for pi in [12, 28, 34]:
    p = phones["parts"][pi]
    print(f"=== Part {pi} ===")
    for n in p["notes"]:
        print(f"  note lyric='{n['lyric']}' tone={n['tone']} phones={[ph['phoneme'] for ph in n.get('phonemes', [])]}")
