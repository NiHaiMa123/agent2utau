"""年轮 v2 谱面（证据驱动）。

与 v1 的差别：
  1) 音素时钟按源有声段重建：HFA 只提供字的身份与数量，其静默段若含实际发声，
     该发声时间归还给相应字；句界钳制保证相邻句不重叠。
  2) 音符音高 = 该字"核心有声段"的中位（辅音静默处 F0 失锁，不能当音高），
     字内 melisma 只在音高真的变化处切分。
  3) 呼吸直接用真实静默（>=0.22s 记 AP，>=0.5s 记 SP），句内不留未标注空隙
     （否则原生会拆成多条渲染句）；呼吸音符载频取下一唱字电平。
  4) 字长下限 0.09s，不足时移动字界向邻字匀时间。
只写 v2 run 目录，不动 v1。
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\project\agent2utau\src")

from agent2utau.openutau.build import build_project, sec_to_tick, RESOLUTION, BPM_FIXED
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.ustx import TempoMap, load_ustx, sha256
from agent2utau.evaluation.independent import extract_regions, validate_native
from agent2utau.resources.config import load_config

V1 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
V2 = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")
DESIGN = V2 / "design"
MIN_SYL = 0.09
MIN_SUB = 0.08
TICK_S = 60.0 / (BPM_FIXED * RESOLUTION)


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


if not (V2 / "observation").exists():
    V2.mkdir(parents=True, exist_ok=True)
    for sub in ("observation", "hfa", "hfa_inputs"):
        shutil.copytree(V1 / sub, V2 / sub)
    print("observation/hfa copied from v1 (same source, same seed)")
DESIGN.mkdir(parents=True, exist_ok=True)

# ---------------- 源观测 ----------------
zf = np.load(V2 / "observation" / "fcpe.npz")
zr = np.load(V2 / "observation" / "rmvpe.npz")
t_f, f0_f = zf["times"].astype(float), zf["f0_hz"].astype(float)
t_r, f0_r = zr["times"].astype(float), zr["f0_hz"].astype(float)
c_f = np.where(f0_f > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_f, 1e-6) / 440.0), np.nan)
c_r = np.where(f0_r > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0_r, 1e-6) / 440.0), np.nan)
rf = np.interp(t_f, t_f, c_f)
rr = np.interp(t_f, t_r, c_r)
agree = np.isfinite(rf) & np.isfinite(rr) & (np.abs(rf - rr) <= 120)
c_all = np.where(agree, (rf + rr) / 2.0, np.nan)

stem, sr = sf.read(str(V2 / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"), dtype="float32")
if stem.ndim > 1:
    stem = stem.mean(axis=1)
win = int(sr * 0.02)
nfr = len(stem) // win
rms_db = 20 * np.log10(np.sqrt((stem[: nfr * win].reshape(nfr, win) ** 2).mean(axis=1)) + 1e-12)
t_rms = (np.arange(nfr) + 0.5) * 0.02
e_at = np.interp(t_f, t_rms, rms_db)
vmask = agree & (e_at > -42.0) & (c_all > 3900.0) & (c_all < 8800.0)


def stats(a, b):
    m = (t_f >= a) & (t_f < b) & vmask
    if m.sum() < 3:
        return None
    v = c_all[m]
    return dict(median=float(np.median(v)), span=float(v.max() - v.min()), n=int(m.sum()),
                t=t_f[m], track=v)


def core_level(a, b):
    """该字的核心有声段中位：辅音静默处 F0 失锁，不能当成音高。"""
    st = stats(a, b)
    if st is None:
        return None
    tt, vv = st["t"], st["track"]
    runs_ = []
    s0 = 0
    for j in range(1, len(tt) + 1):
        if j == len(tt) or tt[j] - tt[j - 1] > 0.06:
            if j - s0 >= 2:
                runs_.append((s0, j))
            s0 = j
    if not runs_:
        return st["median"]
    a0, b0 = max(runs_, key=lambda r: r[1] - r[0])
    return float(np.median(vv[a0:b0]))


def voiced_runs(a, b, min_len=0.05):
    m = (t_f >= a) & (t_f < b) & vmask
    out, start = [], None
    for t, v in zip(t_f[m], vmask[m]):
        if v and start is None:
            start = t
        elif not v and start is not None:
            if t - start >= min_len:
                out.append((start, t))
            start = None
    if start is not None and b - start >= min_len:
        out.append((start, b))
    merged = []
    for s, e in out:
        if merged and s - merged[-1][1] < 0.08:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


hfa = rj(V2 / "hfa" / "hfa_summary.json")
game = rj(V2 / "observation" / "game.json")
game_onsets = sorted({round(n["start"], 3) for n in game["notes"] if n.get("voiced") and n["dur"] >= 0.08})
repairs, levels_log = [], []

# ---------------- 全局字表 + 静默校正 ----------------
global_words = []
for p in hfa["phrases"]:
    for i, w in enumerate(p["lexical_words"]):
        global_words.append(dict(phrase=p["phrase_id"], wi=i, hanzi=w["hanzi"], pinyin=w["mark"],
                                  hfa_start=w["start_s"], hfa_end=w["end_s"]))
global_words.sort(key=lambda w: (w["hfa_start"], w["hfa_end"]))
for w in global_words:
    w["span"] = [w["hfa_start"], w["hfa_end"]]

all_silences = []
for p in hfa["phrases"]:
    for ph in p["phones"]:
        if ph["mark"] in ("SP", "AP", "EP"):
            all_silences.append((p["phrase_id"], ph["start_s"], ph["end_s"]))
all_silences.sort(key=lambda s: s[1])
for pid, ss, se in all_silences:
    for vs, ve in voiced_runs(ss, se):
        overlap = [w for w in global_words if w["hfa_start"] < ve and w["hfa_end"] > vs]
        if overlap:
            overlap[0]["span"][0] = min(overlap[0]["span"][0], vs)
            overlap[-1]["span"][1] = max(overlap[-1]["span"][1], ve)
            kind = "run_over_words"
        else:
            idx = next((i for i, w in enumerate(global_words) if w["hfa_start"] >= ss), None)
            prev = global_words[idx - 1] if idx else None
            if prev is not None and (vs - prev["hfa_end"]) <= 0.12:
                prev["span"][1] = max(prev["span"][1], ve)
                kind = "to_prev"
            elif idx is not None:
                global_words[idx]["span"][0] = min(global_words[idx]["span"][0], vs)
                kind = "to_next"
            else:
                continue
        repairs.append(dict(phrase=pid, kind=kind, recovered=[round(vs, 3), round(ve, 3)]))

for i in range(len(global_words) - 1):
    a, b = global_words[i], global_words[i + 1]
    if a["span"][1] > b["span"][0]:
        mid = (a["span"][1] + b["span"][0]) / 2
        a["span"][1] = mid
        b["span"][0] = mid
by_phrase = {}
for w in global_words:
    by_phrase.setdefault(w["phrase"], []).append(w)
pids = [p["phrase_id"] for p in hfa["phrases"]]
for k in range(len(pids) - 1):
    a_list, b_list = by_phrase[pids[k]], by_phrase[pids[k + 1]]
    a_end = max(w["span"][1] for w in a_list)
    b_start = min(w["span"][0] for w in b_list)
    if a_end > b_start:
        for w in a_list:
            w["span"][1] = min(w["span"][1], b_start)
        for w in b_list:
            w["span"][0] = max(w["span"][0], a_end)

# ---------------- 逐句建音符 ----------------
segments = []
for p in hfa["phrases"]:
    pid = p["phrase_id"]
    syls = []
    for w in by_phrase[pid]:
        a, b = w["span"]
        b = max(b, a + 0.04)
        syls.append(dict(hanzi=w["hanzi"], pinyin=w["pinyin"], start=a, end=b))
    # 字长下限
    for i, s in enumerate(syls):
        if s["end"] - s["start"] >= MIN_SYL:
            continue
        need = MIN_SYL - (s["end"] - s["start"])
        if i + 1 < len(syls):
            nxt = syls[i + 1]
            room = (nxt["end"] - nxt["start"]) - MIN_SYL
            take = min(need, max(0.0, room))
            if take > 0:
                nxt["start"] += take
                s["end"] += take
        if need > 0 and i > 0:
            prev = syls[i - 1]
            room = (prev["end"] - prev["start"]) - MIN_SYL
            take = min(need, max(0.0, room))
            if take > 0:
                prev["end"] -= take
                s["start"] -= take
    for i in range(len(syls) - 1):
        if syls[i]["end"] > syls[i + 1]["start"]:
            mid = (syls[i]["end"] + syls[i + 1]["start"]) / 2
            syls[i]["end"] = mid
            syls[i + 1]["start"] = mid
    # 字内细分
    notes = []
    for i, s in enumerate(syls):
        a, b = s["start"], s["end"]
        cuts = [t for t in game_onsets if a + MIN_SUB < t < b - MIN_SUB]
        pieces = []
        if cuts:
            prev = a
            for t in cuts:
                pieces.append((prev, t))
                prev = t
            pieces.append((prev, b))
            pieces = [pc for pc in pieces if pc[1] - pc[0] >= MIN_SUB] or [(a, b)]
            if pieces[0][0] != a:
                pieces[0] = (a, pieces[0][1])
            if pieces[-1][1] != b:
                pieces[-1] = (pieces[-1][0], b)
            # 只在音高真的变化处保留切分
            if len(pieces) > 1:
                keep = [pieces[0]]
                for pc in pieces[1:]:
                    l1 = stats(keep[-1][0], keep[-1][1])
                    l2 = stats(pc[0], pc[1])
                    if l1 and l2 and abs(l2["median"] - l1["median"]) >= 60:
                        keep.append(pc)
                    else:
                        keep[-1] = (keep[-1][0], pc[1])
                pieces = keep
        else:
            pieces = [(a, b)]
        for k, (pa, pb) in enumerate(pieces):
            st = stats(pa, pb) or stats(pa, pa + 0.1)
            if st is None:
                st = dict(median=(syls[i - 1]["_last"] if i else 6000.0))
            cl = core_level(pa, pb)
            base_c = cl if cl is not None else st["median"]
            notes.append(dict(start=round(pa, 4), end=round(pb, 4), dur=round(pb - pa, 4),
                              tone=int(round(base_c / 100)), lyric=s["hanzi"] if k == 0 else "+",
                              syl=i, sub=k))
            syls[i]["_last"] = base_c
            if k == 0:
                levels_log.append(dict(phrase=pid, hanzi=s["hanzi"], t=round(pa, 3),
                                       core_cents=round(base_c, 1), tone=int(round(base_c / 100))))
    # 组装音符 + 呼吸
    out_notes = []
    first_a = syls[0]["start"]
    lead_start = max(0.0, first_a - 0.22)
    lv = stats(first_a, first_a + 0.12) or dict(median=6000.0)
    if lead_start < first_a - 0.03:
        out_notes.append(dict(start=round(lead_start, 4), end=round(first_a, 4),
                              dur=round(first_a - lead_start, 4),
                              tone=int(round(lv["median"] / 100)), lyric="AP"))
    for i, s in enumerate(syls):
        for n in [n for n in notes if n["syl"] == i]:
            out_notes.append(dict(start=n["start"], end=n["end"], dur=n["dur"], tone=n["tone"], lyric=n["lyric"]))
        if i + 1 < len(syls):
            gap = syls[i + 1]["start"] - s["end"]
            if gap >= 0.22:
                out_notes.append(dict(start=round(s["end"], 4), end=round(syls[i + 1]["start"], 4),
                                      dur=round(gap, 4), tone=out_notes[-1]["tone"],
                                      lyric="SP" if gap >= 0.5 else "AP"))
            else:
                out_notes[-1]["end"] = round(max(out_notes[-1]["end"], syls[i + 1]["start"]), 4)
                out_notes[-1]["dur"] = round(out_notes[-1]["end"] - out_notes[-1]["start"], 4)
    tail = syls[-1]["end"]
    out_notes.append(dict(start=round(tail, 4), end=round(tail + 0.25, 4), dur=0.25,
                          tone=out_notes[-1]["tone"], lyric="AP"))
    # 呼吸载频取下一唱字电平
    for i, n in enumerate(out_notes):
        if n["lyric"] in ("AP", "SP"):
            nxt = next((m for m in out_notes[i + 1:] if m["lyric"] not in ("AP", "SP")), None)
            prv = next((m for m in reversed(out_notes[:i]) if m["lyric"] not in ("AP", "SP")), None)
            pick = nxt or prv
            if pick:
                n["tone"] = pick["tone"]
    anchor_tick = (sec_to_tick(out_notes[0]["start"] - 0.15) // 20) * 20
    segments.append(dict(phrase_id=pid, hanzi=p["hanzi"], start_sec=out_notes[0]["start"],
                         part_start_sec=anchor_tick * TICK_S, notes=out_notes))


def sung_bounds(seg):
    sung = [n for n in seg["notes"] if n["lyric"] not in ("AP", "SP")]
    if not sung:
        return None, None
    return min(n["start"] for n in sung), max(n["end"] for n in sung)


for seg in segments:
    ss, se = sung_bounds(seg)
    if ss is None:
        continue
    lead = seg["notes"][0]
    if lead["lyric"] in ("AP", "SP") and lead["end"] > ss:
        seg["notes"].pop(0)
    tail = seg["notes"][-1]
    if tail["lyric"] in ("AP", "SP") and tail["start"] < se:
        seg["notes"].pop()
for k in range(len(segments) - 1):
    cur, nxt = segments[k], segments[k + 1]
    _, cur_end = sung_bounds(cur)
    nxt_start, _ = sung_bounds(nxt)
    if cur_end is None or nxt_start is None:
        continue
    tail = cur["notes"][-1]
    if tail["lyric"] in ("AP", "SP") and tail["end"] > nxt_start:
        tail["end"] = round(max(tail["start"], nxt_start), 4)
        tail["dur"] = round(tail["end"] - tail["start"], 4)
        if tail["dur"] < 0.03:
            cur["notes"].pop()
for k in range(1, len(segments)):
    cur, prv = segments[k], segments[k - 1]
    _, prv_end = sung_bounds(prv)
    cur_start, _ = sung_bounds(cur)
    if prv_end is None or cur_start is None:
        continue
    lead = cur["notes"][0]
    if lead["lyric"] in ("AP", "SP") and lead["start"] < prv_end:
        lead["start"] = round(prv_end, 4)
        lead["dur"] = round(lead["end"] - lead["start"], 4)
        if lead["dur"] < 0.03:
            cur["notes"].pop(0)

tiny = [(s["phrase_id"], n) for s in segments for n in s["notes"]
        if n["lyric"] not in ("SP", "AP", "+") and n["dur"] < 0.085]
br = [n for s in segments for n in s["notes"] if n["lyric"] in ("SP", "AP")]
print(f"静默校正 {len(repairs)} 处; 极短唱字(<0.085s) {len(tiny)} 个; 呼吸音符 {len(br)} 个")
for t in tiny[:8]:
    print("   极短:", t)

SCORE = DESIGN / "score.ustx"
build_project("nianlun_lingyuan", segments, SCORE)
print(f"built parts={len(segments)} notes={sum(len(s['notes']) for s in segments)}")

cfg = load_config()
pitch_path = DESIGN / "baseline_pitch.json"
phones_path = DESIGN / "baseline_phones.json"
prov_path = DESIGN / "native_provenance.json"
rp = run_bridge(cfg, ["export-pitch", "--project", str(SCORE.resolve()), "--out", str(pitch_path.resolve())])
rph = run_bridge(cfg, ["export-phonemes", "--project", str(SCORE.resolve()), "--out", str(phones_path.resolve())])
print("export:", rp.get("ok"), rp.get("frame_count"), rph.get("ok"), rph.get("phone_count"))
ou = Path(cfg["openutau_dir"])
doc = load_ustx(SCORE)
singer = doc["tracks"][0]["singer"]
prov = dict(schema_version=1, project_sha256=sha256(SCORE),
            pitch_sha256=sha256(pitch_path), phonemes_sha256=sha256(phones_path),
            environment=dict(core_sha256=sha256(ou / "OpenUtau.Core.dll"),
                             bridge_sha256=sha256(ou / "a2u-bridge.exe"),
                             singer_config_sha256=sha256(ou / "Singers" / singer / "dsconfig.yaml"),
                             singer_id=singer))
prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
tm = TempoMap.from_doc(doc)
native, gap = validate_native(SCORE, doc, tm, pitch_path, phones_path, prov_path)
print("validate_native gap:", gap)
regions, phrases = extract_regions(native)
print(f"regions={len(regions)} vowel_units={len([r for r in regions if 'phone_ids' in r])}")
(DESIGN / "clock_repair_log.json").write_text(
    json.dumps(dict(repairs=repairs, levels=levels_log), ensure_ascii=False, indent=1), encoding="utf-8")
print("done")
