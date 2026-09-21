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
from golf_swing_pose.coaching import build_coaching_feedback, summarize_reference_swings
from golf_swing_pose.phase_analysis import (
    build_phase_timeline,
    compare_swing_to_reference,
    detect_swing_phases,
    generate_coaching_summary,
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
    assert "phase_summary" in report
    assert "coaching_summary" in report
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


def test_detect_swing_phases_and_summary_from_timeline() -> None:
    frames = [
        {"frame": 0, "timestamp_seconds": 0.0, "right_elbow": 160.0, "hip_rotation_proxy": 0.0,
         "head_offset_proxy": 0.21, "weight_shift_proxy": 0.10},
        {"frame": 1, "timestamp_seconds": 0.1, "right_elbow": 130.0, "hip_rotation_proxy": 3.0,
         "head_offset_proxy": 0.25, "weight_shift_proxy": 0.12},
        {"frame": 2, "timestamp_seconds": 0.2, "right_elbow": 90.0, "hip_rotation_proxy": 15.0,
         "head_offset_proxy": 0.33, "weight_shift_proxy": 0.14},
        {"frame": 3, "timestamp_seconds": 0.3, "right_elbow": 110.0, "hip_rotation_proxy": 24.0,
         "head_offset_proxy": 0.41, "weight_shift_proxy": 0.26},
        {"frame": 4, "timestamp_seconds": 0.4, "right_elbow": 140.0, "hip_rotation_proxy": 30.0,
         "head_offset_proxy": 0.44, "weight_shift_proxy": 0.45},
        {"frame": 5, "timestamp_seconds": 0.5, "right_elbow": 150.0, "hip_rotation_proxy": 32.0,
         "head_offset_proxy": 0.47, "weight_shift_proxy": 0.55},
    ]

    phases = detect_swing_phases(frames)
    summary = generate_coaching_summary(frames)

    assert phases["address"] == 0
    assert phases["top_of_backswing"] == 2
    assert "impact" in phases
    assert phases["finish"] == 5
    assert any("right elbow" in item.lower() for item in summary)


def test_build_phase_timeline_labels_each_frame() -> None:
    frames = [
        {"frame": 0, "timestamp_seconds": 0.0, "right_elbow": 170.0},
        {"frame": 1, "timestamp_seconds": 0.1, "right_elbow": 150.0},
        {"frame": 2, "timestamp_seconds": 0.2, "right_elbow": 90.0},
        {"frame": 3, "timestamp_seconds": 0.3, "right_elbow": 100.0},
        {"frame": 4, "timestamp_seconds": 0.4, "right_elbow": 140.0},
        {"frame": 5, "timestamp_seconds": 0.5, "right_elbow": 150.0},
    ]

    timeline = build_phase_timeline(frames)

    assert [entry["phase"] for entry in timeline] == [
        "address",
        "backswing",
        "top_of_backswing",
        "downswing",
        "impact",
        "finish",
    ]


def test_compare_swing_to_reference_returns_phase_deltas() -> None:
    reference_frames = [
        {"right_elbow": 160.0, "hip_rotation_proxy": 0.0, "head_offset_proxy": 0.2, "weight_shift_proxy": 0.1},
        {"right_elbow": 100.0, "hip_rotation_proxy": 20.0, "head_offset_proxy": 0.3, "weight_shift_proxy": 0.3},
        {"right_elbow": 150.0, "hip_rotation_proxy": 30.0, "head_offset_proxy": 0.5, "weight_shift_proxy": 0.6},
    ]
    candidate_frames = [
        {"right_elbow": 165.0, "hip_rotation_proxy": 0.0, "head_offset_proxy": 0.25, "weight_shift_proxy": 0.12},
        {"right_elbow": 110.0, "hip_rotation_proxy": 18.0, "head_offset_proxy": 0.35, "weight_shift_proxy": 0.28},
        {"right_elbow": 160.0, "hip_rotation_proxy": 35.0, "head_offset_proxy": 0.52, "weight_shift_proxy": 0.58},
    ]

    comparison = compare_swing_to_reference(reference_frames, candidate_frames)

    assert comparison["top_of_backswing"]["right_elbow_delta"] == pytest.approx(10.0)
    assert comparison["impact"]["weight_shift_delta"] == pytest.approx(-0.02)
    assert comparison["summary"]["largest_delta"] in {"right_elbow", "weight_shift", "hip_rotation", "head_offset"}


def test_summarize_reference_swings_builds_average_phase_baseline() -> None:
    reference_swings = [
        {
            "phase_summary": {"top_of_backswing": 2, "impact": 4},
            "address": {"right_elbow": 170.0, "weight_shift": 0.10},
            "top_of_backswing": {"right_elbow": 95.0, "weight_shift": 0.25},
            "impact": {"right_elbow": 150.0, "weight_shift": 0.60},
        },
        {
            "phase_summary": {"top_of_backswing": 3, "impact": 5},
            "address": {"right_elbow": 168.0, "weight_shift": 0.12},
            "top_of_backswing": {"right_elbow": 100.0, "weight_shift": 0.30},
            "impact": {"right_elbow": 145.0, "weight_shift": 0.55},
        },
    ]

    baseline = summarize_reference_swings(reference_swings)

    assert baseline["top_of_backswing"]["right_elbow"] == pytest.approx(97.5)
    assert baseline["impact"]["weight_shift"] == pytest.approx(0.575)


def test_build_coaching_feedback_creates_rule_based_feedback() -> None:
    baseline = {
        "address": {"right_elbow": 170.0, "weight_shift": 0.10},
        "top_of_backswing": {"right_elbow": 97.5, "weight_shift": 0.28},
        "impact": {"right_elbow": 147.5, "weight_shift": 0.58},
    }
    candidate = {
        "address": {"right_elbow": 170.0, "weight_shift": 0.10},
        "top_of_backswing": {"right_elbow": 118.0, "weight_shift": 0.18},
        "impact": {"right_elbow": 160.0, "weight_shift": 0.52},
    }

    feedback = build_coaching_feedback(baseline, candidate)

    assert any("right elbow" in item.lower() for item in feedback)
    assert any("weight shift" in item.lower() for item in feedback)
    assert len(feedback) >= 2
