import pytest

from onboarding.depth_calibration import calibrate_depth_scale_factor


def test_underestimate_case_scales_up():
    assert calibrate_depth_scale_factor(known_distance_m=10.0, estimated_distance_m=8.0) == pytest.approx(1.25)


def test_overestimate_case_scales_down():
    assert calibrate_depth_scale_factor(known_distance_m=10.0, estimated_distance_m=12.0) == pytest.approx(10 / 12)


def test_perfect_model_is_a_no_op():
    assert calibrate_depth_scale_factor(known_distance_m=10.0, estimated_distance_m=10.0) == 1.0


def test_rejects_non_positive_distances():
    with pytest.raises(ValueError):
        calibrate_depth_scale_factor(0.0, 5.0)
    with pytest.raises(ValueError):
        calibrate_depth_scale_factor(10.0, -1.0)
