import copy
import pytest
from agent2utau.evaluation.phonation_audit import compare_pair
from agent2utau.evaluation.phonation import FEATURES


def word(ident='a', times=range(7), delta=0):
    return dict(id=ident, phrase_id='p', phone='zh/a', support_s=[0, 1], body={k: 0 for k in FEATURES},
                frames=[dict(time_s=t*.01, stage='body', status='measured', midi=60,
                             **{k: float(delta) for k in FEATURES}) for t in times])


def test_shared_centers_remove_different_masks():
    a, b = word(times=range(9)), word(times=range(2, 9), delta=2)
    a['frames'][0].update({k: 1000 for k in FEATURES})
    out = compare_pair([a], [b])
    assert out['words'][0]['shared_count'] == 7
    assert all(v == 2 for v in out['median_right_minus_left'].values())
    assert out['perceptual_firmness'] is None


def test_high_individual_coverage_does_not_hide_no_shared_support():
    out = compare_pair([word(times=range(7))], [word(times=range(5, 12))])
    assert out['comparable_vowels'] == 0
    assert out['median_right_minus_left'] is None


def test_vowels_equal_vote_and_swapped_pair_sign():
    a = [word('a', range(50)), word('b', range(6))]
    b = [word('a', range(50), 2), word('b', range(6), 8)]
    assert compare_pair(a, b)['median_right_minus_left']['rms_dbfs'] == 5
    assert compare_pair(b, a)['median_right_minus_left']['rms_dbfs'] == -5


@pytest.mark.parametrize('field,value', [('phone', 'zh/i'), ('support_s', [0, 2]), ('phrase_id', 'q')])
def test_identity_changes_rejected(field, value):
    a = word(); b = copy.deepcopy(a); b[field] = value
    with pytest.raises(ValueError, match='Different'):
        compare_pair([a], [b])


def test_octave_shift_and_missing_body_stay_unknown():
    a = word(); b = word()
    for f in b['frames']: f['midi'] += 12
    assert compare_pair([a], [b])['comparable_vowels'] == 0
    b = word(); b['body'] = None
    assert compare_pair([a], [b])['comparable_vowels'] == 0


def test_duplicate_ids_and_centers_rejected():
    with pytest.raises(ValueError, match='Duplicate region'):
        compare_pair([word(), word()], [word()])
    a = word(); a['frames'].append(copy.deepcopy(a['frames'][0]))
    with pytest.raises(ValueError, match='Duplicate body'):
        compare_pair([a], [word()])
