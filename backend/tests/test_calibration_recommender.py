from app.services.calibration_recommender import generate_power_recommendations


def _map(name: str, category: str, changed_percent: float = 0.0, max_delta: float = 0.0):
    return {
        "name": name,
        "category": category,
        "diff": {
            "changed_cells": 1 if changed_percent else 0,
            "changed_percent": changed_percent,
            "max_abs_delta": max_delta,
            "direction": "increase" if changed_percent else "unchanged",
        },
    }


def test_missing_map_categories_returns_definitions_recommendation():
    recommendations = generate_power_recommendations(
        map_results=[],
        has_modified=True,
        fuel_type="petrol",
        is_turbo=False,
    )

    assert len(recommendations) == 1
    assert recommendations[0]["category"] == "definitions"
    assert recommendations[0]["mode"] == "missing_context"
    assert recommendations[0]["priority"] == "high"


def test_limiter_change_receives_high_risk_when_delta_is_large():
    recommendations = generate_power_recommendations(
        map_results=[_map("RPM Limiter", "limiter", changed_percent=100, max_delta=1000)],
        has_modified=True,
        fuel_type="petrol",
        is_turbo=False,
    )

    limiter = recommendations[0]
    assert limiter["category"] == "limiter"
    assert limiter["risk"] == "high"
    assert limiter["priority"] in {"medium", "high"}
    assert "protections" in " ".join(limiter["risks"])


def test_original_only_mode_produces_planning_recommendation():
    recommendations = generate_power_recommendations(
        map_results=[_map("Torque request", "torque")],
        has_modified=False,
        fuel_type="petrol",
        is_turbo=False,
    )

    recommendation = recommendations[0]
    assert recommendation["category"] == "torque"
    assert recommendation["mode"] == "suggest_next_change"
    assert recommendation["mode_label"] == "Original-only planning"
