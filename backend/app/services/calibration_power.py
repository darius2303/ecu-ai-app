from __future__ import annotations

from typing import Any

from app.models.schemas import ECUInput
from app.services.analyzer import analyze_ecu_data


def _summary_mean(item: dict[str, Any]) -> float | None:
    summary = item.get("modified_summary") or item.get("summary") or {}
    value = summary.get("mean")
    return float(value) if isinstance(value, (int, float)) else None


def _normalize_boost(value: float | None, is_turbo: bool) -> float:
    if not is_turbo:
        return 1.0
    if value is None:
        return 1.55
    if value > 300.0:
        return max(0.8, min(2.6, value / 1000.0))
    if value > 20.0:
        return max(0.8, min(2.6, value / 100.0))
    return max(0.8, min(2.6, value))


def _normalize_injection(value: float | None) -> float:
    if value is None:
        return 55.0
    if value > 500.0:
        return max(8.0, min(95.0, value / 100.0))
    return max(8.0, min(95.0, value))


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
            "reason": "Lipsesc date motor: " + ", ".join(missing),
            "confidence": "low",
        }

    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in map_results:
        by_category.setdefault(str(item.get("category") or "unknown"), []).append(item)

    boost_mean = _summary_mean(by_category.get("boost", [{}])[0]) if by_category.get("boost") else None
    fuel_mean = _summary_mean(by_category.get("fuel", [{}])[0]) if by_category.get("fuel") else None

    rpm = 3500.0 if is_turbo else 4500.0
    boost_pressure = _normalize_boost(boost_mean, is_turbo)
    injection_quantity = _normalize_injection(fuel_mean)
    afr = 14.7 if fuel_type == "diesel" else 13.2 if is_turbo else 14.0

    confidence = "low"
    if by_category.get("boost") and by_category.get("fuel"):
        confidence = "medium"
    if by_category.get("boost") and by_category.get("fuel") and by_category.get("air_fuel"):
        confidence = "medium-high"

    try:
        result = analyze_ecu_data(
            ECUInput(
                rpm=rpm,
                boost_pressure=boost_pressure,
                injection_quantity=injection_quantity,
                afr=afr,
                engine_displacement=engine_displacement,
                fuel_type=fuel_type,  # type: ignore[arg-type]
                is_turbo=is_turbo,
                stock_hp=stock_hp,
            )
        )
    except Exception as exc:  # model load / validation errors should not break calibration analysis
        return {
            "available": False,
            "reason": f"Estimarea nu a putut fi calculata: {exc}",
            "confidence": "low",
        }

    result.update(
        {
            "available": True,
            "confidence": confidence,
            "source": "calibration_maps",
            "derived_inputs": {
                "rpm": rpm,
                "boost_pressure": boost_pressure,
                "injection_quantity": injection_quantity,
                "afr": afr,
            },
            "note": "Estimare euristica din harti binare + definitii; valideaza cu loguri si dyno.",
        }
    )
    return result
