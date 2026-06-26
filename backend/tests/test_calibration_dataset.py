from app.services.calibration_dataset import build_ml_dataset


def _map(category: str, changed_percent: float = 0.0, changed_cells: int = 0):
    return {
        "name": f"{category} map",
        "address": 16,
        "address_hex": "0x10",
        "rows": 2,
        "columns": 2,
        "data_type": "u16",
        "byte_order": "big",
        "factor": 0.1,
        "offset": 0,
        "category": category,
        "summary": {"min": 10, "max": 40, "mean": 25},
        "modified_summary": {"min": 10, "max": 48, "mean": 28},
        "diff": {
            "changed_cells": changed_cells,
            "total_cells": 4,
            "changed_percent": changed_percent,
            "mean_delta": 3,
            "max_abs_delta": 8,
            "direction": "increase" if changed_cells else "unchanged",
        },
        "axes": [
            {"label": "rpm_axis", "unit": "RPM", "min": 1500, "max": 7000},
            {"label": "load_axis", "unit": "hPaMAP", "min": 80, "max": 250},
        ],
        "affected_zone": [
            {"label": "RPM", "min": 3500, "max": 7000},
            {"label": "hPaMAP", "min": 120, "max": 250},
        ],
    }


def test_build_ml_dataset_creates_map_level_features_and_seed_labels():
    analysis = {
        "summary": {
            "original_file": "original.bin",
            "modified_file": "stage1.bin",
        },
        "maps": [
            _map("torque", changed_percent=50, changed_cells=2),
            _map("fuel", changed_percent=0, changed_cells=0),
        ],
        "recommendations": [
            {
                "category": "torque",
                "title": "Torque request / torque limiters",
                "priority": "high",
                "risk": "medium-high",
                "missing_dependencies": ["boost"],
            }
        ],
    }

    dataset = build_ml_dataset(
        analysis,
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=100,
    )

    assert dataset["summary"]["samples"] == 2
    assert dataset["summary"]["mode"] == "comparison"
    torque_row = dataset["rows"][0]
    fuel_row = dataset["rows"][1]
    assert torque_row["sample_id"] == "original.bin::0x10"
    assert torque_row["seed_label"] == "torque_review"
    assert torque_row["recommendation_priority_score"] == 0.85
    assert torque_row["recommendation_risk_score"] == 0.7
    assert torque_row["missing_dependencies"] == ["boost"]
    assert torque_row["has_rpm_axis"] is True
    assert torque_row["affected_rpm_min"] == 3500
    assert fuel_row["seed_label"] == "unchanged_support_map"


def test_build_ml_dataset_marks_original_only_rows_as_planning_candidates():
    analysis = {
        "summary": {
            "original_file": "original.bin",
            "modified_file": None,
        },
        "maps": [_map("fuel")],
        "recommendations": [],
    }

    dataset = build_ml_dataset(analysis, fuel_type="diesel", is_turbo=True)

    assert dataset["summary"]["mode"] == "original_only"
    assert dataset["rows"][0]["source_mode"] == "original_only"
    assert dataset["rows"][0]["seed_label"] == "candidate_for_review"
    assert dataset["rows"][0]["include_for_training"] is False
