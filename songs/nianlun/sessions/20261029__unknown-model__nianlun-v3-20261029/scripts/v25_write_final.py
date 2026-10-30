"""把咬字专项的完整结论写入最终核验（含未解释的 +1.4pp 与起音无改善）。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
p = NEW/'evaluation'/'FINAL_VERIFICATION.json'
v = json.load(io.open(p, encoding='utf-8'))

v['intelligibility']['measurement'] = {
    'method': '6s-window chunked ASR, hallucination-filtered, global bigram recall',
    'validity_check': 'source scores highest (69.3%) as required for a ground-truth upper bound',
    'determinism': 'identical across 3 repeats (std 0.000%)',
}
v['intelligibility']['ablation'] = {
    'current': 0.560,
    'without_brec_voic': 0.556,
    'without_pitd': 0.571,
    'conclusion': 'removing the phonation layer or the whole pitch curve moves recall by <=1.1pp, '
                  'so the 13.3pp gap to the source is NOT attributable to the designed layers',
}
v['intelligibility']['vowel_offset_experiment'] = {
    'mechanism_tested': 'consonant share (ours 26.1% vs source 29.7%), via phoneme_overrides offset',
    'dose_+20ms': dict(recall=0.574, consonant_share=0.265, consonant_med_ms=150, vowel_med_ms=404),
    'dose_+35ms': dict(recall=0.571, consonant_share=0.269, consonant_med_ms=152, vowel_med_ms=403),
    'baseline':   dict(recall=0.560, consonant_share=0.261, consonant_med_ms=148, vowel_med_ms=407),
    'onset_rise_db': dict(baseline=2.0, plus20=2.0, plus35=2.2, source=3.5),
    'verdict': 'recall rose 1.4pp reproducibly, but the assumed mechanism did NOT occur '
               '(vowels shortened only 3-4ms, consonants lengthened 2-4ms, onset rise unchanged). '
               'The gain is therefore unexplained and is NOT adopted; the delivered version keeps '
               'the baseline configuration.',
}
v['limitations'] = [
    'No audio-perception tool: every conclusion is numeric/structural; listening is unverified.',
    'Intelligibility 56.0% vs source 69.3%. Ablations show this is not caused by the designed '
    'pitch or phonation layers (<=1.1pp). A vowel-offset experiment gave +1.4pp reproducibly but '
    'without the hypothesised mechanism, so it was not adopted.',
    'Pitch curve is more conservative than the reference study project (p99 +59c vs +410c); '
    'this is a deliberate trade-off that removed cliffs and reverse precursors.',
    '102 large leaps retain melody-intrinsic counter steps, proved identical to the bare melody.',
    'Contact sheets cover all 349 units but at reduced size; per-cycle fine shape needs zoom.',
]
json.dump(v, io.open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)

print('=== 咬字专项最终结论 ===')
print(f"  recall: source {v['intelligibility']['source']:.1%} / "
      f"v2 {v['intelligibility']['v2']:.1%} / delivered {v['intelligibility']['final']:.1%}")
print(f"  消融: no-BREC/VOIC {v['intelligibility']['ablation']['without_brec_voic']:.1%}, "
      f"no-PITD {v['intelligibility']['ablation']['without_pitd']:.1%}")
print(f"  元音 offset 实验: +20ms {v['intelligibility']['vowel_offset_experiment']['dose_+20ms']['recall']:.1%} "
      f"但起音未改善 -> 不采纳")
print('wrote FINAL_VERIFICATION.json')
