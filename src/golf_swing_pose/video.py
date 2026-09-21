"""Frame-by-frame golf swing video analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2

from .analyzer import PoseAnalyzer, PoseQualityError
from .coaching import build_coaching_feedback, phase_snapshot
from .phase_analysis import detect_swing_phases, generate_coaching_summary


def analyze_video(
    input_path: str | Path,
    output_video: str | Path,
    output_data: str | Path,
    analyzer: PoseAnalyzer | Any | None = None,
    reference_baseline: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Analyze every video frame and write annotated video plus JSON metrics."""
    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {input_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        capture.release()
        raise ValueError(f"Could not read video dimensions: {input_path}")

    output_video_path = Path(output_video)
    output_data_path = Path(output_data)
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    output_data_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise ValueError(f"Could not create output video: {output_video}")

    pose_analyzer = analyzer
    owns_analyzer = analyzer is None
    records: list[dict[str, Any]] = []
    frame_index = 0
    try:
        if pose_analyzer is None:
            pose_analyzer = PoseAnalyzer()
        while True:
            success, frame = capture.read()
            if not success:
                break

            timestamp = frame_index / fps
            try:
                result = pose_analyzer.analyze_image(frame)
            except PoseQualityError as error:
                writer.write(frame)
                records.append({
                    "frame": frame_index,
                    "timestamp_seconds": timestamp,
                    "pose_detected": False,
                    "angles": {},
                    "metrics": {},
                    "visibility": {},
                    "warnings": [str(error)],
                })
            else:
                writer.write(result.annotated_image)
                records.append({
                    "frame": frame_index,
                    "timestamp_seconds": timestamp,
                    "pose_detected": True,
                    "angles": result.angles,
                    "metrics": result.metrics,
                    "visibility": result.visibility,
                    "warnings": list(result.warnings),
                })
            frame_index += 1
    finally:
        capture.release()
        writer.release()
        if owns_analyzer and pose_analyzer is not None:
            pose_analyzer.close()

    phase_frames = []
    for record in records:
        if not record.get("pose_detected"):
            continue
        metrics = record.get("metrics", {})
        phase_frames.append({
            "frame": record.get("frame"),
            "timestamp_seconds": record.get("timestamp_seconds"),
            "right_elbow": record.get("angles", {}).get("right_elbow", 180.0),
            "hip_rotation_proxy": metrics.get("hip_rotation_proxy", 0.0),
            "head_offset_proxy": metrics.get("head_offset_proxy", 0.0),
            "weight_shift_proxy": metrics.get("weight_shift_proxy", 0.0),
        })

    report = {
        "input": str(input_path),
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": len(records),
        "frames": records,
        "phase_summary": detect_swing_phases(phase_frames),
        "coaching_summary": generate_coaching_summary(phase_frames),
    }
    if reference_baseline:
        candidate_snapshot = phase_snapshot(phase_frames)
        report["reference_baseline"] = reference_baseline
        report["reference_comparison"] = {
            phase: {
                metric: candidate_snapshot.get(phase, {}).get(metric, 0.0) - value
                for metric, value in reference_baseline.get(phase, {}).items()
                if metric != "weight_shift"
            }
            for phase in reference_baseline
        }
        report["coaching_feedback"] = build_coaching_feedback(
            reference_baseline,
            candidate_snapshot,
        )
    output_data_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report