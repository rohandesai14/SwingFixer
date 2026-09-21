"""Simple swing-phase detection and coaching heuristics for a golf swing timeline."""

from __future__ import annotations

from typing import Sequence


def build_phase_timeline(frames: Sequence[dict]) -> list[dict]:
    """Assign a rough phase label to each frame in a swing timeline."""
    if not frames:
        return []

    phases = detect_swing_phases(frames)
    if not phases:
        return []

    address_index = phases.get("address", 0)
    top_index = phases.get("top_of_backswing", 0)
    impact_index = phases.get("impact", max(0, len(frames) - 1))
    finish_index = phases.get("finish", len(frames) - 1)

    timeline: list[dict] = []
    for idx, frame in enumerate(frames):
        if idx == address_index:
            label = "address"
        elif idx == top_index:
            label = "top_of_backswing"
        elif idx == impact_index:
            label = "impact"
        elif idx == finish_index:
            label = "finish"
        elif idx < top_index:
            label = "backswing"
        elif idx < impact_index:
            label = "downswing"
        else:
            label = "finish"

        timeline.append({
            "frame": frame.get("frame", idx),
            "timestamp_seconds": frame.get("timestamp_seconds", idx),
            "phase": label,
        })

    return timeline


def compare_swing_to_reference(reference_frames: Sequence[dict], candidate_frames: Sequence[dict]) -> dict[str, dict | str]:
    """Compare a candidate swing to a reference swing using a small phase-slice model."""
    if not reference_frames or not candidate_frames:
        return {"summary": {"largest_delta": "none"}}

    def pick_phase_frame(frames: Sequence[dict], phase: str) -> dict:
        if phase == "address":
            return frames[0]
        if phase == "top_of_backswing":
            return frames[min(len(frames) - 1, max(0, len(frames) // 2))]
        return frames[-1]

    phase_names = ["address", "top_of_backswing", "impact"]
    phase_map: dict[str, dict[str, float]] = {}
    for phase in phase_names:
        ref = pick_phase_frame(reference_frames, phase)
        cand = pick_phase_frame(candidate_frames, phase)
        phase_map[phase] = {
            "right_elbow_delta": float(cand.get("right_elbow", ref.get("right_elbow", 0.0)) - float(ref.get("right_elbow", 0.0))),
            "hip_rotation_delta": float(cand.get("hip_rotation_proxy", ref.get("hip_rotation_proxy", 0.0)) - float(ref.get("hip_rotation_proxy", 0.0))),
            "head_offset_delta": float(cand.get("head_offset_proxy", ref.get("head_offset_proxy", 0.0)) - float(ref.get("head_offset_proxy", 0.0))),
            "weight_shift_delta": float(cand.get("weight_shift_proxy", ref.get("weight_shift_proxy", 0.0)) - float(ref.get("weight_shift_proxy", 0.0))),
        }

    largest_key = "right_elbow"
    largest_value = max(abs(phase_map[phase]["right_elbow_delta"]) for phase in phase_names)
    for metric_name in ("hip_rotation", "head_offset", "weight_shift"):
        metric_value = max(abs(phase_map[phase][f"{metric_name}_delta"]) for phase in phase_names)
        if metric_value > largest_value:
            largest_key = metric_name
            largest_value = metric_value

    return {
        "address": phase_map["address"],
        "top_of_backswing": phase_map["top_of_backswing"],
        "impact": phase_map["impact"],
        "summary": {"largest_delta": largest_key},
    }


def detect_swing_phases(frames: Sequence[dict]) -> dict[str, int]:
    """Identify rough swing-phase indices from a per-frame metric timeline."""
    if not frames:
        return {}

    right_elbow_values = [float(frame.get("right_elbow", 180.0)) for frame in frames]
    if not right_elbow_values:
        return {"address": 0}

    min_elbow_index = min(range(len(right_elbow_values)), key=lambda i: right_elbow_values[i])
    post_top_indices = range(min_elbow_index, len(frames))
    max_rotation_index = max(
        post_top_indices,
        key=lambda i: float(frames[i].get("hip_rotation_proxy", 0.0)),
    )
    weight_shift_index = max(
        post_top_indices,
        key=lambda i: float(frames[i].get("weight_shift_proxy", 0.0)),
    )

    phases = {
        "address": 0,
        "top_of_backswing": min_elbow_index,
        "downswing": max(min_elbow_index + 1, max_rotation_index),
        "impact": max(min_elbow_index + 2, max_rotation_index, weight_shift_index),
        "finish": len(frames) - 1,
    }
    if phases["impact"] <= phases["downswing"]:
        phases["impact"] = min(len(frames) - 1, phases["downswing"] + 1)
    if phases["impact"] >= phases["finish"]:
        phases["impact"] = max(0, phases["finish"] - 1)

    return phases


def generate_coaching_summary(frames: Sequence[dict]) -> list[str]:
    """Return a simple, threshold-based coaching summary for the timeline."""
    if not frames:
        return []

    summary: list[str] = []
    right_elbow_values = [float(frame.get("right_elbow", 180.0)) for frame in frames]
    min_elbow = min(right_elbow_values)
    max_head_offset = max(float(frame.get("head_offset_proxy", 0.0)) for frame in frames)
    max_weight_shift = max(float(frame.get("weight_shift_proxy", 0.0)) for frame in frames)

    if min_elbow < 110:
        summary.append("Right elbow is compact at the top of the backswing; consider keeping it closer to an approximate 90-degree bend.")
    else:
        summary.append("Right elbow stays relatively straight through the swing; check if the trail arm is too extended on the backswing.")

    if max_head_offset > 0.45:
        summary.append("Head offset is elevated; monitor lateral head drift during the swing.")
    else:
        summary.append("Head offset remains moderate; keep head position stable through the motion.")

    if max_weight_shift < 0.25:
        summary.append("Weight shift appears limited; consider loading the trail side earlier in the swing.")
    else:
        summary.append("Weight shift is progressing through the motion; keep pressure moving toward the lead side at impact.")

    return summary
