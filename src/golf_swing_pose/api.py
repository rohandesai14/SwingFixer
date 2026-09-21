"""HTTP API for submitting and retrieving swing analyses."""

from __future__ import annotations

import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .video import analyze_video

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JOB_ROOT = PROJECT_ROOT / "output" / "api_jobs"
REFERENCE_BASELINE = PROJECT_ROOT / "output" / "reference_baseline.json"

app = FastAPI(title="SwingFixer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()


def _update_job(job_id: str, **values: Any) -> None:
    with jobs_lock:
        jobs[job_id].update(values)


def _run_analysis(job_id: str, input_path: Path, output_dir: Path) -> None:
    try:
        _update_job(job_id, status="processing")
        baseline = None
        if REFERENCE_BASELINE.is_file():
            import json

            baseline_data = json.loads(REFERENCE_BASELINE.read_text(encoding="utf-8"))
            baseline = baseline_data.get("baseline", baseline_data)
        report_path = output_dir / "report.json"
        video_path = output_dir / "annotated.mp4"
        report = analyze_video(input_path, video_path, report_path, reference_baseline=baseline)
        _update_job(
            job_id,
            status="complete",
            frame_count=report["frame_count"],
            report_url=f"/api/analysis/{job_id}/report",
            video_url=f"/api/analysis/{job_id}/video",
        )
    except Exception as error:
        _update_job(job_id, status="failed", error=str(error))


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analysis", status_code=202)
async def create_analysis(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A video filename is required")
    job_id = uuid.uuid4().hex
    output_dir = JOB_ROOT / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = output_dir / Path(file.filename).name
    with input_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "queued", "filename": file.filename}
    threading.Thread(target=_run_analysis, args=(job_id, input_path, output_dir), daemon=True).start()
    return {"id": job_id, "status": "queued"}


@app.get("/api/analysis/{job_id}/status")
def analysis_status(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return job


@app.get("/api/analysis/{job_id}/report")
def analysis_report(job_id: str) -> FileResponse:
    job = _get_job(job_id)
    report_path = JOB_ROOT / job_id / "report.json"
    if job.get("status") != "complete" or not report_path.is_file():
        raise HTTPException(status_code=409, detail="Analysis is not complete")
    return FileResponse(report_path, media_type="application/json")


@app.get("/api/analysis/{job_id}/video")
def analysis_video(job_id: str) -> FileResponse:
    job = _get_job(job_id)
    video_path = JOB_ROOT / job_id / "annotated.mp4"
    if job.get("status") != "complete" or not video_path.is_file():
        raise HTTPException(status_code=409, detail="Analysis is not complete")
    return FileResponse(video_path, media_type="video/mp4", filename="annotated_swing.mp4")


def _get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return job