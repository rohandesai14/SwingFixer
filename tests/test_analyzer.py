import numpy as np
import pytest

from golf_swing_pose.analyzer import ANGLE_TARGETS, calculate_angle, calculate_golf_metrics


def test_calculate_angle_returns_right_angle() -> None:
    assert calculate_angle(np.array([1, 0]), np.array([0, 0]), np.array([0, 1])) == pytest.approx(90)


def test_calculate_angle_rejects_coincident_points() -> None:
    with pytest.raises(ValueError):
        calculate_angle(np.array([0, 0]), np.array([0, 0]), np.array([1, 1]))


def test_right_elbow_target_matches_top_of_backswing_position() -> None:
    target = ANGLE_TARGETS["right_elbow"]

    assert target.low == 80
    assert target.high == 110
    assert target.low <= 90 <= target.high


def test_calculate_golf_metrics_returns_single_frame_proxies() -> None:
    points = {
        "nose": np.array([0.5, 0.1]),
        "left_shoulder": np.array([0.4, 0.3]),
        "right_shoulder": np.array([0.6, 0.3]),
        "left_hip": np.array([0.45, 0.6]),
        "right_hip": np.array([0.55, 0.6]),
        "left_ankle": np.array([0.4, 0.95]),
        "right_ankle": np.array([0.6, 0.95]),
    }

    metrics = calculate_golf_metrics(points)

    assert metrics["spine_angle"] == pytest.approx(0)
    assert metrics["shoulder_rotation_proxy"] == pytest.approx(0)
    assert metrics["hip_rotation_proxy"] == pytest.approx(0)
    assert metrics["head_offset_proxy"] == pytest.approx(2 / 3)
    assert metrics["weight_shift_proxy"] == pytest.approx(0)
