import numpy as np
import pytest
from agent2utau.expression.variance_expectation import variance_expectation,gaussian_frame_noise


def sample(seed,delta):
    return dict(seed=seed,condition_sha256='a'*64,times_ms=np.array([0.,10.,20.]),
                values={k:np.array(v)+delta for k,v in [('voicing',[-50.,-48.,-46.]),('breathiness',[-40.,-42.,-44.]),('tension',[-1.,0.,1.])]})


def test_balanced_joint_draws_preserve_conditioned_motion_and_order():
    draws=[sample(7,-2),sample(3,0),sample(5,2)]
    original=draws[0]['values']['voicing'].copy()
    a=variance_expectation(draws,'a'*64);b=variance_expectation(draws[::-1],'a'*64)
    for k in a['mean']:
        np.testing.assert_array_equal(a['mean'][k],sample(0,0)['values'][k])
        np.testing.assert_array_equal(a['mean'][k],b['mean'][k])
        assert np.all(a['sample_std'][k]>0)
    np.testing.assert_array_equal(original,draws[0]['values']['voicing'])


def test_repeated_seed_and_changed_conditions_cannot_fake_stability():
    draws=[sample(1,0),sample(2,1),sample(2,2)]
    with pytest.raises(ValueError,match='Duplicate'):variance_expectation(draws,'a'*64)
    draws[2]['seed']=3;draws[2]['condition_sha256']='b'*64
    with pytest.raises(ValueError,match='conditioning'):variance_expectation(draws,'a'*64)
    draws[2]['condition_sha256']='a'*64;draws[2]['times_ms'][1]=11
    with pytest.raises(ValueError,match='clock'):variance_expectation(draws,'a'*64)


def test_noise_prefix_is_independent_of_phrase_length_or_other_batch_members():
    small=gaussian_frame_noise(11,3,24,25);large=gaussian_frame_noise(11,3,24,70)
    np.testing.assert_array_equal(small,large[:,:,:,:25])
    assert not np.array_equal(small,gaussian_frame_noise(29,3,24,25))
