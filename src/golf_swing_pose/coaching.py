"""Reference-based coaching rules for golf swing analysis."""

from __future__ import annotations

from statistics import mean
from typing import Sequence

from .phase_analysis import detect_swing_phases

PHASES = ("address", "top_of_backswing", "impact")
METRICS = ("right_elbow", "hip_rotation_proxy", "head_offset_proxy", "weight_shift_proxy")
METRIC_ALIASES = {
    "weight_shift_proxy": ("weight_shift_proxy", "weight_shift"),
    "right_elbow": ("right_elbow",),
    "hip_rotation_proxy": ("hip_rotation_proxy", "hip_rotation"),
    "head_offset_proxy": ("head_offset_proxy", "head_offset"),
}


def _metric_value(values: dict, metric: str) -> float | None:
    """Read a metric using its canonical name or a supported legacy alias."""
    for alias in METRIC_ALIASES[metric]:
        if alias in values:
            return float(values[alias])
    return None


def phase_snapshot(frames: Sequence[dict]) -> dict[str, dict[str, float]]:
    """Extract comparable metric values at the detected coaching phases."""
    phases = detect_swing_phases(frames)
    snapshot: dict[str, dict[str, float]] = {}
    for phase in PHASES:
        index = phases.get(phase)
        if index is None or not frames:
            continue
        frame = frames[min(len(frames) - 1, max(0, index))]
        snapshot[phase] = {}
        for metric in METRICS:
            for alias in METRIC_ALIASES[metric]:
                if alias in frame:
                    snapshot[phase][metric] = float(frame[alias])
                    break
    return snapshot


def summarize_reference_swings(reference_swings: Sequence[dict]) -> dict[str, dict[str, float]]:
    """Average a set of reference swings into a baseline for comparison."""
    if not reference_swings:
        return {}

    phases = PHASES
    baseline: dict[str, dict[str, float]] = {}
    for phase in phases:
        if not reference_swings:
            continue
        baseline[phase] = {}
        for metric in METRICS:
            values = [
                float(swing[phase][alias])
                for swing in reference_swings
                if phase in swing
                for alias in METRIC_ALIASES[metric]
                if alias in swing[phase]
            ]
            if values:
                baseline[phase][metric] = mean(values)
        if "weight_shift_proxy" in baseline[phase]:
            baseline[phase]["weight_shift"] = baseline[phase]["weight_shift_proxy"]
    return baseline


def build_coaching_feedback(baseline: dict[str, dict[str, float]], candidate: dict[str, dict[str, float]]) -> list[str]:
    """Translate phase delta comparisons into simple coaching messages."""
    feedback: list[str] = []
    metrics = (
        ("right_elbow", "right elbow"),
        ("weight_shift_proxy", "weight shift"),
    )

    for metric_key, metric_label in metrics:
        for phase in ("address", "top_of_backswing", "impact"):
            baseline_value = _metric_value(baseline.get(phase, {}), metric_key)
            candidate_value = _metric_value(candidate.get(phase, {}), metric_key)
            if baseline_value is None or candidate_value is None:
                continue
            delta = candidate_value - baseline_value
            if abs(delta) < 0.01:
                continue
            if metric_key == "right_elbow" and delta > 10:
                feedback.append(f"At {phase}, your right elbow is too straight compared with the reference baseline.")
            elif metric_key == "right_elbow" and delta < -10:
                feedback.append(f"At {phase}, your right elbow is more bent than the reference baseline; consider a slightly wider turn.")
            if metric_key == "weight_shift_proxy" and delta > 0.1:
                feedback.append(f"At {phase}, your weight shift is too far forward compared with the reference baseline.")
            elif metric_key == "weight_shift_proxy" and delta < -0.1:
                feedback.append(f"At {phase}, your weight shift is behind the reference baseline; load pressure earlier in the swing.")

    if not feedback:
        feedback.append("Your swing is tracking close to the reference baseline; keep the sequence consistent.")

    return feedback
