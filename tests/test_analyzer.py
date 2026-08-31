import numpy as np
import pytest

from golf_swing_pose.analyzer import calculate_angle


def test_calculate_angle_returns_right_angle() -> None:
    assert calculate_angle(np.array([1, 0]), np.array([0, 0]), np.array([0, 1])) == pytest.approx(90)


def test_calculate_angle_rejects_coincident_points() -> None:
    with pytest.raises(ValueError):
        calculate_angle(np.array([0, 0]), np.array([0, 0]), np.array([1, 1]))
