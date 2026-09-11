import cv2
import numpy as np
import pytest

from golf_swing_pose.analyzer import (
    ANGLE_TARGETS,
    PoseQualityError,
    PoseResult,
    calculate_angle,
    calculate_golf_metrics,
)
from golf_swing_pose.video import analyze_video


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


def test_analyze_video_writes_frame_records_and_outputs(tmp_path) -> None:
    input_path = tmp_path / "input.avi"
    output_video = tmp_path / "output" / "annotated.mp4"
    output_data = tmp_path / "output" / "metrics.json"
    writer = cv2.VideoWriter(
        str(input_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24)
    )
    writer.write(np.zeros((24, 32, 3), dtype=np.uint8))
    writer.write(np.full((24, 32, 3), 100, dtype=np.uint8))
    writer.release()

    class FakeAnalyzer:
        def analyze_image(self, frame):
            return PoseResult(
                angles={"right_elbow": 90.0},
                visibility={"right_elbow": 1.0},
                metrics={"weight_shift_proxy": 0.1},
                warnings=(),
                annotated_image=frame,
            )

    report = analyze_video(input_path, output_video, output_data, FakeAnalyzer())

    assert report["frame_count"] == 2
    assert all(frame["pose_detected"] for frame in report["frames"])
    assert output_video.is_file()
    assert output_data.is_file()


def test_analyze_video_records_missing_pose_without_stopping(tmp_path) -> None:
    input_path = tmp_path / "input.avi"
    output_video = tmp_path / "annotated.mp4"
    output_data = tmp_path / "metrics.json"
    writer = cv2.VideoWriter(
        str(input_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24)
    )
    writer.write(np.zeros((24, 32, 3), dtype=np.uint8))
    writer.release()

    class MissingPoseAnalyzer:
        def analyze_image(self, frame):
            raise PoseQualityError("No pose detected")

    report = analyze_video(input_path, output_video, output_data, MissingPoseAnalyzer())

    assert report["frame_count"] == 1
    assert report["frames"][0]["pose_detected"] is False
    assert report["frames"][0]["warnings"] == ["No pose detected"]
