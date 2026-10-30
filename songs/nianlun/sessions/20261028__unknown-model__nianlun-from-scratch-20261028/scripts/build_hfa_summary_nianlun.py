import hashlib
import json
from pathlib import Path
import textgrid

run_dir = Path(r"runs/production/nianlun-from-scratch-20261028")
obs_dir = run_dir / "observation"
hfa_dir = run_dir / "hfa"
hfa_inputs = run_dir / "hfa_inputs"

manifest = json.loads((hfa_inputs / "slices_manifest.json").read_text(encoding="utf-8"))["phrases"]
game_notes = json.loads((obs_dir / "game.json").read_text(encoding="utf-8"))["notes"]
voiced_all = []
for idx, n in enumerate(game_notes):
    if n["voiced"]:
        voiced_all.append((idx, n))

summary = {"phrases": []}

for entry in manifest:
    pid = entry["phrase_id"]
    hanzi = entry["hanzi"]
    pinyin = entry["pinyin"]
    t0 = entry["slice_start_s"]
    tg_path = hfa_dir / "TextGrid" / f"{pid}.TextGrid"
    assert tg_path.exists(), f"Missing TextGrid for {pid}"

    tg = textgrid.TextGrid.fromFile(str(tg_path))
    words_tier = tg.getFirst("words")
    phones_tier = tg.getFirst("phones")

    words = []
    lexical_words = []
    char_idx = 0
    for iv in words_tier:
        mark = iv.mark.strip()
        if not mark:
            continue
        st = round(t0 + float(iv.minTime), 4)
        et = round(t0 + float(iv.maxTime), 4)
        dur = round(float(iv.maxTime - iv.minTime), 4)
        w_obj = {"mark": mark, "start_s": st, "end_s": et, "dur_s": dur}
        if mark not in ("SP", "AP", "EP"):
            if char_idx < len(hanzi):
                w_obj["hanzi"] = hanzi[char_idx]
                char_idx += 1
            lexical_words.append(w_obj)
        words.append(w_obj)

    phones = []
    for iv in phones_tier:
        mark = iv.mark.strip()
        if not mark:
            continue
        st = round(t0 + float(iv.minTime), 4)
        et = round(t0 + float(iv.maxTime), 4)
        dur = round(float(iv.maxTime - iv.minTime), 4)
        phones.append({"mark": mark, "start_s": st, "end_s": et, "dur_s": dur})

    # GAME voiced notes in this phrase
    v_start = entry["voiced_event_start_idx"]
    v_end = entry["voiced_event_end_idx"]
    game_voiced = []
    if v_start >= 0 and v_end >= v_start:
        for vi in range(v_start, v_end + 1):
            g_idx, gn = voiced_all[vi]
            game_voiced.append({
                "v_idx": vi,
                "g_idx": g_idx,
                "start_s": round(gn["start"], 4),
                "end_s": round(gn["start"] + gn["dur"], 4),
                "dur_s": round(gn["dur"], 4),
                "tone": round(gn["tone"], 2),
                "midi": int(round(gn["tone"])),
            })

    def sha256_f(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    phrase_obj = {
        "phrase_id": pid,
        "hanzi": hanzi,
        "pinyin": pinyin,
        "textgrid_path": str(tg_path.resolve()),
        "textgrid_sha256": sha256_f(tg_path),
        "words": words,
        "phones": phones,
        "lexical_words": lexical_words,
        "game_voiced": game_voiced,
    }
    summary["phrases"].append(phrase_obj)

out_summary = hfa_dir / "hfa_summary.json"
out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated {out_summary} with {len(summary['phrases'])} phrases.")
