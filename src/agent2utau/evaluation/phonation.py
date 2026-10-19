"""Read-only, condition-matched output proxies; never a perceptual pass/fail.

The period-lag estimator below is transparent and deliberately not called
Praat HNR/CPP. Model VOIC/BREC and production expectations are not score inputs.
"""
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import csv
import json
import math

import numpy as np
import soundfile as sf

from ..openutau.ustx import sha256
from .features import phone_kind


@dataclass(frozen=True)
class PhonationConfig:
    hop_s: float = .01
    periods: int = 8
    min_window_s: float = .020
    max_window_s: float = .080
    f0_agreement_c: float = 50.
    local_f0_span_c: float = 20.
    lag_search_fraction: float = .03
    min_rms_dbfs: float = -70.
    min_highband_relative_db: float = -80.
    min_body_frames: int = 5
    pitch_match_semitones: float = 3.
    robust_scale_floor_db: float = 3.
    min_phrase_matched_fraction: float = .75

    def __post_init__(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Nonfinite configuration')
        if (self.hop_s <= 0 or self.periods < 5 or self.min_window_s <= 0
                or self.max_window_s < self.min_window_s or self.f0_agreement_c <= 0
                or self.local_f0_span_c <= 0 or not 0 < self.lag_search_fraction < .1
                or self.min_rms_dbfs >= 0 or self.min_highband_relative_db >= 0 or self.min_body_frames < 2
                or not isinstance(self.min_body_frames, int) or not isinstance(self.periods, int)
                or self.pitch_match_semitones <= 0 or self.robust_scale_floor_db <= 0
                or not 0 < self.min_phrase_matched_fraction <= 1):
            raise ValueError('Invalid configuration')


ALGORITHM_VERSION = '2-separated-acoustic-axes'
SCORE_FEATURES = ('periodicity_ratio_db_proxy', 'highband_flatness_db')
FEATURES = (*SCORE_FEATURES, 'output_spectral_tilt_db_oct', 'rms_dbfs')


def frame_features(samples, sr, f0, cfg=PhonationConfig()):
    """Gain-invariant periodicity/shape, with RMS as a separate diagnostic.

    Correlation searches 13 fractional lags around the supplied measured F0.
    Its transformed ratio is only a proxy under a stationary periodic+noise
    assumption, not a unique physical noise decomposition.
    """
    x = np.asarray(samples, float)
    if (x.ndim != 1 or len(x) < 16 or not np.isfinite(x).all()
            or not np.isfinite(f0) or f0 <= 0 or sr < 16000):
        return dict(status='unknown', reason='invalid_frame')
    x = x - x.mean()
    rms = float(np.sqrt(np.mean(x*x)))
    if rms <= 0 or 20*np.log10(rms) < cfg.min_rms_dbfs:
        return dict(status='unknown', reason='silence_or_low_level')
    if np.max(np.abs(samples)) >= .999:
        return dict(status='unknown', reason='clipping_risk')
    y = x/rms
    lags = sr/f0 * np.linspace(1-cfg.lag_search_fraction, 1+cfg.lag_search_fraction, 13)
    correlations = []
    for lag in lags:
        n = int(np.floor(len(y)-lag))
        if n < 8:
            continue
        left = y[:n]
        right = np.interp(np.arange(n)+lag, np.arange(len(y)), y)
        den = np.linalg.norm(left)*np.linalg.norm(right)
        if den > 0:
            correlations.append(float(left@right/den))
    if not correlations:
        return dict(status='unknown', reason='insufficient_period_support')
    rho = float(np.clip(max(correlations), 0., 1.))
    ratio = float(10*np.log10(max(rho, 1e-6)/max(1-rho, 1e-6)))
    nfft = 2**math.ceil(math.log2(len(y)*4))
    power = abs(np.fft.rfft(y*np.hanning(len(y)), nfft))**2
    freq = np.fft.rfftfreq(nfft, 1/sr)
    floor = max(float(power.max())*1e-12, np.finfo(float).tiny)
    high_power = power[(freq >= 2000) & (freq <= min(8000, sr/2))]
    highband_relative_db = float(10*np.log10(max(float(high_power.sum()), floor)/power.sum()))
    if highband_relative_db < cfg.min_highband_relative_db:
        return dict(status='unknown', reason='unresolved_highband_energy')
    high = np.maximum(high_power, floor)
    flatness = float(10/np.log(10)*(np.mean(np.log(high))-np.log(np.mean(high))))
    band = (freq >= 120) & (freq <= 5000)
    slope = float(np.polyfit(np.log2(freq[band]), 10*np.log10(np.maximum(power[band], floor)), 1)[0])
    return dict(status='measured', period_lag_ncc=rho, periodicity_ratio_db_proxy=ratio,
                highband_flatness_db=flatness, output_spectral_tilt_db_oct=slope,
                rms_dbfs=float(20*np.log10(rms)), highband_relative_power_db=highband_relative_db,
                ratio_censored=bool(rho <= 1e-6 or rho >= 1-1e-6))


def _load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _bound(binding, base):
    if set(binding) != {'path', 'sha256'}:
        raise ValueError('A file requires explicit path/SHA256')
    path = Path(binding['path'])
    path = path.resolve() if path.is_absolute() else (base/path).resolve()
    if sha256(path) != binding['sha256']:
        raise ValueError('Changed input: '+str(path))
    return path


def _f0(binding, base, audio_hash):
    if set(binding) != {'file', 'audio_sha256', 'absolute_offset_s', 'detector'}:
        raise ValueError('Explicit F0 audio/clock/detector binding required')
    if binding['audio_sha256'] != audio_hash or not np.isfinite(binding['absolute_offset_s']):
        raise ValueError('F0 belongs to another audio or invalid clock')
    path = _bound(binding['file'], base)
    with np.load(path, allow_pickle=False) as raw:
        if not {'times', 'f0_hz', 'voiced'} <= set(raw.files):
            raise ValueError('Missing F0 arrays')
        t = np.array(raw['times'], float)+binding['absolute_offset_s']
        f = np.array(raw['f0_hz'], float)
        v = np.array(raw['voiced'], bool)
    if (t.ndim != 1 or f.shape != t.shape or v.shape != t.shape or len(t) < 2
            or not np.isfinite(t).all() or not np.isfinite(f).all()
            or np.any(np.diff(t) <= 0) or np.any(f < 0)
            or np.any(v & (f <= 0))):
        raise ValueError('Invalid F0 arrays')
    return t, f, v


def _sample_f0(track, at):
    t, f, v = track
    right = int(np.searchsorted(t, at))
    if right == 0 or right >= len(t) or t[right]-t[right-1] > .025:
        return None
    if not v[right-1] or not v[right]:
        return None
    return float(np.interp(at, t[right-1:right+1], f[right-1:right+1]))


def _summarize(frames):
    if not frames:
        return None
    return {k: float(np.median([r[k] for r in frames])) for k in FEATURES}


def measure_regions(audio, sr, offset_s, regions, tracks, cfg=PhonationConfig()):
    if len(tracks) != 2:
        raise ValueError('Two independent measured F0 tracks required')
    if not np.isfinite(offset_s):
        raise ValueError('Invalid audio clock')
    results = []
    ids = set()
    prior_end = -np.inf
    for region in regions:
        if set(region) != {'id', 'phrase_id', 'phone', 'support_s'}:
            raise ValueError('Unsupported region fields; no production expectations')
        a, b = region['support_s']
        if (region['id'] in ids or not np.isfinite([a,b]).all() or not a < b
                or a < offset_s-1e-7 or b > offset_s+len(audio)/sr+1e-7
                or a < prior_end-1e-7):
            raise ValueError('Invalid/overlapping region identity or audio clock')
        ids.add(region['id']);prior_end = b
        if phone_kind(region['phone']) != 'vowel':
            results.append(dict(**region, status='excluded', reason='not_vowel', frames=[], body=None))
            continue
        measured = [];excluded = Counter()
        for center in np.arange(math.ceil(a/cfg.hop_s)*cfg.hop_s, b, cfg.hop_s):
            f0 = [_sample_f0(t, center) for t in tracks]
            if any(f is None or f <= 0 for f in f0):
                excluded['unvoiced_or_missing_F0'] += 1;continue
            if abs(1200*np.log2(f0[0]/f0[1])) > cfg.f0_agreement_c:
                excluded['F0_disagreement'] += 1;continue
            pitch = float(np.sqrt(f0[0]*f0[1]))
            duration = max(cfg.min_window_s, cfg.periods/pitch)
            if duration > cfg.max_window_s:
                excluded['insufficient_cycles_within_max_window'] += 1;continue
            lo, hi = center-duration/2, center+duration/2
            if lo < a or hi > b:
                excluded['crosses_vowel_boundary'] += 1;continue
            span_ok = True
            checkpoints = np.unique(np.concatenate(([lo, hi], *[t[(t >= lo) & (t <= hi)] for t,_,_ in tracks])))
            for at in checkpoints:
                pair = [_sample_f0(t, at) for t in tracks]
                if any(f is None for f in pair) or abs(1200*np.log2(pair[0]/pair[1])) > cfg.f0_agreement_c:
                    span_ok = False;break
            for t, f, v in tracks:
                mask = (t >= lo) & (t <= hi)
                if mask.sum() < 2 or not v[mask].all() or np.any(f[mask] <= 0):
                    span_ok = False;break
                if 1200*np.log2(f[mask].max()/f[mask].min()) > cfg.local_f0_span_c:
                    span_ok = False;break
            if not span_ok:
                excluded['nonstationary_or_unvoiced_window'] += 1;continue
            begin, end = round((lo-offset_s)*sr), round((hi-offset_s)*sr)
            features = frame_features(audio[begin:end], sr, pitch, cfg)
            if features['status'] != 'measured':
                excluded[features['reason']] += 1;continue
            phase = (center-a)/(b-a)
            measured.append(dict(time_s=float(center), phase=float(phase), stage='entry' if phase < .25 else 'exit' if phase > .75 else 'body', midi=float(69+12*np.log2(pitch/440)), **features))
        body = [f for f in measured if f['stage'] == 'body']
        results.append(dict(**region, status='measured' if len(body) >= cfg.min_body_frames else 'unknown',
                            reason=None if len(body) >= cfg.min_body_frames else 'insufficient_reliable_body_frames',
                            frames=measured, excluded_frames=dict(excluded), body=_summarize(body) if len(body) >= cfg.min_body_frames else None,
                            median_midi=float(np.median([r['midi'] for r in body])) if body else None,
                            stages={s:_summarize([r for r in measured if r['stage']==s]) for s in ['entry','body','exit']}))
    return results


def conditioned_scores(words, anchors, cfg=PhonationConfig()):
    """One vote per vowel; no cross-vowel filling or production-plan truth."""
    scores = []
    for word in words:
        matches = [r for r in anchors if r['id'] != word['id'] and r.get('body') and word.get('body')
                   and r['phone'] == word['phone']
                   and abs(r['median_midi']-word['median_midi']) <= cfg.pitch_match_semitones]
        if not matches:
            scores.append(dict(unit_id=word['id'], status='unknown', reason='no_comparable_reference' if word.get('body') else word.get('reason','insufficient_body'), reference_ids=[]))
            continue
        baseline = {};z = []
        for feature in SCORE_FEATURES:
            values = np.array([r['body'][feature] for r in matches]);median = float(np.median(values))
            scale = max(float(1.4826*np.median(abs(values-median))), cfg.robust_scale_floor_db)
            baseline[feature] = dict(median=median, scale=scale)
            z.append((word['body'][feature]-median)/scale)
        axes = {feature:dict(change=word['body'][feature]-baseline[feature]['median'],
                             standardized_change=z[i]) for i,feature in enumerate(SCORE_FEATURES)}
        scores.append(dict(unit_id=word['id'], status='provisional', reference_ids=[r['id'] for r in matches],
                           reference_word_count=len(matches), baseline=baseline, standardized_components=z,
                           axis_contrasts=axes,
                           relative_firmness_proxy=None,
                           consistency_distance_proxy=float(np.linalg.norm(z)),
                           evidence_scope='singleton_reference' if len(matches)==1 else 'multiple_conditioned_references',
                           firmness_assessment=None, calibration_status='unvalidated',
                           interpretation='Separate acoustic axes; filter and pitch motion can mimic changes. Distance is descriptive, no composite virtual/firmness scale.'))
    return scores


def phrase_summaries(words, scores, phrase_order, cfg=PhonationConfig()):
    mapping = {s['unit_id']:s for s in scores};out = []
    for ident in phrase_order:
        rows = [r for r in words if r['phrase_id']==ident and phone_kind(r['phone'])=='vowel']
        found = [mapping[r['id']] for r in rows if mapping[r['id']]['status']=='provisional']
        coverage = len(found)/len(rows) if rows else 0.
        out.append(dict(phrase_id=ident, vowels=len(rows), reliable_body_vowels=sum(bool(r.get('body')) for r in rows),
                        comparable_vowels=len(found), comparable_fraction=coverage,
                        status='partial_descriptive_only' if coverage >= cfg.min_phrase_matched_fraction else 'insufficient_matched_coverage',
                        matched_only_median_distance=float(np.median([r['consistency_distance_proxy'] for r in found])) if found else None,
                        matched_only_median_signed_proxy=None,
                        perceptual_consistency='unvalidated', boundary='Matched subset only, equal vowel weights; not a whole-phrase virtual/firmness score'))
    return out


def evaluate_phonation(manifest_path, out):
    manifest_path = Path(manifest_path).resolve();manifest = _load_json(manifest_path);base = manifest_path.parent
    required = {'schema_version','signal_role','project','regions','versions','reference_version','reference_phrases','phrase_order','config','knowledge_context'}
    if set(manifest) != required or manifest['schema_version'] != 1:
        raise ValueError('Unsupported explicit phonation manifest')
    if manifest['signal_role'] != 'pure_solo_vocal':
        raise ValueError('Mixed/polyphonic audio unsupported')
    project = _bound(manifest['project'], base)
    regions = _load_json(_bound(manifest['regions'], base))
    from ..knowledge import check_plan_knowledge
    _, knowledge_receipt = check_plan_knowledge(manifest, manifest_path)
    if (not manifest['versions'] or not manifest['phrase_order']
            or len(set(manifest['phrase_order'])) != len(manifest['phrase_order'])
            or not manifest['reference_phrases']
            or not {r['phrase_id'] for r in regions} <= set(manifest['phrase_order'])):
        raise ValueError('Missing/invalid versions, phrase order or region coverage')
    cfg = PhonationConfig(**manifest['config']);versions = {};input_bindings = []
    for version in manifest['versions']:
        if set(version) != {'id','audio','absolute_offset_s','f0'} or version['id'] in versions:
            raise ValueError('Invalid/duplicate version')
        path = _bound(version['audio'], base);audio, sr = sf.read(path, always_2d=True)
        if audio.shape[1] != 1 or not np.isfinite(audio).all():
            raise ValueError('Finite mono solo vocal required')
        if len(version['f0']) != 2 or len({t['detector'] for t in version['f0']}) != 2:
            raise ValueError('Two distinct explicitly named detectors required')
        if any(t['absolute_offset_s'] != version['absolute_offset_s'] for t in version['f0']):
            raise ValueError('F0 and its bound audio have different clock origins')
        tracks = [_f0(t,base,version['audio']['sha256']) for t in version['f0']]
        for t,_,_ in tracks:
            if (t[0] < version['absolute_offset_s']-.025 or t[0] > version['absolute_offset_s']+.025
                    or t[-1] < version['absolute_offset_s']+len(audio)/sr-.025):
                raise ValueError('F0 does not cover its bound audio clock')
        words = measure_regions(audio[:,0], sr, version['absolute_offset_s'], regions, tracks, cfg)
        versions[version['id']] = dict(words=words)
        input_bindings.append(version)
    if manifest['reference_version'] not in versions or not set(manifest['reference_phrases']) <= set(manifest['phrase_order']):
        raise ValueError('Invalid reference selection')
    anchors = [r for r in versions[manifest['reference_version']]['words'] if r['phrase_id'] in manifest['reference_phrases']]
    for v in versions.values():
        v['scores'] = conditioned_scores(v['words'], anchors, cfg)
        v['phrases'] = phrase_summaries(v['words'], v['scores'], manifest['phrase_order'], cfg)
    pairs = []
    first_id = next(iter(versions))
    for ident, data in versions.items():
        if ident == first_id:continue
        for a,b in zip(versions[first_id]['words'],data['words']):
            pairs.append(dict(unit_id=a['id'],phrase_id=a['phrase_id'],versions=[first_id,ident],
                              status='measured' if a.get('body') and b.get('body') else 'unknown',
                              feature_changes={k:b['body'][k]-a['body'][k] for k in FEATURES} if a.get('body') and b.get('body') else None,
                              pitch_change_semitones=b['median_midi']-a['median_midi'] if a.get('body') and b.get('body') else None,
                              scope='Same-region acoustic response, not proof of improved cross-phrase identity'))
    result = dict(schema_version=2, algorithm_version=ALGORITHM_VERSION, config=asdict(cfg), project_sha256=sha256(project),
                  bindings=dict(manifest=dict(path=str(manifest_path),sha256=sha256(manifest_path)),regions=manifest['regions'],versions=input_bindings),
                  knowledge_receipt=knowledge_receipt, reference=dict(version=manifest['reference_version'],phrase_ids=manifest['reference_phrases'],selection='Caller-declared scoped human continuity anchors, not a fitted perceptual scale'),
                  versions=versions,paired_changes=pairs,perceptual_scale_validated=False,hearing_pass=None,
                  limitations=['Period-lag/flatness proxies are not physiological closure, actual breath percentage or exact Praat HNR/CPP',
                               'Exact phone and broad register matching does not remove all formant/style/dynamics confounds',
                               'Missing comparisons stay unknown; same-word response does not certify continuity',
                               'Pure-solo role and reference acceptance scope are caller attestations; no blind hearing validation',
                               'No combined virtual/firmness score: periodicity and spectral surface are separate uncalibrated axes',
                               'No automatic score-to-VOIC/BREC conversion, repair, cache search or source synthesis'])
    out = Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (out/'words.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['version','unit','phrase','phone','status','body_frames',*FEATURES,'match_count','relative_firmness_proxy','consistency_distance_proxy'])
        for ident,data in versions.items():
            scores={s['unit_id']:s for s in data['scores']}
            for w in data['words']:
                s=scores[w['id']];writer.writerow([ident,w['id'],w['phrase_id'],w['phone'],w['status'],sum(r['stage']=='body' for r in w['frames']),*[(w.get('body') or {}).get(k) for k in FEATURES],len(s['reference_ids']),s.get('relative_firmness_proxy'),s.get('consistency_distance_proxy')])
    lines=['# Phonation consistency observations','','Perceptual scale: unvalidated. Unknown regions are not passes.','','| Version | Phrase | Reliable vowels | Comparable | Coverage | Matched-only distance | Status |','|---|---|---:|---:|---:|---:|---|']
    for ident,data in versions.items():
        for r in data['phrases']:lines.append(f"| {ident} | {r['phrase_id']} | {r['reliable_body_vowels']}/{r['vowels']} | {r['comparable_vowels']} | {r['comparable_fraction']:.1%} | {r['matched_only_median_distance']} | {r['status']} |")
    lines+=['','These are conditioned acoustic proxies and coverage, not a virtual/firmness pass threshold.','See result.json for per-stage frames, excluded windows, reference IDs/scales and paired changes.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args(argv)
    result=evaluate_phonation(args.manifest,args.out);print(json.dumps(dict(status='observed',perceptual_scale_validated=False,versions=list(result['versions']))));return 0


if __name__ == '__main__':raise SystemExit(main())
