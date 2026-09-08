"""Command-line entry point for static-image analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from .analyzer import ANGLE_TARGETS, PoseAnalyzer


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate a golf photo with detected pose angles.")
    parser.add_argument("input", type=Path, help="Path to a full-body golf-swing image")
    parser.add_argument("-o", "--output", type=Path, default=Path("output/annotated_pose.jpg"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PoseAnalyzer() as analyzer:
        result = analyzer.analyze_file(args.input)
    if not cv2.imwrite(str(args.output), result.annotated_image):
        raise RuntimeError(f"Could not write output image: {args.output}")

    print(f"Annotated image: {args.output}")
    for joint, target in ANGLE_TARGETS.items():
        if joint not in result.angles:
            print(f"{joint}: unavailable (visibility {result.visibility.get(joint, 0):.0%})")
            continue
        angle = result.angles[joint]
        verdict = "within starter range" if target.low <= angle <= target.high else "outside starter range"
        print(f"{joint}: {angle:.1f}° — {verdict} ({target.low:.0f}–{target.high:.0f}°)")
    for name, value in result.metrics.items():
        print(f"{name}: {value:.3f} (single-frame 2D proxy)")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
