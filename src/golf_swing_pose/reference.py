"""Build a reusable coaching baseline from local reference videos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2

from .analyzer import PoseAnalyzer, PoseQualityError
from .coaching import phase_snapshot, summarize_reference_swings


def load_manifest(manifest_path: str | Path) -> list[Path]:
    """Return existing video paths listed in a manifest."""
    manifest = Path(manifest_path)
    paths = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name and not name.startswith("#"):
            path = Path(name)
            if not path.is_absolute():
                path = manifest.parent.parent / "videos_160" / path.name
            if path.is_file():
                paths.append(path)
    return paths


def analyze_reference_video(video_path: str | Path, analyzer: Any | None = None) -> dict[str, dict[str, float]]:
    """Extract phase metrics from one reference video without writing an annotated copy."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open reference video: {video_path}")

    pose_analyzer = analyzer or PoseAnalyzer()
    owns_analyzer = analyzer is None
    frames: list[dict[str, float]] = []
    try:
        frame_index = 0
        while True:
            success, frame = capture.read()
            if not success:
                break
            try:
                result = pose_analyzer.analyze_image(frame)
            except PoseQualityError:
                frame_index += 1
                continue
            frames.append({
                "frame": float(frame_index),
                "right_elbow": result.angles.get("right_elbow", 180.0),
                **result.metrics,
            })
            frame_index += 1
    finally:
        capture.release()
        if owns_analyzer:
            pose_analyzer.close()

    return phase_snapshot(frames)


def build_reference_baseline(manifest_path: str | Path) -> dict[str, Any]:
    """Analyze all manifest clips and return the aggregate baseline and metadata."""
    paths = load_manifest(manifest_path)
    swings = []
    analyzed_paths = []
    for path in paths:
        snapshot = analyze_reference_video(path)
        if snapshot:
            swings.append(snapshot)
            analyzed_paths.append(str(path))

    return {
        "source_manifest": str(manifest_path),
        "reference_count": len(swings),
        "reference_videos": analyzed_paths,
        "baseline": summarize_reference_swings(swings),
    }


def write_reference_baseline(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Build and write a JSON reference baseline."""
    report = build_reference_baseline(manifest_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
