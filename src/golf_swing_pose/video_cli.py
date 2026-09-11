"""Command-line entry point for video analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from .video import analyze_video


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a golf swing video frame by frame.")
    parser.add_argument("input", type=Path, help="Path to a golf swing video")
    parser.add_argument("--output-video", type=Path, default=Path("output/annotated_swing.mp4"))
    parser.add_argument("--output-data", type=Path, default=Path("output/swing_metrics.json"))
    args = parser.parse_args()

    report = analyze_video(args.input, args.output_video, args.output_data)
    detected = sum(frame["pose_detected"] for frame in report["frames"])
    print(f"Annotated video: {args.output_video}")
    print(f"Metrics JSON: {args.output_data}")
    print(f"Frames analyzed: {report['frame_count']} ({detected} with detected poses)")


if __name__ == "__main__":
    main()