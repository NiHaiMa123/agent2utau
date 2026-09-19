"""§G5N.2 identity-aware lyric / phoneme alignment — second family.

family A = current Whisper-derived char alignment (force_align DTW).
family B = this module: a lyric-constrained identity-aware forced
alignment — MMS_FA CTC aligner over romanized (toneless pinyin)
syllables of the KNOWN lyric sequence against the separated source
vocal. It answers "which known lyric token is actually sung here,
and where", which waveform onset/energy or phoneme-class consistency
can never answer.

Output contract (persisted, auditable):
  aligner_family / aligner_version / model+lexicon provenance /
  source_wav_sha256 / lyric_sequence_sha256
  per token: token_index, char, pinyin, start/end (wav-relative s),
  confidence (mean CTC span log-prob), boundary uncertainty,
  status aligned|skipped|inserted

Waveform-class evidence (`_onset_span_evidence`) stays a supporting
acoustic diagnostic — it is NEVER identity authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ALIGNER_FAMILY = "mms_fa_ctc_uroman"
ALIGNER_VERSION = "ifa1"
# material aligner/model/lexicon/config change → bump ALIGNER_VERSION
# (dependent inventory/package evidence becomes stale, §G5N.2-N30)

# CTC emission frame period for MMS_FA at 16 kHz (encoder stride 320).
ALIGNER_FRAME_S = 0.02
# Timing-disagreement safety bound for identity adjudication — a cap,
# never a pass target (§G5N.2 tolerance semantics).
IDENTITY_TIMING_CAP_S = 0.30
# Minimum mean CTC span log-prob for a token to count as confidently
# aligned; below → low-confidence → identity_unverified (fail-closed).
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


def identity_align(wav, chars):
    """Run family-B forced alignment.

    wav: Path (or None) to the separated source vocal clip.
    chars: KNOWN lyric sequence for the clip — list of dicts with at
           least "char" (text only; their timing is NOT used — that is
           family-A's claim, not a constraint).

    Returns the contract dict. On any missing input / model failure /
    unalignable text → {"available": False, "reason": ...} — callers
    must treat that as identity_unverified, never as evidence."""
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


def identity_adjudicate(align_doc, chars):
    """Adjudicate each char's IDENTITY against family-B output.

    chars: the SAME known-lyric sequence list used for alignment —
           entries carry family-A (Whisper) char/start/end/probability
           in wav-relative seconds.

    Per char verdict:
      identity_verified   — family-B aligns the same token index,
                            monotonic order, boundary disagreement
                            within evidence-derived tolerance
      identity_conflict   — family-B places the token at a
                            non-monotonic / mismatched position
      measurement_ambiguous — identity agrees but A/B timing
                            disagreement exceeds tolerance
      identity_unverified — family-B unavailable / low confidence
                            / missing token

    Tolerance is evidence-derived (§G5N.2): base = 3× frame period
    plus the phrase's own confident-token disagreement dispersion
    (median abs deviation), hard-capped by IDENTITY_TIMING_CAP_S."""
    n = len(chars)
    verdicts = [{"verdict": "identity_unverified", "dev_start_s": None,
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
    tol = min(IDENTITY_TIMING_CAP_S,
              3 * ALIGNER_FRAME_S + disp)

    prev_end = -1e9
    for i, (c, t) in enumerate(zip(chars, toks)):
        v = verdicts[i]
        v["famB_start"] = t.get("start")
        v["famB_end"] = t.get("end")
        v["famB_confidence"] = t.get("confidence")
        v["tolerance_s"] = round(tol, 4)
        if t.get("status") != "aligned":
            v["verdict"] = "identity_unverified"
            continue
        if t["start"] < prev_end - 1e-4:
            v["verdict"] = "identity_conflict"
            continue
        prev_end = t["end"]
        if c.get("start") is None:
            v["verdict"] = "identity_unverified"
            continue
        dev = abs(float(t["start"]) - float(c["start"]))
        v["dev_start_s"] = round(dev, 4)
        v["verdict"] = ("identity_verified" if dev <= tol
                        else "measurement_ambiguous")
    return {"available": True, "verdicts": verdicts, "reason": None,
            "tolerance_s": round(tol, 4)}
