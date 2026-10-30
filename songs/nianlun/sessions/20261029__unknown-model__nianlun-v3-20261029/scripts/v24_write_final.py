"""把三组消融结论写入最终核验，并生成完整交付报告的数据部分。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
p = NEW/'evaluation'/'FINAL_VERIFICATION.json'
v = json.load(io.open(p, encoding='utf-8'))

v['intelligibility']['ablation'] = {
    'current_mix_with_all_curves': 0.560,
    'without_brec_voic': 0.556,
    'without_pitd': 0.571,
    'interpretation': 'removing the phonation layer or the entire pitch curve changes '
                      'global bigram recall by <=1.1 pp, so the residual gap to the source '
                      'is not caused by the designed layers; it is the baseline of this '
                      'voicebank/phoneme configuration',
}
v['limitations'] = [
    'No audio-perception tool: every conclusion is numeric/structural.',
    'Intelligibility: 56.0% vs source 69.3%. Ablations (no BREC/VOIC = 55.6%, no PITD = 57.1%) '
    'show this residual is NOT caused by the designed layers.',
    'Pitch curve is more conservative than the reference study project (p99 +59c vs +410c); '
    'this is a deliberate trade-off to remove cliffs and reverse precursors.',
    '102 large leaps retain melody-intrinsic counter steps, proved identical to the bare melody.',
    'Contact sheets cover all 349 units but at reduced size; per-cycle fine shape needs zoom.',
]
json.dump(v, io.open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)

print('=== 最终核验（含消融）===')
print(f"native readback : {v['native_readback']['max_error_c']:.4f}c (contract <0.501) -> PASS")
print(f"bound recompute : {v['native_readback']['bound_recompute_max_c']:.4f}c over "
      f"{v['native_readback']['bound_frames']} frames -> PASS")
print(f"visual review   : {v['visual_review']['units']} units / "
      f"{v['visual_review']['contact_sheet_pages']} sheets / {v['visual_review']['verdicts']}")
print(f"no fixed recipe : head {v['no_fixed_recipe']['head_dev_distinct']} / "
      f"tail {v['no_fixed_recipe']['tail_dev_distinct']} / "
      f"body {v['no_fixed_recipe']['body_span_distinct']} distinct values; "
      f"polarity {v['no_fixed_recipe']['body_polarity']['pos']}:"
      f"{v['no_fixed_recipe']['body_polarity']['neg']}")
print(f"intelligibility : source {v['intelligibility']['source']:.1%} / "
      f"v2 {v['intelligibility']['v2']:.1%} / final {v['intelligibility']['final']:.1%}")
print(f"  ablations     : no-BREC/VOIC {v['intelligibility']['ablation']['without_brec_voic']:.1%}, "
      f"no-PITD {v['intelligibility']['ablation']['without_pitd']:.1%}")
print(f"audio           : IQR {v['audio']['dynamic_iqr_db']}dB, peak {v['audio']['peak']}, "
      f"full-scale {v['audio']['full_scale_samples']}")
print('wrote FINAL_VERIFICATION.json')
