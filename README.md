# SwingFixer

SwingFixer analyzes golf swings with MediaPipe pose tracking, identifies rough
swing phases, compares them with a local reference baseline, and turns the
differences into coaching feedback. It includes a Python analysis backend, a
FastAPI service, and a browser dashboard.

## Project workflow

```text
video upload -> pose metrics -> phase detection -> reference comparison -> coaching feedback
```

The reference dataset is intentionally local. The tracked manifest at
`refs/pro_baseline_manifest.txt` points to selected GolfDB clips, while the
larger raw `videos_160/` directory is ignored.

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

## Run the tests

```sh
UV_CACHE_DIR=/private/tmp/golfswing-uv-cache uv run pytest
```

## Phase 3: Analyze a video

The video pipeline reads every frame, writes an annotated video, and saves one
JSON record per frame. Frames without a detected pose are preserved in the
output video and recorded with a warning instead of stopping the run.

```sh
uv run golf-video path/to/swing.mp4 \
	--output-video output/swing_annotated.mp4 \
	--output-data output/swing_metrics.json
```

For example, a local video can be analyzed with:

```sh
uv run golf-video swing_video.MOV \
	--output-video output/swing_video_annotated.mp4 \
	--output-data output/swing_video_metrics.json
```

The annotated MP4 can be opened with QuickTime or VLC. The JSON file contains
one record per frame, including timestamps, detected angles, Phase 2 metrics,
visibility values, and warnings.

## Build a local reference baseline

The selected GolfDB clips can be aggregated into a reusable phase-level
baseline. This analyzes the manifest clips once and stores the result as JSON:

```sh
uv run golf-reference refs/pro_baseline_manifest.txt \
	--output output/reference_baseline.json
```

Use that baseline when analyzing a candidate swing:

```sh
uv run golf-video swing_video.MOV \
	--reference-baseline output/reference_baseline.json \
	--output-video output/swing_video_reference_annotated.mp4 \
	--output-data output/swing_video_reference_metrics.json
```

The report includes `reference_baseline`, `reference_comparison`, and
`coaching_feedback` alongside the frame metrics and general coaching summary.

## Run the API

Start the live analysis service from the project root:

```sh
uv run golf-api
```

The API listens on `http://localhost:8000` and exposes:

```text
GET  /api/health
POST /api/analysis
GET  /api/analysis/{id}/status
GET  /api/analysis/{id}/report
GET  /api/analysis/{id}/video
```

Jobs run in the background. The service automatically uses
`output/reference_baseline.json` when that baseline exists.

## Run the frontend

The frontend is a React and TypeScript Vite dashboard under `frontend/`. Install
Node.js 20 or newer, then install and start it in a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.
Choose a video and select **Analyze video** to
submit it to the API, poll the analysis job, and load the annotated result.

The React entry point is `frontend/src/main.tsx`, and the dashboard is composed
in `frontend/src/App.tsx`. The frontend package provides these scripts:

```text
npm run dev        start the Vite development server
npm run typecheck  run strict TypeScript validation
npm run build      create a production bundle
npm run preview    serve the production bundle locally
```

If the API is running on its default port, start both services in separate
terminals before using live analysis:

```sh
# Terminal 1, project root
uv run golf-api

# Terminal 2, frontend/
npm run dev
```

The browser dashboard calls the FastAPI service at `http://localhost:8000`.
The dashboard includes:

- annotated video playback
- phase timeline and frame navigation
- frame-by-frame motion profiles
- reference values and phase deltas
- general and reference-based coaching feedback

For reopening an existing analysis without processing the video again, use
**Load report JSON** and select a previously generated report.

Run the frontend checks with:

```sh
npm run typecheck
npm run build
```

## Known limitations

- Phase detection and metrics are heuristic 2D camera-view proxies.
- The reference clips have varied camera setups, so comparisons are useful for
	directional feedback rather than clinical measurement.
- API jobs are held in memory and are intended for local use; restarting the
	API clears the job list.
