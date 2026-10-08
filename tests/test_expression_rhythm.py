import numpy as np
import pytest
from agent2utau.expression.rhythm import fixed_recording_shift,syllable_timing_conflicts


def test_joint_audit_detects_stolen_vowel_even_with_ordered_positive_durations():
    result=syllable_timing_conflicts([1.,1.4],[1.,1.13],duration_ratio_bounds=(.65,1.6),next_reference_s=1.4,next_target_s=1.13,boundary_limit_s=.12)
    assert result['review_reasons']==['vowel_compressed','following_word_boundary_displaced']
    following=syllable_timing_conflicts([1.4,3.],[1.13,3.],duration_ratio_bounds=(.65,1.6))
    assert following['duration_ratio']>1


def test_no_rule_forces_legitimate_short_word_to_become_long():
    result=syllable_timing_conflicts([1.,1.1],[2.,2.1],duration_ratio_bounds=(.65,1.6))
    assert result['review_reasons']==[]


def test_global_clock_uses_independent_distributed_anchors():
    reference=np.linspace(28.,240.,100);recording=reference-1.88+.02*np.sin(reference)
    result=fixed_recording_shift(reference,recording,residual_limit_s=.08)
    assert abs(result['shift_s']+1.88)<.005
    assert len(result['regions'])==4 and all(r['anchors']>=4 for r in result['regions'])


def test_fixed_clock_rejects_tempo_drift_and_missing_song_coverage():
    reference=np.linspace(28.,240.,100)
    with pytest.raises(ValueError,match='single recording shift'):
        fixed_recording_shift(reference,reference*1.005-1.88,residual_limit_s=.08)
    reference=np.r_[np.linspace(28.,30.,99),240.]
    with pytest.raises(ValueError,match='distributed musical support'):
        fixed_recording_shift(reference,reference-1.88,residual_limit_s=.08)
