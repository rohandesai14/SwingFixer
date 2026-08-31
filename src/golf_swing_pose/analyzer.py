"""Single-frame pose detection, angle measurement, and annotation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


@dataclass(frozen=True)
class AngleTarget:
    low: float
    high: float


# These are intentionally broad starter ranges. Phase 2 should replace them with
# stance- and swing-phase-specific reference data.
ANGLE_TARGETS: Mapping[str, AngleTarget] = {
    "left_elbow": AngleTarget(145, 180),
    "right_elbow": AngleTarget(145, 180),
    "left_knee": AngleTarget(145, 175),
    "right_knee": AngleTarget(145, 175),
}

# BlazePose landmark indices. Keeping these here lets us use the current
# MediaPipe Tasks package, which no longer exports ``mp.solutions``.
LANDMARKS = {
    "LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12,
    "LEFT_ELBOW": 13, "RIGHT_ELBOW": 14,
    "LEFT_WRIST": 15, "RIGHT_WRIST": 16,
    "LEFT_HIP": 23, "RIGHT_HIP": 24,
    "LEFT_KNEE": 25, "RIGHT_KNEE": 26,
    "LEFT_ANKLE": 27, "RIGHT_ANKLE": 28,
}
POSE_CONNECTIONS = (
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28),
)


@dataclass
class PoseResult:
    angles: dict[str, float]
    visibility: dict[str, float]
    annotated_image: np.ndarray


def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return the smaller 2D angle ABC in degrees, from 0 through 180."""
    ba = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    bc = np.asarray(c, dtype=float) - np.asarray(b, dtype=float)
    denominator = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominator == 0:
        raise ValueError("Cannot calculate an angle from coincident points")
    cosine = np.clip(np.dot(ba, bc) / denominator, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


class PoseAnalyzer:
    """Analyze a static golf-swing image using MediaPipe Pose."""

    def __init__(self, min_visibility: float = 0.5, model_path: str | Path | None = None) -> None:
        self.min_visibility = min_visibility
        default_model = Path(__file__).resolve().parents[2] / "models" / "pose_landmarker_full.task"
        resolved_model = Path(model_path) if model_path else default_model
        if not resolved_model.is_file():
            raise FileNotFoundError(f"Pose Landmarker model is missing: {resolved_model}")
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(resolved_model),
                delegate=python.BaseOptions.Delegate.CPU,
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        self._pose = vision.PoseLandmarker.create_from_options(options)
        self._pose_connections = POSE_CONNECTIONS

    def close(self) -> None:
        self._pose.close()

    def __enter__(self) -> "PoseAnalyzer":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def analyze_file(self, path: str | Path) -> PoseResult:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {path}")
        return self.analyze_image(image)

    def analyze_image(self, image_bgr: np.ndarray) -> PoseResult:
        """Detect landmarks and return measured joints plus a visual overlay."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        detection = self._pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not detection.pose_landmarks:
            raise ValueError("No pose detected. Use a clear, full-body golf photo.")

        output = image_bgr.copy()
        points = detection.pose_landmarks[0]
        self._draw_skeleton(output, points)

        joint_specs = {
            "left_elbow": (LANDMARKS["LEFT_SHOULDER"], LANDMARKS["LEFT_ELBOW"], LANDMARKS["LEFT_WRIST"]),
            "right_elbow": (LANDMARKS["RIGHT_SHOULDER"], LANDMARKS["RIGHT_ELBOW"], LANDMARKS["RIGHT_WRIST"]),
            "left_knee": (LANDMARKS["LEFT_HIP"], LANDMARKS["LEFT_KNEE"], LANDMARKS["LEFT_ANKLE"]),
            "right_knee": (LANDMARKS["RIGHT_HIP"], LANDMARKS["RIGHT_KNEE"], LANDMARKS["RIGHT_ANKLE"]),
        }
        angles: dict[str, float] = {}
        visibility: dict[str, float] = {}

        height, width = output.shape[:2]
        for name, (first, vertex, third) in joint_specs.items():
            first_point, vertex_point, third_point = points[first], points[vertex], points[third]
            score = min(first_point.visibility, vertex_point.visibility, third_point.visibility)
            visibility[name] = float(score)
            if score < self.min_visibility:
                continue

            a = np.array([first_point.x, first_point.y])
            b = np.array([vertex_point.x, vertex_point.y])
            c = np.array([third_point.x, third_point.y])
            angle = calculate_angle(a, b, c)
            angles[name] = angle
            color = self._angle_color(name, angle)
            location = (int(vertex_point.x * width), int(vertex_point.y * height))
            cv2.putText(output, f"{name.replace('_', ' ')}: {angle:.0f}", location,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

        return PoseResult(angles=angles, visibility=visibility, annotated_image=output)

    @staticmethod
    def _angle_color(name: str, angle: float) -> tuple[int, int, int]:
        target = ANGLE_TARGETS[name]
        return (0, 180, 0) if target.low <= angle <= target.high else (0, 0, 255)

    def _draw_skeleton(self, image: np.ndarray, points: list[object]) -> None:
        """Draw task-API normalized landmarks without relying on the legacy graph."""
        height, width = image.shape[:2]
        for start, end in self._pose_connections:
            first, second = points[start], points[end]
            if min(first.visibility, second.visibility) < self.min_visibility:
                continue
            cv2.line(image, (int(first.x * width), int(first.y * height)),
                     (int(second.x * width), int(second.y * height)), (255, 255, 255), 2, cv2.LINE_AA)
        for point in points:
            if point.visibility >= self.min_visibility:
                cv2.circle(image, (int(point.x * width), int(point.y * height)), 3, (0, 255, 255), -1, cv2.LINE_AA)
