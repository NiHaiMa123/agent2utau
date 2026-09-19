"""§G5N.3 lyric-constrained forced alignment — timing/alignment
evidence family B.

family A = current Whisper-derived char alignment (force_align DTW).
family B = this module: MMS_FA CTC aligner over romanized (toneless
pinyin) syllables of the KNOWN lyric sequence against the separated
source vocal.

§G5N.3 authority correction: the KNOWN lyric sequence is the lexical
identity authority — it is INJECTED as the forced-alignment target,
so "the aligner found a span for token i" is NOT independent
recognition of that Han character (many homophones share a syllable;
the text was handed to the aligner). What family B independently
measures is TIMING/BOUNDARY under the known-token constraint:
where each known token's acoustics land, at what CTC confidence.
The old `identity_*` verdict names are therefore retired from
authority — a forced-alignment agreement can only ever support
alignment/timing, never lexical identity.

Output contract (persisted, auditable):
  aligner_family / aligner_version / model+lexicon provenance /
  source_wav_sha256 / lyric_sequence_sha256
  per token: token_index, char, pinyin, start/end (wav-relative s),
  confidence (mean CTC span log-prob), boundary uncertainty,
  status aligned|skipped|inserted

Waveform-class evidence (`_onset_span_evidence`) stays a supporting
acoustic diagnostic — likewise never identity authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ALIGNER_FAMILY = "mms_fa_ctc_uroman"
ALIGNER_VERSION = "ifa2"
# material aligner/model/lexicon/config change → bump ALIGNER_VERSION
# (dependent inventory/package evidence becomes stale, §G5N.3-N40)

# CTC emission frame period for MMS_FA at 16 kHz (encoder stride 320).
ALIGNER_FRAME_S = 0.02
# Timing-disagreement safety bound for alignment adjudication — a
# cap, never a pass target (§G5N.3 tolerance semantics).
ALIGN_TIMING_CAP_S = 0.30
# Minimum mean CTC span log-prob for a token to count as confidently
# aligned; below → low-confidence → alignment_unresolved
# (fail-closed).
MIN_TOKEN_LOGPROB = -4.0

_MODEL = None


def _sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def romanize_syllables(text: str):
    """汉字 → toneless romanized syllables matching the MMS_FA uroman
    label set (ASCII a–z). Tone marks stripped; ü → v (machine pinyin).
    Returns one syllable per Han char, or None on failure — the caller
    fails closed, never guesses."""
    try:
        from pypinyin import pinyin, Style
    except Exception:
        return None
    try:
        syls = [t[0] for t in pinyin(text, style=Style.NORMAL)]
    except Exception:
        return None
    out = []
    for ch, s in zip(text, syls):
        s = s.strip().lower().replace("ü", "v").replace("u:", "v")
        if not s or any(c < "a" or c > "z" for c in s):
            return None
        out.append(s)
    return out


def lyric_sequence_sha(chars) -> str:
    """Canonical hash of the KNOWN lyric token sequence (text only —
    the alignment constraint / identity namespace, never acoustic
    evidence itself)."""
    seq = "".join(c["char"] for c in chars if c.get("char"))
    return hashlib.sha256(seq.encode("utf-8")).hexdigest()


def _model():
    global _MODEL
    if _MODEL is None:
        import torchaudio
        _MODEL = torchaudio.pipelines.MMS_FA.get_model().eval()
    return _MODEL


def forced_align(wav, chars):
    """Run family-B forced alignment.

    wav: Path (or None) to the separated source vocal clip.
    chars: KNOWN lyric sequence for the clip — list of dicts with at
           least "char" (text only; their timing is NOT used — that is
           family-A's claim, not a constraint).

    Returns the contract dict. On any missing input / model failure /
    unalignable text → {"available": False, "reason": ...} — callers
    must treat that as alignment_unresolved, never as evidence."""
    doc = {"aligner_family": ALIGNER_FAMILY,
           "aligner_version": ALIGNER_VERSION,
           "available": False, "reason": None, "tokens": []}
    wav = Path(wav) if wav else None
    if wav is None or not wav.exists():
        doc["reason"] = "source_wav_missing"
        return doc
    doc["source_wav_sha256"] = _sha256(wav)
    doc["lyric_sequence_sha256"] = lyric_sequence_sha(chars)
    text = "".join(c["char"] for c in chars)
    syls = romanize_syllables(text)
    if not syls:
        doc["reason"] = "romanization_failed"
        return doc
    try:
        import torch
        import torchaudio
        import soundfile as sf
        bundle = torchaudio.pipelines.MMS_FA
        model = _model()
        x, sr = sf.read(str(wav), dtype="float32")
        if getattr(x, "ndim", 1) > 1:
            x = x.mean(axis=1)
        waveform = torch.from_numpy(x)[None]
        if sr != bundle.sample_rate:
            waveform = torchaudio.functional.resample(
                waveform, sr, bundle.sample_rate)
        with torch.inference_mode():
            emission, _ = model(waveform)
        labels = bundle.get_labels(star="*")
        dic = bundle.get_dict(star="*")
        toks = []
        for i, s in enumerate(syls):
            if i:
                toks.append(dic["*"])
            toks += [dic[c] for c in s]
        targets = torch.tensor([toks], dtype=torch.int32)
        align, scores = torchaudio.functional.forced_align(
            emission.log_softmax(-1), targets)
        tok_spans = torchaudio.functional.merge_tokens(
            align[0], scores[0])
        ratio = waveform.shape[1] / emission.shape[1] \
            / bundle.sample_rate
        groups, cur = [], []
        for ts in tok_spans:
            if labels[ts.token] == "*":
                groups.append(cur)
                cur = []
            else:
                cur.append(ts)
        groups.append(cur)
        if len(groups) != len(syls):
            doc["reason"] = "alignment_group_mismatch"
            return doc
        doc["model"] = "ctc_alignment_mling_uroman"
        doc["lexicon"] = "pypinyin-normal-toneless"
        doc["model_provenance"] = {
            "bundle": "torchaudio.pipelines.MMS_FA",
            "sample_rate": bundle.sample_rate,
            "frame_s": ALIGNER_FRAME_S,
            "n_params": int(sum(p.numel()
                                for p in model.parameters())),
        }
        for i, (g, s) in enumerate(zip(groups, syls)):
            conf = sum(t.score for t in g) / len(g)
            doc["tokens"].append({
                "token_index": i,
                "char": chars[i]["char"],
                "pinyin": s,
                "phoneme_sequence": None,
                "start": round(g[0].start * ratio, 4),
                "end": round(g[-1].end * ratio, 4),
                "confidence": round(conf, 4),
                "boundary_uncertainty_s": ALIGNER_FRAME_S,
                "status": ("aligned" if conf >= MIN_TOKEN_LOGPROB
                           else "skipped"),
            })
        doc["available"] = True
        doc["reason"] = None
        return doc
    except Exception as exc:  # model/runtime failure → fail closed
        doc["reason"] = f"aligner_unavailable:{type(exc).__name__}"
        return doc


def alignment_adjudicate(align_doc, chars):
    """Adjudicate each char's ALIGNMENT/TIMING against family-B
    output — never its lexical identity (§G5N.3: the known lyric
    sequence is already the lexical authority; both families merely
    measure where each KNOWN token's acoustics land).

    chars: the SAME known-lyric sequence list used for alignment —
           entries carry family-A (Whisper) char/start/end/probability
           in wav-relative seconds.

    Per char verdict:
      alignment_supported    — family-B aligns the same token index,
                               monotonic order, boundary disagreement
                               within evidence-derived tolerance
      alignment_order_conflict — family-B places the token at a
                               non-monotonic / mismatched position
      measurement_ambiguous  — same token but A/B timing
                               disagreement exceeds tolerance
      alignment_unresolved   — family-B unavailable / low confidence
                               / missing token

    Tolerance is evidence-derived: base = 3× frame period plus the
    phrase's own confident-token disagreement dispersion (median abs
    deviation), hard-capped by ALIGN_TIMING_CAP_S."""
    n = len(chars)
    verdicts = [{"verdict": "alignment_unresolved",
                 "dev_start_s": None,
                 "famB_start": None, "famB_end": None,
                 "famB_confidence": None, "tolerance_s": None}
                for _ in range(n)]
    if not align_doc or not align_doc.get("available"):
        return {"available": False, "verdicts": verdicts,
                "reason": (align_doc or {}).get("reason")}
    toks = align_doc.get("tokens") or []
    if len(toks) != n:
        return {"available": True, "verdicts": verdicts,
                "reason": "token_count_mismatch"}

    devs = []
    for c, t in zip(chars, toks):
        if c.get("start") is not None and t.get("status") == "aligned":
            devs.append(abs(float(t["start"]) - float(c["start"])))
    disp = 0.0
    if len(devs) >= 3:
        ds = sorted(devs)
        disp = ds[len(ds) // 2]
    tol = min(ALIGN_TIMING_CAP_S,
              3 * ALIGNER_FRAME_S + disp)

    prev_end = -1e9
    for i, (c, t) in enumerate(zip(chars, toks)):
        v = verdicts[i]
        v["famB_start"] = t.get("start")
        v["famB_end"] = t.get("end")
        v["famB_confidence"] = t.get("confidence")
        v["tolerance_s"] = round(tol, 4)
        if t.get("status") != "aligned":
            v["verdict"] = "alignment_unresolved"
            continue
        if t["start"] < prev_end - 1e-4:
            v["verdict"] = "alignment_order_conflict"
            continue
        prev_end = t["end"]
        if c.get("start") is None:
            v["verdict"] = "alignment_unresolved"
            continue
        dev = abs(float(t["start"]) - float(c["start"]))
        v["dev_start_s"] = round(dev, 4)
        v["verdict"] = ("alignment_supported" if dev <= tol
                        else "measurement_ambiguous")
    return {"available": True, "verdicts": verdicts, "reason": None,
            "tolerance_s": round(tol, 4)}


# §G5N.3 audit back-compat: rlv10 artifacts persist the old
# identity_* names — readable for audit, never consumed as current
# authority. These aliases keep historical tooling unbroken.
identity_align = forced_align
identity_adjudicate = alignment_adjudicate
IDENTITY_TIMING_CAP_S = ALIGN_TIMING_CAP_S


# ------------------------------------------------- §G5N.5 boundary stability
#
# Whisper target-token probability is an acoustic-quality feature of
# the constrained alignment — it is NOT a boundary-confidence measure
# (multi-Hanzi words share one probability and split their span evenly
# across chars). Boundary authority must instead be proven by
# perturbation stability: the same constrained alignment is re-run
# under several LEGAL context windows (same lyric sequence, varied
# audio crops) and the boundary jitter is measured. Multi-context
# outputs of the same Whisper model are ONE measurement family —
# they can never count as N independent votes.

# boundary jitter bound: the same physical agreement bound used for
# cross-family onset↔MMS comparison (sung-consonant lead-in + frame
# resolution) — observed on the calibration set as a bimodal gap
# (stable tokens jitter ~0.01–0.07s, unstable ~0.45s+). Evidence-
# derived, persisted in the stability doc, never tuned per case.
WHISPER_STABLE_JITTER_S = 0.12
# minimum valid contexts required before a stability verdict exists
WHISPER_STABILITY_MIN_CTX = 3
# context pads (left, right) around the token span — all keep the
# same known lyric sequence and exact coverage; none is chosen to
# favour a result
WHISPER_STABILITY_PADS = (
    (0.45, 0.45), (0.30, 0.55), (0.55, 0.30),
    (0.65, 0.40), (0.35, 0.60))


def whisper_boundary_stability(vocals_wav, text, span0, span1,
                               n_tokens, align_fn=None, pads=None):
    """Perturbation-based Whisper boundary stability (§G5N.5).

    Re-runs the constrained Whisper alignment of the SAME known lyric
    sequence on `vocals_wav` under several legal context crops around
    [span0, span1] and measures per-token boundary jitter. Returns a
    persisted doc:

      contexts[]  per-crop result (window, validity, failure_reason)
      tokens[]    per-token {start_median, end_median, start_jitter,
                             end_jitter, n_valid, stability_status}
      family      "whisper_attention_dtw_stability" (ONE family)
      jitter_bound_s / min_valid_contexts (the evidence-derived rule)
      provenance  vocals_wav_sha256 / lyric_sequence_sha256

    align_fn is injectable for tests — signature
    (wav, text, t0, t1) -> list of {char,start,end,probability}.
    """
    from .analysis.lyrics import force_align as _fa
    fn = align_fn or _fa
    pads = pads or WHISPER_STABILITY_PADS
    contexts, per_token = [], [[] for _ in range(n_tokens)]
    for ci, (lp, rp) in enumerate(pads):
        t0, t1 = max(0.0, span0 - lp), span1 + rp
        ctx = {"context_id": f"pad_{lp:.2f}_{rp:.2f}",
               "source_start": round(t0, 4), "source_end": round(t1, 4),
               "valid": False, "failure_reason": None}
        try:
            if not 0 < t1 - t0 <= 29:
                raise ValueError("window_out_of_range")
            al = fn(vocals_wav, text, t0, t1)
            if len(al) != n_tokens:
                raise ValueError("token_count_mismatch")
            if any(al[k]["start"] < al[k - 1]["start"] - 1e-3
                   for k in range(1, n_tokens)):
                raise ValueError("non_monotonic")
            ctx["valid"] = True
            for i, c in enumerate(al):
                per_token[i].append(
                    (float(c["start"]), float(c["end"]),
                     float(c.get("probability") or 0.0), ci))
        except Exception as e:  # noqa: BLE001 — recorded, never fatal
            ctx["failure_reason"] = f"{type(e).__name__}:{e}"
        contexts.append(ctx)
    n_valid = sum(1 for c in contexts if c["valid"])
    import statistics as st

    def _med(v):
        return round(st.median(v), 4) if v else None

    tokens = []
    for i in range(n_tokens):
        obs = per_token[i]
        starts = [o[0] for o in obs]
        ends = [o[1] for o in obs]
        sj = round(max(starts) - min(starts), 4) if starts else None
        ej = round(max(ends) - min(ends), 4) if ends else None
        if not obs or n_valid < WHISPER_STABILITY_MIN_CTX:
            status = "insufficient"
        elif sj is not None and ej is not None \
                and sj <= WHISPER_STABLE_JITTER_S \
                and ej <= WHISPER_STABLE_JITTER_S:
            status = "stable"
        else:
            status = "unstable"
        tokens.append({
            "token_index": i,
            "start_median": _med(starts), "end_median": _med(ends),
            "start_jitter": sj, "end_jitter": ej,
            "n_valid": len(obs), "stability_status": status})
    import json as _json
    return {
        "family": "whisper_attention_dtw_stability",
        "contexts": contexts,
        "tokens": tokens,
        "n_valid_contexts": n_valid,
        "jitter_bound_s": WHISPER_STABLE_JITTER_S,
        "min_valid_contexts": WHISPER_STABILITY_MIN_CTX,
        "criterion": ("stable iff n_valid>=%d and start/end jitter "
                      "<= %.3fs (the cross-family agreement bound)"
                      % (WHISPER_STABILITY_MIN_CTX,
                         WHISPER_STABLE_JITTER_S)),
        "vocals_wav_sha256": _sha256(vocals_wav)
        if vocals_wav and Path(vocals_wav).exists() else None,
        "lyric_sequence_sha256": hashlib.sha256(
            _json.dumps(text, ensure_ascii=False,
                        sort_keys=True).encode()).hexdigest()}
