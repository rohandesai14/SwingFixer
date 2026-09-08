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

Green labels are within approximate starter targets; red labels are outside
them. For the current top-of-backswing sample, the trail/right elbow target is
80–110 degrees, centered around the commonly coached approximately 90-degree
bend. It is not a universal target for every swing phase, handedness, or camera
view, and should be validated against labeled swings before coaching use.

## Phase 2 metrics

Static analysis now also reports a spine angle, shoulder and hip rotation
proxies, a normalized head offset proxy, and a normalized weight-shift proxy.
These are camera-view, single-frame measurements: rotation is a 2D line tilt,
head displacement is relative to the shoulder center, and weight shift compares
the ankle midpoint with the hip midpoint. They are intentionally labeled as
proxies until validated against multi-frame and 3D measurements. Low-visibility
landmarks are reported as warnings and unavailable metrics are omitted.

## Test the math

```sh
UV_CACHE_DIR=/private/tmp/golfswing-uv-cache uv run pytest
```
