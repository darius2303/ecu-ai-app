from app.services.calibration_power import estimate_power_from_calibration


def _map(category: str, changed_percent: float, max_delta: float, direction: str = "increase"):
    return {
        "category": category,
        "diff": {
            "changed_cells": 4 if changed_percent else 0,
            "changed_percent": changed_percent,
            "max_abs_delta": max_delta,
            "direction": direction,
        },
    }


def test_power_estimate_requires_engine_context():
    estimate = estimate_power_from_calibration(
        [_map("torque", 50, 12)],
        engine_displacement=None,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=100,
    )

    assert estimate["available"] is False
    assert "engine_displacement" in estimate["reason"]


def test_power_estimate_is_unavailable_without_modified_maps():
    estimate = estimate_power_from_calibration(
        [_map("torque", 0, 0)],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=100,
    )

    assert estimate["available"] is False
    assert "No modified maps" in estimate["reason"]


def test_power_estimate_combines_torque_fuel_air_and_boost_context():
    estimate = estimate_power_from_calibration(
        [
            _map("torque", 70, 16),
            _map("fuel", 30, 8),
            _map("air_fuel", 20, 5),
            _map("boost", 25, 4),
        ],
        engine_displacement=1.0,
        fuel_type="diesel",
        is_turbo=True,
        stock_hp=100,
    )

    assert estimate["available"] is True
    assert estimate["confidence"] == "medium-high"
    assert estimate["stage1_gain_percent"] > 8
    assert estimate["estimated_hp_after_stage1"] > 108
    assert estimate["derived_inputs"]["changed_categories"] == [
        "air_fuel",
        "boost",
        "fuel",
        "torque",
    ]


def test_power_estimate_caps_limiter_only_changes():
    estimate = estimate_power_from_calibration(
        [_map("limiter", 100, 1000)],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=100,
    )

    assert estimate["available"] is True
    assert estimate["stage1_gain_percent"] <= 2.0
    assert estimate["potential_class"] == "Low"
