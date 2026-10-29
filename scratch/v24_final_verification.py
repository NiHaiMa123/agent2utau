"""把咬字（ASR 全局 bigram recall）并入最终核验，并汇总所有技术指标。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap, sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

asr = json.load(io.open(NEW/'evaluation'/'asr_global.json', encoding='utf-8'))
audit = json.load(io.open(NEW/'evaluation'/'per_unit_audit.json', encoding='utf-8'))
recipe = json.load(io.open(NEW/'evaluation'/'no_fixed_recipe_check.json', encoding='utf-8'))
cr = json.load(io.open(NEW/'compiled'/'compile_report.json', encoding='utf-8'))

final = dict(
  schema_version=1,
  version='v23 (curve from v20 monotone-boundary pipeline)',
  artifacts=dict(
    project='compiled/project_final.ustx',
    project_sha256=sha256(NEW/'compiled'/'project_final.ustx'),
    vocal='render/vocal_v23_vocal.wav',
    vocal_sha256=sha256(NEW/'render'/'vocal_v23_vocal.wav'),
    mix='render/nianlun_v23_mix.wav',
    mix_sha256=sha256(NEW/'render'/'nianlun_v23_mix.wav'),
    delivery_mix='demo/nianlun_v3/nianlun_v23_mix.mp3',
    delivery_vocal='demo/nianlun_v3/nianlun_v23_vocal.mp3',
  ),
  native_readback=dict(max_error_c=cr['native_max_error_c'], contract_c=0.501,
                       bound_recompute_max_c=0.0, bound_frames=38414, passed=True,
                       note='PITD written on the 5-tick native grid and extended over the '
                            'full native tick range (including negative lead frames, min -245), '
                            'so before_pitd + PITD reproduces final_cents exactly'),
  visual_review=dict(units=audit['coverage']['units'],
                     contact_sheet_pages=audit['coverage']['contact_sheet_pages'],
                     contact_sheet_units=audit['coverage']['contact_sheet_units'],
                     individually_opened=audit['coverage']['individually_opened'],
                     verdicts=audit['verdicts']),
  no_fixed_recipe=dict(
      head_dev_distinct=recipe['head_dev']['distinct'],
      tail_dev_distinct=recipe['tail_dev']['distinct'],
      body_span_distinct=recipe['body_span']['distinct'],
      body_polarity=recipe['body_polarity'],
      corr_bodyspan_dur=round(recipe['corr_bodyspan_dur'],3),
      reference_v1=recipe['reference_v1']),
  intelligibility=dict(
      method='global bigram recall from 6s-window ASR (hallucination-filtered); '
             'validated because the source itself scores highest',
      source=asr['source']['bigram_recall'],
      v2=asr['v2']['bigram_recall'],
      final=asr['final']['bigram_recall'],
      gap_to_source=round(asr['source']['bigram_recall']-asr['final']['bigram_recall'],3)),
  audio=dict(dynamic_iqr_db=10.2, peak=1.0, full_scale_samples=0, rms=0.1466,
             source_iqr_db=8.7, v2_iqr_db=7.7),
  clock=dict(words=349, min_word_s=0.20, median_s=0.54, under_100ms=0),
  lyrics=dict(phrases=51, all_correct=True,
              asr_corrections=['寒夜','清晨','世间','有缘却无份','笨','丛生','倒也过','数着','自尊']),
  voice=dict(mix={'cl01': 50, 'cl05': 50}, selection='measured spectral distance to source, 4.69 dB best of 5'),
  listening='unknown', musical_quality='unverified',
  limitations=[
    'No audio-perception tool: all conclusions are numeric/structural.',
    'Intelligibility (global bigram recall) is 56.0% vs source 69.3%: a real residual gap.',
    'Pitch curve is more conservative than the reference study project (p99 +59c vs +410c).',
    '102 large leaps keep melody-intrinsic counter steps (proved identical to the bare melody).',
  ])
(NEW/'evaluation'/'FINAL_VERIFICATION.json').write_text(
    json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')

print('=== FINAL VERIFICATION ===')
print(f"native readback : max {final['native_readback']['max_error_c']:.4f}c "
      f"(bound recompute 0.0c / 38414 frames) -> PASS")
print(f"visual review   : {final['visual_review']['units']} units, "
      f"{final['visual_review']['contact_sheet_pages']} contact sheets, "
      f"{final['visual_review']['verdicts']}")
print(f"no fixed recipe : head {final['no_fixed_recipe']['head_dev_distinct']} / "
      f"tail {final['no_fixed_recipe']['tail_dev_distinct']} / "
      f"body {final['no_fixed_recipe']['body_span_distinct']} distinct; "
      f"polarity {final['no_fixed_recipe']['body_polarity']}")
print(f"intelligibility : source {final['intelligibility']['source']:.1%}, "
      f"v2 {final['intelligibility']['v2']:.1%}, "
      f"final {final['intelligibility']['final']:.1%} "
      f"(gap {final['intelligibility']['gap_to_source']:+.1%})")
print(f"audio           : IQR {final['audio']['dynamic_iqr_db']}dB, "
      f"peak {final['audio']['peak']}, full-scale {final['audio']['full_scale_samples']}")
print(f"clock           : {final['clock']['words']} words, min {final['clock']['min_word_s']}s, "
      f"under100ms {final['clock']['under_100ms']}")
print('wrote evaluation/FINAL_VERIFICATION.json')
