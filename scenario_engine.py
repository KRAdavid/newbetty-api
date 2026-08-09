from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

MOISTURE_RANGES = {
    "DRY": (0.0, 5.0),
    "GOOD": (6.0, 9.0),
    "MOIST": (10.0, 14.0),
    "SATURATED": (15.0, 19.0),
    "POOR": (20.0, 100.0),
}

@dataclass(frozen=True)
class SurfaceScenario:
    track_condition: str
    moisture_percent: float
    moisture_band: str
    pace_pressure: str

def validate_surface_scenario(track_condition: str, moisture_percent: Any, pace_pressure: str = "MODEL_AUTO") -> SurfaceScenario:
    condition = {"건조": "DRY", "양호": "GOOD", "다습": "MOIST", "포화": "SATURATED", "불량": "POOR"}.get(str(track_condition or "").strip(), str(track_condition or "").strip()).upper()
    if condition not in MOISTURE_RANGES:
        raise ValueError("track_condition must be one of DRY, GOOD, MOIST, SATURATED, POOR")
    try:
        moisture = float(moisture_percent)
    except (TypeError, ValueError) as exc:
        raise ValueError("moisture_percent must be a number") from exc
    if not 0 <= moisture <= 100:
        raise ValueError("moisture_percent must be between 0 and 100")
    low, high = MOISTURE_RANGES[condition]
    if not low <= moisture <= high:
        raise ValueError(f"{condition} requires moisture_percent between {low:g} and {high:g}")
    pressure = str(pace_pressure or "MODEL_AUTO").strip().upper()
    if pressure not in {"MODEL_AUTO", "LOW", "MEDIUM", "HIGH"}:
        raise ValueError("pace_pressure must be MODEL_AUTO, LOW, MEDIUM, or HIGH")
    return SurfaceScenario(condition, round(moisture, 3), condition, pressure)

def _surface_fit(observations: Iterable[dict[str, Any]], target: SurfaceScenario) -> tuple[float | None, int]:
    values = []
    for item in observations:
        try:
            moisture = float(item["moisture_percent"])
            top3 = float(item["top3"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 0 <= moisture <= 100 or not 0 <= top3 <= 1:
            continue
        distance = abs(moisture - target.moisture_percent)
        similarity = max(0.0, 1.0 - distance / 25.0)
        values.append((top3, similarity))
    if not values:
        return None, 0
    weight = sum(similarity for _, similarity in values)
    if weight <= 0:
        return None, 0
    return round(sum(top3 * similarity for top3, similarity in values) / weight, 4), len(values)

def rescore_entries(entries: list[dict[str, Any]], scenario: SurfaceScenario) -> dict[str, Any]:
    ranked = []
    insufficient = []
    for entry in entries:
        observations = entry.get("surface_history") or []
        fit, support = _surface_fit(observations, scenario)
        if support < 3 or fit is None:
            insufficient.append(int(entry.get("runner_no") or 0))
            continue
        try:
            base = float(entry.get("base_score"))
        except (TypeError, ValueError):
            base = None
        if base is None:
            insufficient.append(int(entry.get("runner_no") or 0))
            continue
        ranked.append({
            "runner_no": int(entry.get("runner_no") or 0),
            "horse_name": str(entry.get("horse_name") or ""),
            "score": round(base + (fit - 0.5) * 8.0, 4),
            "surface_fit": fit,
            "surface_support": support,
        })
    ranked.sort(key=lambda item: (-item["score"], item["runner_no"]))
    if not ranked or insufficient:
        return {
            "status": "HOLD",
            "rescored": False,
            "release_blocked": True,
            "reason_code": "INSUFFICIENT_PAST_SURFACE_EVIDENCE",
            "insufficient_runner_numbers": insufficient,
            "ranking": [],
        }
    for index, item in enumerate(ranked, 1):
        item["rank"] = index
    return {
        "status": "READY",
        "rescored": True,
        "release_blocked": False,
        "reason_code": None,
        "ranking": ranked,
    }
