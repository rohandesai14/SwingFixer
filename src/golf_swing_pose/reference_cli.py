"""Command-line entry point for building a local reference baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .reference import write_reference_baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a coaching baseline from reference golf videos.")
    parser.add_argument("manifest", type=Path, help="Manifest containing reference video filenames")
    parser.add_argument("--output", type=Path, default=Path("output/reference_baseline.json"))
    args = parser.parse_args()

    report = write_reference_baseline(args.manifest, args.output)
    print(f"Reference baseline: {args.output}")
    print(f"Reference videos analyzed: {report['reference_count']}")


if __name__ == "__main__":
    main()
