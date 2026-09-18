"""M2.5 Blocker E — machine structure precision calibration (plan2 §10.1.5).

A machine `TRUE_SPLIT_CANDIDATE`/`TRUE_MERGE_CANDIDATE` is frozen evidence,
not repair truth. Before any machine structure candidate may enter the
trusted corrected score it must survive a phrase-level A/B calibration:
the human hears SOURCE context plus a blind Baseline-vs-Candidate pair
(same phrase window, same singer/tempo/renderer/gain, identical score
outside the target) and picks one of four outcomes:

  split/baseline preferred / equivalent / none_correct
  → human_confirmed_machine_split / machine_structure_false_positive /
    no_demonstrated_benefit / unresolved (manual_followup)

Only `human_confirmed_machine_split` authorizes apply — recorded in
runs/<diag>/structure_calibration/decisions.json, bound to the exact
repair_id + patch_sha + audio_package_hash. Reuses the D render machinery
(phrase_window, blind options, shared-gain option renders, provenance)
but keeps its own store: calibration semantics ≠ phrase-review semantics.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CALIB_SCHEMA = "m25-cal-2"
CALIB_DIRNAME = "structure_calibration"
LEGACY_DIRNAMES = ("structure_calibration_m25cal1_audit",)
LYRIC_CONTRACT = "neutral_vowel"
CHOICES = ("split", "baseline", "equivalent", "none_correct")
OUTCOME = {"split": "human_confirmed_machine_split",
           "baseline": "machine_structure_false_positive",
           "equivalent": "no_demonstrated_benefit",
           "none_correct": "unresolved"}


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _sha(obj) -> str:
    if isinstance(obj, (dict, list)):
        obj = _canon(obj).encode("utf-8")
    return hashlib.sha256(obj).hexdigest()


def _jwrite(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def _now() -> float:
    return time.time()


def calib_dir(run_dir: Path) -> Path:
    return Path(run_dir) / CALIB_DIRNAME


def ensure_calib_authority(run_dir: Path):
    """Fail-closed schema gate (§10.1.5A-G1): any store whose
    plan/decisions/state files are not schema m25-cal-2 is a legacy
    review artifact — rename the whole directory to an audit name
    (never overwrite) and start a clean m25-cal-2 authority. Old
    packages/decisions keep existing only as regression evidence;
    they can never authorize repair again."""
    cdir = calib_dir(run_dir)
    if not cdir.exists():
        return
    bad = False
    for name in ("plan.json", "decisions.json", "state.json"):
        p = cdir / name
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                bad = True
                break
            if d.get("schema") != CALIB_SCHEMA:
                bad = True
                break
    if not bad:
        return
    import time as _t
    base = run_dir / LEGACY_DIRNAMES[0]
    dest = base
    if dest.exists():
        dest = run_dir / f"{LEGACY_DIRNAMES[0]}_" \
            f"{_t.strftime('%Y%m%d-%H%M%S')}"
    cdir.replace(dest)
    cdir.mkdir(parents=True, exist_ok=True)


def cal_item_id(repair_id: str) -> str:
    """Stable calibration item identity = the repair identity itself —
    same patch content → same id across re-plans."""
    return "cal-" + str(repair_id)


# ------------------------------------------------------------ plan (pure)

def plan_calibration(run, packets=None, notes=None, rph=None):
    """Pure: machine structure candidates → review-shaped cal items.

    Each item carries the exact patch the repair engine would apply,
    a blinded [baseline, candidate] option pair and a phrase window —
    same window/singer/renderer/gain for both options (§10.1.5 UX).
    Deterministic: rebuilt from the same frozen artifacts the repair
    plan binds, so repair_id/patch match plan entries exactly.
    """
    from .repair import (machine_structure_candidates,
                         _structure_repair_id, _sha as rsha)
    from .review.build import (assign_identity, blind_order,
                               context_notes, phrase_window, plan_hash,
                               render_profile, render_profile_hash)
    packets = packets if packets is not None else run["packets"]
    notes = notes if notes is not None else run["baseline_notes"]
    c0_sha = rsha(notes)
    if rph is None:
        rph = render_profile_hash(render_profile())
    items = []
    for c in machine_structure_candidates(packets):
        patch = c["patch"]
        rid = _structure_repair_id(run["run_id"], c0_sha, c, notes)
        iid = cal_item_id(rid)
        typ = patch["type"]
        if typ == "split":
            region = [patch["children"][0]["start"],
                      patch["children"][-1]["end"]]
        elif typ == "merge":
            region = [patch["merged"]["start"], patch["merged"]["end"]]
        else:  # boundary_shift — single note span after shift
            a = patch.get("after") or {}
            region = [a.get("start", patch.get("start")),
                      a.get("end", patch.get("end"))]
        item = {
            "type": typ, "parent_ids": list(patch["note_ids"]),
            "note_ids": list(patch["note_ids"]),
            "region": [float(region[0]), float(region[1])],
            "packets": [c["note_id"]],
            "boundary": patch.get("boundary"),
            "reason": f"machine_{typ}_calibration",
            "repair_id": rid, "patch": patch,
            "authority": c["authority"],
            # m25-cal-2 (§10.1.5A-G2): no lyric guessing — the render
            # uses deterministic a/+ vowels; the source focus clip is
            # the real-melody reference.
            "lyric_contract": LYRIC_CONTRACT,
        }
        assign_identity(item)                 # target_key + item_id
        item["item_id"] = iid                 # cal-namespaced stable id
        win = phrase_window(item["region"], run["duration"], notes,
                            run.get("lrc_lines"), run.get("silences"))
        # a note may overlap the left window edge by < NO_CUT_TOL_S —
        # context_notes keeps it (its end is inside) and its relative
        # start would go negative at render time ("precedes part
        # anchor"). Back the edge up to the earliest overlapped start;
        # nothing is ever cut, context stays identical across options.
        for _ in range(4):
            ctx = context_notes(notes, win)
            early = [n["start"] for n in ctx
                     if n["start"] < win["start"] - 1e-9]
            if not early:
                break
            win = dict(win, start=round(min(early), 3))
        item["phrase"] = win
        item["phrase_key"] = f"{win['start']:.2f}-{win['end']:.2f}"
        ctx = context_notes(notes, win)
        opts = blind_order([
            {"candidate_id": "baseline",
             "score_patch": {"type": "identity"},
             "provenance": {"kind": "candidate0"}},
            {"candidate_id": f"machine_{typ}",
             "score_patch": patch,
             "provenance": {"kind": "machine_structure_candidate",
                            "repair_id": rid,
                            "authority": c["authority"]}},
        ], iid)
        item["options"] = opts
        item["context"] = ctx
        item["context_note_ids"] = [n["id"] for n in ctx]
        item["baseline_option"] = next(
            o["option_id"] for o in opts
            if o["candidate_id"] == "baseline")
        item["generation"] = 1
        item["plan_hash"] = plan_hash(
            iid, run["song_sha256"], run["run_id"], c0_sha, win,
            item["context_note_ids"], opts, rph,
            target_key_=item["target_key"])
        items.append(item)
    return items


# ------------------------------------------------------------- render IO

def render_contract_sha(run, rph_hash: str) -> str:
    """Identity of the review-render contract (§10.1.5A-G2): schema +
    lyric contract + render profile. A material renderer change → a
    different contract → previous QC verdict no longer applies."""
    return _sha({"schema": CALIB_SCHEMA, "lyric_contract": LYRIC_CONTRACT,
                 "render_profile_hash": rph_hash})


# ------------------------------------------------------------- QC verdict

def _verdict_path(run_dir: Path) -> Path:
    return calib_dir(run_dir) / "qc" / "verdict.json"


def load_verdict(run_dir: Path):
    p = _verdict_path(run_dir)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if d.get("schema") == CALIB_SCHEMA else None


def review_ready(run_dir: Path, contract_sha: str) -> bool:
    """§10.1.5A-G9 + Git-evidence rule: review-readiness defaults false
    and can only be set by an explicit pre-human QC PASS verdict whose
    required artifacts — including the verdict itself — are actually
    committed to Git. Render success or a local file never counts."""
    v = load_verdict(run_dir)
    if not (v and v.get("verdict") == "PASS"
            and v.get("contract_sha256") == contract_sha
            # recorded under the Git-evidence regime — a verdict
            # written before this rule existed never counts
            and (v.get("git_evidence_at_record") or {}).get("complete")):
        return False
    ev = git_evidence(run_dir, item_ids=v.get("sample_ids") or [],
                      include_qc=True)
    return bool(ev["complete"])


def write_verdict(run_dir: Path, verdict: str, contract_sha: str,
                  auditor: str, notes: str = "",
                  sample_ids=None,
                  require_git_evidence: bool = True) -> dict:
    """Record the pre-human QC verdict (append-only audit trail).
    A PASS is refused unless the sample packages + plan/state it covers
    are already committed to Git — the verdict then only takes effect
    (review_ready) after the qc files themselves are committed too."""
    run_dir = Path(run_dir)
    rec = {"schema": CALIB_SCHEMA,
           "verdict": "PASS" if verdict.upper() == "PASS" else "FAIL",
           "contract_sha256": contract_sha,
           "auditor": auditor, "notes": notes,
           "sample_ids": list(sample_ids or []),
           "recorded_at": _now()}
    if rec["verdict"] == "PASS" and require_git_evidence:
        ev = git_evidence(run_dir, item_ids=rec["sample_ids"],
                          include_qc=False)
        if not ev["complete"]:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A Git-evidence rule): "
                f"{len(ev['missing'])}/{ev['checked']} required "
                "artifacts are not committed to Git — e.g. "
                f"{ev['missing'][:4]}")
        rec["git_evidence_at_record"] = {
            "complete": True, "checked": ev["checked"]}
    _jwrite(_verdict_path(run_dir), rec)
    log = _verdict_path(run_dir).parent / "audit.jsonl"
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# ------------------------------------------------------------- semantic diff

def semantic_diff(item, c0_notes_by_id=None) -> dict:
    """§10.1.5A-G3/G4: machine-checkable proof that the Baseline option
    is Candidate-0 verbatim outside the target and the Candidate option
    differs ONLY by the declared patch. Rendered notes compare at
    score level (float tone); ustx integerization is uniform across
    options and recorded explicitly."""
    from .review.build import apply_patch
    from .review.render import option_notes, neutral_vowels
    ctx = item["context"]
    patch = item["patch"]
    target_ids = set(patch["note_ids"])
    base = apply_patch(ctx, {"type": "identity"})
    cand = apply_patch(ctx, patch)

    def produced(n):
        return n.get("split_child") is not None or n["id"] == "__merged__"

    def fields(n):
        return {"id": n["id"], "start": round(n["start"], 6),
                "end": round(n["end"], 6), "dur": round(n["dur"], 6),
                "tone": round(n["tone"], 6),
                "voiced": bool(n.get("voiced", True))}

    b_out = [n for n in base if n["id"] not in target_ids]
    c_out = [n for n in cand
             if n["id"] not in target_ids and not produced(n)]
    score_diff = []
    if [n["id"] for n in b_out] != [n["id"] for n in c_out]:
        score_diff.append({"kind": "note_set_changed_outside_target"})
    else:
        for bn, cn in zip(b_out, c_out):
            if fields(bn) != fields(cn):
                score_diff.append({"kind": "note_changed_outside_target",
                                   "id": bn["id"],
                                   "baseline": fields(bn),
                                   "candidate": fields(cn)})
    b_lyr = neutral_vowels(b_out)
    c_lyr = neutral_vowels(
        [n for n in cand
         if n["id"] not in target_ids and not produced(n)])
    lyric_diff = ([{"kind": "lyric_diff_outside_target"}]
                  if b_lyr != c_lyr else [])
    dev = max((abs(n["tone"] - round(n["tone"])) * 100.0
               for n in base + cand), default=0.0)
    c0_diff = []
    if c0_notes_by_id:
        for n in base:
            src = c0_notes_by_id.get(n["id"])
            if src is not None and (abs(src["start"] - n["start"]) > 1e-6
                                    or abs(src["dur"] - n["dur"]) > 1e-6
                                    or abs(src["tone"] - n["tone"]) > 1e-6):
                c0_diff.append({"id": n["id"], "context": fields(n),
                                "c0": src})
    return {
        "schema": CALIB_SCHEMA, "cal_item_id": item["item_id"],
        "repair_id": item["repair_id"],
        "lyric_contract": LYRIC_CONTRACT,
        "target": {"note_ids": sorted(target_ids),
                   "operation": patch["type"],
                   "patch_sha256": _sha(patch)},
        "outside_target": {
            "score_diff": score_diff, "lyric_diff": lyric_diff,
            "pitch_semantics": ("uniform: integer tone, no PITD "
                                "(diagnostic contract, identical "
                                "across options)")},
        "within_target": {
            "before": [fields(n) for n in base
                       if n["id"] in target_ids],
            "after": [fields(n) for n in cand if produced(n)
                      or n["id"] in target_ids]},
        "baseline_vs_c0": ("context slice identical" if not c0_diff
                           else c0_diff),
        "tone_integerization": {
            "max_deviation_cents": round(dev, 3),
            "note": ("uniform across options; canonical GAME ustx "
                     "also stores integer tones")},
        "canonical_audio_reference": None,
    }


# ------------------------------------------- target focus + signal QC (G5A/B)

SOURCE_FOCUS_PAD_S = 0.6
TARGET_FOCUS_PAD_S = 0.5
QC_DRIFT_RATIO_FLAG = 0.5        # out-of-target A/B diff rms / baseline rms
QC_LOUDNESS_RANGE = (0.7, 1.4)   # candidate/baseline full-phrase rms
QC_TARGET_F0_SEMITONES = 1.0     # both-options-vs-source median deviation
GIT_REQUIRED_ITEM_FILES = (
    "manifest.json", "OPTION_0.wav", "OPTION_1.wav",
    "OPTION_0.ustx", "OPTION_1.ustx",
    "BASELINE.ustx", "CANDIDATE.ustx",
    "SOURCE_FOCUS_original_mix.wav", "SOURCE_FOCUS_separated_vocal.wav",
    "semantic_diff.json",
    "BASELINE_TARGET.wav", "CANDIDATE_TARGET.wav",
    "signal_qc.json",
)


def _crop_rendered(src_wav: Path, dst: Path, t0: float, t1: float) -> dict:
    """§10.1.5A-G5A: crop [t0,t1] seconds from the ALREADY-RENDERED
    full-phrase wav — never re-render a short window for focus audio."""
    import soundfile as sf
    info = sf.info(str(src_wav))
    i0 = max(0, min(info.frames, int(round(t0 * info.samplerate))))
    i1 = max(i0, min(info.frames, int(round(t1 * info.samplerate))))
    with sf.SoundFile(str(src_wav)) as f:
        f.seek(i0)
        data = f.read(i1 - i0, always_2d=True)
    sf.write(str(dst), data, info.samplerate)
    return {"frames": i1 - i0, "sample_rate": info.samplerate}


def _f0_summary(wav_path: Path, t0: float = 0.0,
                t1: float | None = None) -> dict:
    """FCPE summary of one focus clip: medians + first/second-half medians
    (enough to see e.g. 62→64 vs 64→64). Extractor failure is recorded,
    never silently omitted."""
    import numpy as np
    try:
        from .analysis.f0 import extract_f0, segment_f0, hz_to_midi
        f0 = extract_f0(wav_path)
    except Exception as e:
        return {"error": f"f0_extractor_unavailable: {e}"}
    end = float(f0["times"][-1]) if len(f0["times"]) else 0.0
    seg = segment_f0(f0, t0, t1 if t1 is not None else end)
    hz = seg["f0_hz"][seg["voiced"]]
    n, tot = int(len(hz)), max(1, int(seg["n_frames"]))
    out = {"voiced_frames": n, "n_frames": int(seg["n_frames"]),
           "voiced_fraction": round(n / tot, 4),
           "midi_median": None, "midi_min": None, "midi_max": None,
           "first_half_midi_median": None,
           "second_half_midi_median": None}
    if n >= 3:
        midi = hz_to_midi(hz)
        h = max(1, n // 2)
        out.update({"midi_median": round(float(np.median(midi)), 3),
                    "midi_min": round(float(midi.min()), 3),
                    "midi_max": round(float(midi.max()), 3),
                    "first_half_midi_median":
                        round(float(np.median(midi[:h])), 3),
                    "second_half_midi_median":
                        round(float(np.median(midi[h:])), 3)})
    return out


def _segment_ab_ratio(b, c, i0: int, i1: int):
    """rms(b−c)/rms(b) over a sample range — the phrase-drift metric the
    pre-human Git audit used (~0.68×baseline RMS on phrase-wide diffs)."""
    import numpy as np
    sb, sc = b[i0:i1], c[i0:i1]
    if sb.size == 0:
        return None
    rb = float(np.sqrt(np.mean(sb ** 2)))
    if rb < 1e-6:
        return None
    return round(float(np.sqrt(np.mean((sb - sc) ** 2))) / rb, 4)


def signal_qc(man: dict, idir: Path) -> dict:
    """§10.1.5A-G5B: machine-readable signal audit of one rendered item.

    Crops BASELINE/CANDIDATE_TARGET.wav from the real renders (G5A),
    measures full-phrase level/timing drift + pre/target/post A/B diff
    ratios, summarizes target-window F0 for source/baseline/candidate,
    and auto-flags conditions that disqualify human review (phrase-wide
    bleed, loudness drift, both options off-source)."""
    import numpy as np
    import soundfile as sf
    from .review.render import _file_sha
    idir = Path(idir)
    cal = man["calibration"]
    base_id, cand_id = cal["baseline_option"], cal["candidate_role"]
    owav = {o["option_id"]: o["wav"] for o in man["options"]}
    region = [float(x) for x in man["target_group"]["region"]]
    ph_start = float(man["phrase"]["start"])
    t0 = max(0.0, region[0] - TARGET_FOCUS_PAD_S)
    t1 = region[1] + TARGET_FOCUS_PAD_S
    focus = {}
    for oid, name in ((base_id, "BASELINE_TARGET.wav"),
                      (cand_id, "CANDIDATE_TARGET.wav")):
        focus[name] = _crop_rendered(idir / owav[oid], idir / name,
                                     t0 - ph_start, t1 - ph_start)
    b, sr = sf.read(str(idir / owav[base_id]), dtype="float32",
                    always_2d=True)
    c, _ = sf.read(str(idir / owav[cand_id]), dtype="float32",
                   always_2d=True)
    n = min(len(b), len(c))
    b, c = b[:n], c[:n]
    reg0 = max(0, min(n, int((region[0] - ph_start) * sr)))
    reg1 = max(reg0, min(n, int((region[1] - ph_start) * sr)))

    def rms(x):
        return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0

    def peak(x):
        return float(np.abs(x).max()) if x.size else 0.0

    def sil(x):
        return round(float((np.abs(x) < 0.0032).mean()), 4)

    rb, rc = rms(b), rms(c)
    loud = rc / rb if rb > 1e-6 else None
    pre = _segment_ab_ratio(b, c, 0, reg0)
    tgt = _segment_ab_ratio(b, c, reg0, reg1)
    post = _segment_ab_ratio(b, c, reg1, n)
    flags = []
    for nm, v in (("pre_target", pre), ("post_target", post)):
        if v is not None and v > QC_DRIFT_RATIO_FLAG:
            flags.append(f"{nm}_ab_drift:{v}")
    if loud is not None and not QC_LOUDNESS_RANGE[0] <= loud \
            <= QC_LOUDNESS_RANGE[1]:
        flags.append(f"option_loudness_drift:{round(loud, 3)}")
    f0_b = _f0_summary(idir / "BASELINE_TARGET.wav")
    f0_c = _f0_summary(idir / "CANDIDATE_TARGET.wav")
    foc = idir / "SOURCE_FOCUS_separated_vocal.wav"
    if foc.exists():
        fs = max(0.0, region[0] - SOURCE_FOCUS_PAD_S)
        f0_s = _f0_summary(foc, t0 - fs, t1 - fs)
    else:
        f0_s = {"error": "missing SOURCE_FOCUS_separated_vocal.wav"}
    sm = f0_s.get("midi_median")
    mism = [nm for nm, f in (("baseline", f0_b), ("candidate", f0_c))
            if sm is not None and f.get("midi_median") is not None
            and abs(f["midi_median"] - sm) > QC_TARGET_F0_SEMITONES]
    if len(mism) == 2:
        flags.append("both_options_target_f0_mismatch")
    return {
        "schema": CALIB_SCHEMA,
        "cal_item_id": man["review_item_id"],
        "repair_id": cal["repair_id"],
        "sample_rate": sr, "duration": round(n / sr, 4),
        "baseline_rms": round(rb, 6), "candidate_rms": round(rc, 6),
        "baseline_peak": round(peak(b), 6),
        "candidate_peak": round(peak(c), 6),
        "silence_fraction": {"baseline": sil(b), "candidate": sil(c)},
        "declared_region": region,
        "target_window": {"absolute": [round(t0, 4), round(t1, 4)],
                          "phrase_relative":
                              [round(t0 - ph_start, 4),
                               round(t1 - ph_start, 4)],
                          "pad_s": TARGET_FOCUS_PAD_S},
        "pre_target_ab_diff_rms_ratio": pre,
        "target_ab_diff_rms_ratio": tgt,
        "post_target_ab_diff_rms_ratio": post,
        "option_loudness_ratio": round(loud, 4) if loud else None,
        "source_target_f0_summary": f0_s,
        "baseline_target_f0_summary": f0_b,
        "candidate_target_f0_summary": f0_c,
        "target_focus_sha256": _sha({
            "baseline": _file_sha(idir / "BASELINE_TARGET.wav"),
            "candidate": _file_sha(idir / "CANDIDATE_TARGET.wav")}),
        "target_focus_is_primary": True,
        "auto_flags": flags,
        "auto_review_ready": not flags,
    }


def augment_item(idir: Path) -> dict:
    """(Re)generate the G5A target-focus crops + G5B signal_qc.json for
    one already-rendered item. Reads OPTION wavs only — never re-renders,
    never touches manifest/aph (the decision authority)."""
    idir = Path(idir)
    man = json.loads((idir / "manifest.json").read_text(encoding="utf-8"))
    qc = signal_qc(man, idir)
    _jwrite(idir / "signal_qc.json", qc)
    return qc


def augment_calibration(run_dir: Path, only=None, progress=print) -> dict:
    """G5A/G5B pass over an existing store (or a fresh build): every
    rendered item gets target-focus crops + signal_qc.json."""
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    plan_p = calib_dir(run_dir) / "plan.json"
    if not plan_p.exists():
        raise RuntimeError("no calibration plan — build packages first")
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    keep = set(only or [])
    out = {}
    for it in plan["items"]:
        iid = it["cal_item_id"]
        if keep and iid not in keep and it["repair_id"] not in keep \
                and it["note_id"] not in keep:
            continue
        idir = calib_dir(run_dir) / "items" / iid
        if not (idir / "manifest.json").exists():
            continue
        qc = augment_item(idir)
        out[iid] = qc["auto_flags"]
        progress(f"  {iid}: auto_flags={qc['auto_flags'] or 'none'}")
    return {"augmented": sorted(out), "flags": out}


# --------------------------------------------- Git evidence rule (§10.1.5A)

def _git_tracked_set(run_dir: Path):
    """Files committed to Git under the calibration store, calib-dir-
    relative posix paths; None when unavailable/not a worktree."""
    import subprocess
    cdir = calib_dir(run_dir).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=cdir, capture_output=True, text=True,
                             timeout=15)
        if top.returncode != 0:
            return None
        root = Path(top.stdout.strip()).resolve()
        prefix = cdir.relative_to(root).as_posix() + "/"
        out = subprocess.run(["git", "ls-files", "-z", "--", prefix],
                             cwd=root, capture_output=True, timeout=60)
        if out.returncode != 0:
            return None
        raw = out.stdout.decode("utf-8", "replace").split("\0")
        return {p[len(prefix):] for p in raw
                if p.startswith(prefix)}
    except Exception:
        return None


def git_evidence(run_dir: Path, item_ids=None,
                 include_qc: bool = True) -> dict:
    """§10.1.5A hard rule — 'local file exists' / 'agent says generated'
    never counts; only files actually committed to Git are acceptance
    evidence. Reports which required artifacts are missing from Git."""
    cdir = calib_dir(run_dir)
    if item_ids is None:
        items_dir = cdir / "items"
        item_ids = sorted(d.name for d in items_dir.iterdir()
                          if d.is_dir()) if items_dir.exists() else []
    expected = ["plan.json", "state.json"]
    if include_qc:
        expected += ["qc/verdict.json", "qc/audit.jsonl"]
    for iid in item_ids:
        expected += [f"items/{iid}/{f}" for f in GIT_REQUIRED_ITEM_FILES]
    tracked = _git_tracked_set(run_dir)
    if tracked is None:
        return {"complete": False, "git": "unavailable_or_not_a_worktree",
                "missing": expected, "checked": len(expected),
                "item_ids": list(item_ids)}
    missing = [e for e in expected if e not in tracked]
    return {"complete": not missing, "git": "ok",
            "missing": missing, "checked": len(expected),
            "item_ids": list(item_ids)}


def build_calibration(run_dir: Path, cfg=None, render=True, only=None,
                      progress=print) -> dict:
    """Build (and render) phrase A/B packages for machine structure
    candidates. m25-cal-2 (§10.1.5A): a FULL batch (no `only`) requires
    a pre-human QC PASS verdict for the current render contract —
    samples (only=...) are the pre-QC path."""
    from .review.render import (load_run, render_item, item_manifest,
                                _clip, render_provenance, _file_sha)
    from .review.build import (render_profile, render_profile_hash)
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    run = load_run(run_dir)
    profile = render_profile(
        template_sha=_file_sha(
            Path(__file__).resolve().parents[2]
            / "configs" / "ustx_template.yaml"))
    rph = {"profile": profile, "hash": render_profile_hash(profile)}
    contract_sha = render_contract_sha(run, rph["hash"])
    if not only and not review_ready(run_dir, contract_sha):
        raise RuntimeError(
            "full calibration batch blocked (§10.1.5A-G10): no "
            "pre-human QC PASS verdict for contract "
            f"{contract_sha[:16]} — build samples with --items first, "
            "audit them, then structure-calib-qc --pass")
    items = plan_calibration(run, rph=rph["hash"])
    if only:
        keep = set(only)
        items = [i for i in items if i["item_id"] in keep
                 or i["repair_id"] in keep or i["packets"][0] in keep]
    cdir = calib_dir(run_dir)
    c0_by_id = {f"note_{i:04d}": n
                for i, n in enumerate(run["baseline_notes"])}
    prov = render_provenance(cfg) if render else None
    planned, src_rendered = [], {}
    for it in items:
        pkey, ph = it["phrase_key"], it["phrase"]
        pdir = cdir / "phrases" / pkey
        refs = None
        if render:
            if pkey not in src_rendered:
                refs = {
                    "original_mix": _clip(
                        run["original_wav"],
                        pdir / "SOURCE_PHRASE_original_mix.wav",
                        ph["start"], ph["end"]),
                    "separated_vocal": _clip(
                        run["vocals_wav"],
                        pdir / "SOURCE_PHRASE_separated_vocal.wav",
                        ph["start"], ph["end"])}
                for r in refs.values():
                    r["path"] = f"../../phrases/{pkey}/{r['path']}"
                src_rendered[pkey] = refs
                progress(f"  source phrase {pkey} "
                         f"({ph['end'] - ph['start']:.2f}s, "
                         f"{ph['boundary_source']})")
            else:
                refs = src_rendered[pkey]
        idir = cdir / "items" / it["item_id"]
        rres = None
        if render:
            progress(f"  rendering {it['item_id']} "
                     f"({it['type']}, {len(it['options'])} options)")
            rres = render_item(cfg, idir, it, run["chars"])
            # §10.1.5A-G4: focus clips of the contested region from the
            # SOURCE audio — the original melody is the ground truth.
            reg = it["region"]
            _clip(run["original_wav"],
                  idir / "SOURCE_FOCUS_original_mix.wav",
                  max(0.0, reg[0] - SOURCE_FOCUS_PAD_S),
                  reg[1] + SOURCE_FOCUS_PAD_S)
            _clip(run["vocals_wav"],
                  idir / "SOURCE_FOCUS_separated_vocal.wav",
                  max(0.0, reg[0] - SOURCE_FOCUS_PAD_S),
                  reg[1] + SOURCE_FOCUS_PAD_S)
        man = item_manifest(run, it, "structure-calibration", rph,
                            refs, rres, provenance=prov)
        # calibration-specific manifest fields (append, never reshape)
        man["schema"] = CALIB_SCHEMA
        man["calibration"] = {
            "repair_id": it["repair_id"],
            "patch_sha256": _sha(it["patch"]),
            "candidate_role": next(
                o["option_id"] for o in it["options"]
                if o["candidate_id"] != "baseline"),
            "baseline_option": it["baseline_option"],
            "lyric_contract": LYRIC_CONTRACT,
            "contract_sha256": contract_sha,
            "choices": list(CHOICES),
        }
        diff = semantic_diff(it, c0_by_id)
        _jwrite(idir / "semantic_diff.json", diff)
        man["calibration"]["semantic_diff_sha256"] = _sha(diff)
        # unblinded copies for pre-human QC — OPTION_* files remain the
        # decision authority; these are review aids only.
        if render and idir.exists():
            base_opt = man["baseline_option"]
            cand_opt = man["calibration"]["candidate_role"]
            for opt, name in ((base_opt, "BASELINE.ustx"),
                              (cand_opt, "CANDIDATE.ustx")):
                src_ustx = idir / f"{opt}.ustx"
                if src_ustx.exists():
                    (idir / name).write_bytes(src_ustx.read_bytes())
        mpath = idir / "manifest.json"
        _jwrite(mpath, man)
        qc_flags = None
        if render and man["package_state"] == "valid":
            qc_flags = augment_item(idir)["auto_flags"]
        planned.append({"cal_item_id": it["item_id"],
                        "repair_id": it["repair_id"],
                        "note_id": it["packets"][0],
                        "type": it["type"], "phrase": it["phrase"],
                        "phrase_key": pkey,
                        "plan_hash": it["plan_hash"],
                        "audio_package_hash": man["audio_package_hash"],
                        "package_state": man["package_state"],
                        "signal_qc_flags": qc_flags,
                        "semantic_diff_sha256": _sha(diff),
                        "manifest": str(mpath)})
    _jwrite(cdir / "plan.json",
            {"schema": CALIB_SCHEMA, "created_at": _now(),
             "diagnostic_run_id": run["run_id"],
             "candidate0_sha256": run["candidate0_sha256"],
             "lyric_contract": LYRIC_CONTRACT,
             "contract_sha256": contract_sha,
             "items": planned})
    progress(f"calibration: {len(planned)} items → {cdir}")
    return {"items": planned, "contract_sha256": contract_sha}


# ------------------------------------------------------------- decisions

def _decisions_path(run_dir: Path) -> Path:
    return calib_dir(run_dir) / "decisions.json"


def load_decisions(run_dir: Path) -> dict:
    ensure_calib_authority(Path(run_dir))
    p = _decisions_path(run_dir)
    if not p.exists():
        return {"schema": CALIB_SCHEMA, "revisions": []}
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("schema") != CALIB_SCHEMA:
        raise RuntimeError(
            f"unsupported calibration decisions schema: {d.get('schema')}")
    return d


def current_decision(run_dir: Path, repair_id: str):
    """Latest non-superseded decision for one repair_id."""
    revs = [r for r in load_decisions(run_dir)["revisions"]
            if r.get("repair_id") == repair_id
            and not r.get("superseded_by")]
    return revs[-1] if revs else None


def _find_manifest(run_dir: Path, cal_item_id: str):
    p = calib_dir(run_dir) / "items" / cal_item_id / "manifest.json"
    return p if p.exists() else None


def decide(run_dir: Path, cal_item_id: str, choice: str):
    """Append a calibration decision. `choice` is the blinded OPTION_i
    (or equivalent/none_correct); the manifest maps it to the
    baseline/candidate role so the recorded semantics are always
    role-based — the reviewer never needs to know which is which.
    """
    from .review.render import verify_package
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    mpath = _find_manifest(run_dir, cal_item_id)
    if mpath is None:
        raise RuntimeError(f"no calibration package for {cal_item_id}")
    man = json.loads(mpath.read_text(encoding="utf-8"))
    if man.get("schema") != CALIB_SCHEMA:
        raise RuntimeError(
            f"legacy package schema {man.get('schema')} is not "
            f"decidable under {CALIB_SCHEMA} — m25-cal-1 packages are "
            "audit-only")
    ok, why = verify_package(man, mpath.parent)
    if not ok:
        raise RuntimeError(f"package not decidable: {why}")
    cal = man["calibration"]
    opts = {o["option_id"]: o for o in man["options"]}
    if choice in opts:
        role = ("baseline" if opts[choice]["candidate_id"] == "baseline"
                else "split")
        decided_option = choice
    elif choice in ("equivalent", "none_correct"):
        role = choice
        decided_option = None
    else:
        raise RuntimeError(f"bad choice {choice} — one of "
                           f"{sorted(opts) + ['equivalent', 'none_correct']}")
    prior = current_decision(run_dir, cal["repair_id"])
    rev = {
        "revision_id": "calrev-" + _sha({
            "repair_id": cal["repair_id"], "role": role,
            "aph": man["audio_package_hash"], "at": _now()})[:16],
        "cal_item_id": cal_item_id,
        "repair_id": cal["repair_id"],
        "note_id": man["target_group"]["packets"][0],
        "patch_sha256": cal["patch_sha256"],
        "audio_package_hash": man["audio_package_hash"],
        "choice": role,
        "decided_option": decided_option,
        "option_role": (opts.get(decided_option) or {})
                       .get("candidate_id"),
        "outcome": OUTCOME[role],
        "decided_at": _now(),
        "superseded_by": None,
    }
    d = load_decisions(run_dir)
    if prior is not None:
        prior["superseded_by"] = rev["revision_id"]
    d["revisions"].append(rev)
    _jwrite(_decisions_path(run_dir), d)
    rebuild_calibration_state(run_dir)
    return rev


def calibration_authorized(run_dir: Path, repair_id: str, patch):
    """The M2.5 machine-authority gate (§10.1.5/§10.1.7-C): a machine
    structure candidate applies ONLY while a fresh
    human_confirmed_machine_split decision binds this exact repair_id +
    patch content AND its recorded package still verifies byte-for-byte.
    Any other outcome — false_positive / no_benefit / unresolved /
    superseded / missing — is no authority (candidate, never repair)."""
    rev = current_decision(run_dir, repair_id)
    if rev is None or rev.get("outcome") != \
            "human_confirmed_machine_split":
        return None
    if rev.get("patch_sha256") != _sha(patch):
        return None
    from .review.render import verify_package
    mpath = _find_manifest(run_dir, rev["cal_item_id"])
    if mpath is None:
        return None
    man = json.loads(mpath.read_text(encoding="utf-8"))
    if man.get("schema") != CALIB_SCHEMA:
        return None                        # legacy package — audit-only
    if man.get("audio_package_hash") != rev["audio_package_hash"]:
        return None
    ok, _ = verify_package(man, mpath.parent)
    return rev if ok else None


def rebuild_calibration_state(run_dir: Path) -> dict:
    """Derived summary — always recomputable from decisions + plan."""
    ensure_calib_authority(Path(run_dir))
    d = load_decisions(run_dir)
    plan_p = calib_dir(run_dir) / "plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8")) \
        if plan_p.exists() else {"items": []}
    counts = {v: 0 for v in OUTCOME.values()}
    reviewed, pending = [], []
    for it in plan["items"]:
        rev = current_decision(run_dir, it["repair_id"])
        if rev is None:
            pending.append(it["cal_item_id"])
        else:
            reviewed.append({"cal_item_id": it["cal_item_id"],
                             "repair_id": it["repair_id"],
                             "outcome": rev["outcome"],
                             "revision_id": rev["revision_id"]})
            counts[rev["outcome"]] += 1
    confirmed = counts["human_confirmed_machine_split"]
    ev = git_evidence(run_dir)
    state = {
        "schema": CALIB_SCHEMA, "rebuilt_at": _now(),
        "total_machine_split_candidates": len(plan["items"]),
        "reviewed_count": len(reviewed),
        "split_preferred_count": confirmed,
        "baseline_preferred_count":
            counts["machine_structure_false_positive"],
        "equivalent_count": counts["no_demonstrated_benefit"],
        "none_correct_count": counts["unresolved"],
        "measured_song_level_precision":
            (confirmed / len(reviewed)) if reviewed else None,
        "pending": pending, "reviewed": reviewed,
        "contract_sha256": plan.get("contract_sha256"),
        "git_evidence": {k: ev[k] for k in
                         ("complete", "git", "checked")} | \
                        {"missing_count": len(ev["missing"])},
        "review_ready": review_ready(
            run_dir, plan.get("contract_sha256") or ""),
    }
    _jwrite(calib_dir(run_dir) / "state.json", state)
    return state
