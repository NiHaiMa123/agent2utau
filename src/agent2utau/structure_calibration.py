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
    """§10.1.5A-G9: review-readiness defaults false and can only be set
    by an explicit pre-human QC verdict — never by render success."""
    v = load_verdict(run_dir)
    return bool(v and v.get("verdict") == "PASS"
                and v.get("contract_sha256") == contract_sha)


def write_verdict(run_dir: Path, verdict: str, contract_sha: str,
                  auditor: str, notes: str = "",
                  sample_ids=None) -> dict:
    """Record the pre-human QC verdict (append-only audit trail)."""
    run_dir = Path(run_dir)
    rec = {"schema": CALIB_SCHEMA,
           "verdict": "PASS" if verdict.upper() == "PASS" else "FAIL",
           "contract_sha256": contract_sha,
           "auditor": auditor, "notes": notes,
           "sample_ids": list(sample_ids or []),
           "recorded_at": _now()}
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
                  max(0.0, reg[0] - 0.6), reg[1] + 0.6)
            _clip(run["vocals_wav"],
                  idir / "SOURCE_FOCUS_separated_vocal.wav",
                  max(0.0, reg[0] - 0.6), reg[1] + 0.6)
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
        planned.append({"cal_item_id": it["item_id"],
                        "repair_id": it["repair_id"],
                        "note_id": it["packets"][0],
                        "type": it["type"], "phrase": it["phrase"],
                        "phrase_key": pkey,
                        "plan_hash": it["plan_hash"],
                        "audio_package_hash": man["audio_package_hash"],
                        "package_state": man["package_state"],
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
        "review_ready": review_ready(
            run_dir, plan.get("contract_sha256") or ""),
    }
    _jwrite(calib_dir(run_dir) / "state.json", state)
    return state
