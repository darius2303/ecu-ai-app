from __future__ import annotations

from typing import Any


def estimate_power_from_calibration(
    map_results: list[dict[str, Any]],
    *,
    engine_displacement: float | None,
    fuel_type: str | None,
    is_turbo: bool | None,
    stock_hp: float | None,
) -> dict[str, Any]:
    missing = []
    if engine_displacement is None:
        missing.append("engine_displacement")
    if fuel_type is None:
        missing.append("fuel_type")
    if is_turbo is None:
        missing.append("is_turbo")
    if missing:
        return {
            "available": False,
            "reason": "Missing engine data: " + ", ".join(missing),
            "confidence": "low",
        }

    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in map_results:
        by_category.setdefault(str(item.get("category") or "unknown"), []).append(item)

    changed_maps = [
        item for item in map_results
        if (item.get("diff") or {}).get("changed_cells", 0) > 0
    ]
    if not changed_maps:
        return {
            "available": False,
            "reason": "No modified maps were available for a rough power estimate.",
            "confidence": "low",
        }

    category_weights = {
        "torque": 0.055,
        "fuel": 0.04,
        "boost": 0.05 if is_turbo else 0.01,
        "air_fuel": 0.035,
        "timing": 0.018,
        "rail_pressure": 0.022,
        "limiter": 0.008,
    }
    gain = 0.0
    changed_categories: set[str] = set()
    for item in changed_maps:
        category = str(item.get("category") or "unknown")
        changed_categories.add(category)
        diff = item.get("diff") or {}
        changed_percent = float(diff.get("changed_percent") or 0.0)
        max_delta = float(diff.get("max_abs_delta") or 0.0)
        direction = str(diff.get("direction") or "unchanged")
        direction_factor = 1.0 if direction == "increase" else 0.4 if direction == "mixed" else 0.15
        magnitude_factor = min(1.35, 0.75 + min(max_delta, 25.0) / 50.0)
        gain += category_weights.get(category, 0.005) * changed_percent * direction_factor * magnitude_factor

    if "torque" in changed_categories and ("fuel" in by_category or "air_fuel" in by_category):
        gain += 1.0
    if is_turbo and "boost" in changed_categories:
        gain += 1.2
    if "limiter" in changed_categories and changed_categories.isdisjoint({"torque", "fuel", "boost", "air_fuel"}):
        gain = min(gain, 2.0)

    if fuel_type == "petrol" and not is_turbo:
        gain *= 0.8
    if fuel_type == "diesel" and is_turbo:
        gain *= 1.08

    gain = max(0.0, min(18.0, gain))

    confidence = "low"
    if by_category.get("fuel") and by_category.get("air_fuel"):
        confidence = "medium"
    if by_category.get("torque") and by_category.get("fuel") and by_category.get("air_fuel"):
        confidence = "medium-high"

    estimated_hp = None
    if stock_hp is not None:
        estimated_hp = round(float(stock_hp) * (1.0 + gain / 100.0), 2)

    potential_class = "Low"
    if gain >= 9.0:
        potential_class = "High"
    elif gain >= 4.0:
        potential_class = "Moderate"

    return {
        "available": True,
        "stage1_gain_percent": round(gain, 2),
        "potential_class": potential_class,
        "estimated_hp_after_stage1": estimated_hp,
        "confidence": confidence,
        "source": "calibration_heuristic",
        "derived_inputs": {
            "changed_categories": sorted(changed_categories),
            "changed_maps": len(changed_maps),
        },
        "note": "Rough heuristic estimate from map changes; validate with logs and dyno data.",
    }
