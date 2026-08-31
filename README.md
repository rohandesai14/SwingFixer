# Golf Swing Pose Analyzer

Phase 1 detects a golfer's body pose in a single full-body image, measures elbow
and knee angles, and writes an annotated skeleton overlay.

## Setup (macOS)

This project deliberately uses Python 3.12. MediaPipe is not yet compatible with
the system Python 3.14 used on this machine.

The detector uses MediaPipe's CPU-delegated Task API and the included
`models/pose_landmarker_full.task` model. It removes the legacy pose API from
the application code. Run it from a logged-in macOS desktop session: the
headless execution host used for automated checks cannot create the internal
macOS graphics service required by MediaPipe, even when inference is CPU-based.

```sh
UV_CACHE_DIR=/private/tmp/golfswing-uv-cache \
UV_PYTHON_INSTALL_DIR="$PWD/.uv-python" \
uv sync --python 3.12
```

## Analyze an image

```sh
UV_CACHE_DIR=/private/tmp/golfswing-uv-cache \
UV_PYTHON_INSTALL_DIR="$PWD/.uv-python" \
uv run golf-pose path/to/swing.jpg --output output/swing_annotated.jpg
```

Green labels are within the deliberately broad starter targets; red labels are
outside them. These targets are not coaching prescriptions yet—they will be
replaced with phase- and stance-aware reference data in Phase 2.

## Test the math

```sh
UV_CACHE_DIR=/private/tmp/golfswing-uv-cache uv run pytest
```
