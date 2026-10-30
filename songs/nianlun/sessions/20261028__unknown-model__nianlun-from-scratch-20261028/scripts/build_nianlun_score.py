import hashlib
import json
from pathlib import Path
import yaml

from agent2utau.openutau.build import build_project, sec_to_tick, RESOLUTION, BPM_FIXED
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.ustx import TempoMap, load_ustx, sha256
from agent2utau.evaluation.independent import extract_regions, validate_native
from agent2utau.resources.config import load_config

cfg = load_config()
run_dir = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
design_dir = run_dir / "design"
design_dir.mkdir(parents=True, exist_ok=True)

hfa = json.loads((run_dir / "hfa" / "hfa_summary.json").read_text(encoding="utf-8"))
tones_spec = json.loads(Path("songs/nianlun/sessions/20261028__unknown-model__nianlun-from-scratch-20261028/reports/nianlun_phrase_tones.json").read_text(encoding="utf-8"))

def tick_to_sec(tick: int) -> float:
    return tick * (60.0 / (BPM_FIXED * RESOLUTION))

# Leading breath/silence type: SP at intro and after long interludes, AP elsewhere
LEADING_LABELS = {}
for i, p in enumerate(hfa["phrases"]):
    pid = p["phrase_id"]
    if pid in ("p00", "p22", "p44"):
        LEADING_LABELS[pid] = "SP"
    else:
        LEADING_LABELS[pid] = "AP"

segments = []

for p in hfa["phrases"]:
    pid = p["phrase_id"]
    hanzi = p["hanzi"]
    l_words = p["lexical_words"]
    phones = p["phones"]
    p_tones = tones_spec[pid]
    assert len(l_words) == len(p_tones), f"{pid}: len mismatch {len(l_words)} vs {len(p_tones)}"

    syl_spans = []
    for wi, lw in enumerate(l_words):
        ws, we = lw["start_s"], lw["end_s"]
        w_phones = [
            ph for ph in phones
            if ph["start_s"] >= ws - 1e-3 and ph["end_s"] <= we + 1e-3
            and ph["mark"] not in ("SP", "AP", "EP")
        ]
        vs = w_phones[-1]["start_s"] if w_phones else ws
        ve = we
        if ve - vs < 0.18:
            vs = max(ws, ve - 0.19)
        syl_spans.append({
            "hanzi": lw["hanzi"],
            "pinyin": lw["mark"],
            "word_start_s": ws,
            "vowel_start_s": vs,
            "end_s": ve,
            "tone_spec": p_tones[wi],
        })

    raw_notes = []
    first_vs = syl_spans[0]["vowel_start_s"]
    first_t = syl_spans[0]["tone_spec"]
    first_tone = first_t[0][0] if isinstance(first_t, list) else first_t
    lead_dur = 0.20
    lead_start = round(first_vs - lead_dur, 4)
    raw_notes.append({
        "start": lead_start,
        "end": round(first_vs, 4),
        "dur": round(first_vs - lead_start, 4),
        "tone": int(first_tone),
        "lyric": LEADING_LABELS[pid],
    })

    for i, sp in enumerate(syl_spans):
        vs = sp["vowel_start_s"]
        if i > 0:
            prev_end = raw_notes[-1]["end"]
            if vs < prev_end + 0.08:
                vs = max(vs, prev_end)
        if i < len(syl_spans) - 1:
            next_sp = syl_spans[i + 1]
            gap_words = next_sp["word_start_s"] - sp["end_s"]
            if gap_words >= 0.18:
                # Inter-subphrase pause
                note_end = round(sp["end_s"], 4)
                ap_end = round(next_sp["vowel_start_s"], 4)
                insert_ap = (note_end, ap_end, "AP" if gap_words >= 0.22 else "SP")
            else:
                note_end = round(next_sp["vowel_start_s"], 4)
                insert_ap = None
        else:
            note_end = round(sp["end_s"], 4)
            insert_ap = None

        tspec = sp["tone_spec"]
        if isinstance(tspec, list):
            total_dur = note_end - vs
            cur_s = vs
            cum_frac = 0.0
            for k, (t_midi, frac) in enumerate(tspec):
                cum_frac += frac
                n_end = round(vs + total_dur * cum_frac, 4) if k < len(tspec) - 1 else note_end
                if n_end <= cur_s:
                    n_end = cur_s + 0.05
                raw_notes.append({
                    "start": round(cur_s, 4),
                    "end": round(n_end, 4),
                    "dur": round(n_end - cur_s, 4),
                    "tone": int(t_midi),
                    "lyric": sp["hanzi"] if k == 0 else "+",
                })
                cur_s = n_end
        else:
            raw_notes.append({
                "start": round(vs, 4),
                "end": round(note_end, 4),
                "dur": round(note_end - vs, 4),
                "tone": int(tspec),
                "lyric": sp["hanzi"],
            })

        if insert_ap is not None:
            ap_s, ap_e, ap_lyric = insert_ap
            next_t = syl_spans[i + 1]["tone_spec"]
            next_midi = next_t[0][0] if isinstance(next_t, list) else next_t
            raw_notes.append({
                "start": round(ap_s, 4),
                "end": round(ap_e, 4),
                "dur": round(ap_e - ap_s, 4),
                "tone": int(next_midi),
                "lyric": ap_lyric,
            })

    anchor_tick = (sec_to_tick(raw_notes[0]["start"] - 0.15) // 20) * 20
    anchor_sec = tick_to_sec(max(0, anchor_tick))
    segments.append({
        "phrase_id": pid,
        "hanzi": hanzi,
        "start_sec": raw_notes[0]["start"],
        "part_start_sec": anchor_sec,
        "notes": raw_notes,
    })

for s_idx, seg in enumerate(segments):
    raw_n = seg["notes"]
    for j in range(len(raw_n) - 1):
        n1 = raw_n[j]
        n2 = raw_n[j + 1]
        t1_start = sec_to_tick(n1["start"])
        t1_dur = sec_to_tick(n1["end"]) - t1_start
        t2_start = sec_to_tick(n2["start"])
        gap = t2_start - (t1_start + t1_dur)
        if t1_dur <= 0 or gap < -1:
            print(f"ERROR in seg {s_idx} ({seg['phrase_id']}): note {j} ('{n1['lyric']}' {n1['start']}-{n1['end']}s) vs note {j+1} ('{n2['lyric']}' {n2['start']}-{n2['end']}s), dur={t1_dur}, gap={gap}")

score_ustx = design_dir / "score.ustx"
build_project("nianlun_lingyuan", segments, score_ustx)
print(f"Built {score_ustx} with {len(segments)} voice parts.")

# Export baseline pitch and phonemes via bridge
pitch_path = design_dir / "baseline_pitch.json"
phones_path = design_dir / "baseline_phones.json"
prov_path = design_dir / "native_provenance.json"

r_pitch = run_bridge(cfg, ["export-pitch", "--project", str(score_ustx.resolve()), "--out", str(pitch_path.resolve())])
print("export-pitch:", r_pitch.get("ok"), r_pitch.get("frame_count"), "frames")

r_phones = run_bridge(cfg, ["export-phonemes", "--project", str(score_ustx.resolve()), "--out", str(phones_path.resolve())])
print("export-phonemes:", r_phones.get("ok"), r_phones.get("phone_count"), "phones")

ou = Path(cfg["openutau_dir"])
doc = load_ustx(score_ustx)
singer = doc["tracks"][0]["singer"]
env = {
    "core_sha256": sha256(ou / "OpenUtau.Core.dll"),
    "bridge_sha256": sha256(ou / "a2u-bridge.exe"),
    "singer_config_sha256": sha256(ou / "Singers" / singer / "dsconfig.yaml"),
    "singer_id": singer,
}
prov = {
    "schema_version": 1,
    "project_sha256": sha256(score_ustx),
    "pitch_sha256": sha256(pitch_path),
    "phonemes_sha256": sha256(phones_path),
    "environment": env,
}
prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")

tm = TempoMap.from_doc(doc)
native, gap = validate_native(score_ustx, doc, tm, pitch_path, phones_path, prov_path)
print("validate_native gap:", gap)
regions, phrases = extract_regions(native)
vowel_units = [r for r in regions if "phone_ids" in r]
unknown_phones = [r for r in regions if "phone_ids" not in r and r["region_type"] == "unknown"]
print(f"Total regions: {len(regions)}, vowel units: {len(vowel_units)}, unknown phones: {len(unknown_phones)}")
