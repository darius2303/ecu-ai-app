from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


POWER_CATEGORIES = {
    "torque",
    "fuel",
    "boost",
    "air_fuel",
    "timing",
    "rail_pressure",
    "limiter",
}


LABEL_OPTIONS = [
    "bad_stage1_change",
    "good_stage1_change",
    "safe_supporting_change",
    "risky_limiter_change",
    "torque_increase",
    "fuel_support_needed",
    "boost_support_needed",
    "afr_lambda_risk",
    "timing_risk",
    "not_power_related",
    "unknown",
]


RISK_LABEL_OPTIONS = [
    "low",
    "medium",
    "medium-high",
    "high",
    "unknown",
]


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return None


def _summary_value(summary: dict[str, Any] | None, key: str) -> float | None:
    if not isinstance(summary, dict):
        return None
    return _number(summary.get(key))


def _axis_features(axes: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "axis_count": 0,
        "axis_1_label": None,
        "axis_1_min": None,
        "axis_1_max": None,
        "axis_2_label": None,
        "axis_2_min": None,
        "axis_2_max": None,
        "has_rpm_axis": False,
        "has_load_axis": False,
    }
    if not isinstance(axes, list):
        return result

    usable_axes = [axis for axis in axes if isinstance(axis, dict)]
    result["axis_count"] = len(usable_axes)
    for index, axis in enumerate(usable_axes[:2], start=1):
        label = str(axis.get("unit") or axis.get("label") or "")
        label_lower = label.lower()
        result[f"axis_{index}_label"] = label or None
        result[f"axis_{index}_min"] = _number(axis.get("min"))
        result[f"axis_{index}_max"] = _number(axis.get("max"))
        if "rpm" in label_lower:
            result["has_rpm_axis"] = True
        if any(token in label_lower for token in ("load", "hpa", "map", "%", "acc", "iq")):
            result["has_load_axis"] = True
    return result


def _zone_features(zones: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "affected_zone_count": 0,
        "affected_rpm_min": None,
        "affected_rpm_max": None,
        "affected_load_min": None,
        "affected_load_max": None,
    }
    if not isinstance(zones, list):
        return result

    usable_zones = [zone for zone in zones if isinstance(zone, dict)]
    result["affected_zone_count"] = len(usable_zones)
    for zone in usable_zones:
        label = str(zone.get("label") or "").lower()
        minimum = _number(zone.get("min"))
        maximum = _number(zone.get("max"))
        if "rpm" in label:
            result["affected_rpm_min"] = minimum
            result["affected_rpm_max"] = maximum
        elif any(token in label for token in ("load", "hpa", "map", "%", "acc", "iq")):
            result["affected_load_min"] = minimum
            result["affected_load_max"] = maximum
    return result


def _supporting_categories(map_results: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("category") or "unknown")
        for item in map_results
        if isinstance(item, dict)
    }


def _recommendation_index(recommendations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "unknown")
        grouped.setdefault(category, []).append(item)
    return grouped


def _risk_score(value: str | None) -> float:
    risk = (value or "").lower()
    return {
        "low": 0.2,
        "medium": 0.45,
        "medium-high": 0.7,
        "high": 0.9,
        "unknown": 0.5,
    }.get(risk, 0.5)


def _priority_score(value: str | None) -> float:
    priority = (value or "").lower()
    return {
        "low": 0.2,
        "medium": 0.5,
        "high": 0.85,
    }.get(priority, 0.4)


def _seed_label(
    category: str,
    changed_percent: float,
    has_modified: bool,
    recommendations: list[dict[str, Any]],
) -> str:
    if not has_modified:
        return "candidate_for_review" if category in POWER_CATEGORIES else "unknown"
    if changed_percent <= 0:
        return "unchanged_support_map" if category in POWER_CATEGORIES else "not_power_related"
    if recommendations:
        return f"{category}_review"
    if category == "limiter":
        return "risky_limiter_change"
    if category in POWER_CATEGORIES:
        return f"{category}_changed"
    return "unknown_changed"


def _ml_confidence_seed(
    category: str,
    changed_percent: float,
    axis_count: int,
    recommendations: list[dict[str, Any]],
    has_modified: bool,
) -> float:
    score = 0.2
    if category in POWER_CATEGORIES:
        score += 0.2
    if axis_count > 0:
        score += 0.15
    if has_modified and changed_percent > 0:
        score += 0.25
    if recommendations:
        score += 0.15
    return round(min(score, 0.95), 3)


def build_ml_dataset(
    analysis: dict[str, Any],
    *,
    engine_displacement: float | None = None,
    fuel_type: str | None = None,
    is_turbo: bool | None = None,
    stock_hp: float | None = None,
) -> dict[str, Any]:
    """Create feature rows suitable for future ML training.

    The labels are intentionally weak seed labels. They are useful for sorting
    and bootstrapping, but should be reviewed by a tuner before model training.
    """

    map_results = [
        item for item in (analysis.get("maps") or [])
        if isinstance(item, dict)
    ]
    recommendations = [
        item for item in (analysis.get("recommendations") or [])
        if isinstance(item, dict)
    ]
    summary = analysis.get("summary") or {}
    has_modified = bool(summary.get("modified_file"))
    available_categories = _supporting_categories(map_results)
    recommendations_by_category = _recommendation_index(recommendations)

    rows: list[dict[str, Any]] = []
    for item in map_results:
        category = str(item.get("category") or "unknown")
        diff = item.get("diff") or {}
        map_recommendations = recommendations_by_category.get(category, [])
        changed_percent = float(diff.get("changed_percent") or 0.0)
        changed_cells = int(diff.get("changed_cells") or 0)
        total_cells = int(diff.get("total_cells") or (int(item.get("rows") or 0) * int(item.get("columns") or 0)))
        original_summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        modified_summary = item.get("modified_summary") if isinstance(item.get("modified_summary"), dict) else {}
        axes = _axis_features(item.get("axes") or [])
        zones = _zone_features(item.get("affected_zone") or [])
        dependencies = {
            dependency
            for recommendation in map_recommendations
            for dependency in (recommendation.get("missing_dependencies") or [])
            if isinstance(dependency, str)
        }
        row = {
            "sample_id": f"{summary.get('original_file') or 'calibration'}::{item.get('address_hex') or item.get('name')}",
            "source_original_file": summary.get("original_file"),
            "source_modified_file": summary.get("modified_file"),
            "source_mode": "comparison" if has_modified else "original_only",
            "fuel_type": fuel_type,
            "is_turbo": is_turbo,
            "engine_displacement_l": _number(engine_displacement),
            "stock_hp": _number(stock_hp),
            "map_name": item.get("name"),
            "map_category": category,
            "is_power_related": category in POWER_CATEGORIES,
            "address": item.get("address"),
            "address_hex": item.get("address_hex"),
            "rows": item.get("rows"),
            "columns": item.get("columns"),
            "cell_count": total_cells,
            "data_type": item.get("data_type"),
            "byte_order": item.get("byte_order"),
            "value_unit": item.get("value_unit"),
            "scale_factor": _number(item.get("factor")),
            "scale_offset": _number(item.get("offset")),
            "original_min": _summary_value(original_summary, "min"),
            "original_max": _summary_value(original_summary, "max"),
            "original_mean": _summary_value(original_summary, "mean"),
            "modified_min": _summary_value(modified_summary, "min"),
            "modified_max": _summary_value(modified_summary, "max"),
            "modified_mean": _summary_value(modified_summary, "mean"),
            "changed_cells": changed_cells,
            "changed_percent": round(changed_percent, 4),
            "mean_delta": _number(diff.get("mean_delta")) or 0.0,
            "max_abs_delta": _number(diff.get("max_abs_delta")) or 0.0,
            "direction": diff.get("direction") or "unchanged",
            "has_recommendation": bool(map_recommendations),
            "recommendation_titles": [
                recommendation.get("title")
                for recommendation in map_recommendations[:3]
                if recommendation.get("title")
            ],
            "recommendation_priority": map_recommendations[0].get("priority") if map_recommendations else None,
            "recommendation_risk": map_recommendations[0].get("risk") if map_recommendations else None,
            "recommendation_priority_score": _priority_score(
                map_recommendations[0].get("priority") if map_recommendations else None
            ),
            "recommendation_risk_score": _risk_score(
                map_recommendations[0].get("risk") if map_recommendations else None
            ),
            "has_supporting_torque": "torque" in available_categories,
            "has_supporting_fuel": "fuel" in available_categories,
            "has_supporting_boost": "boost" in available_categories,
            "has_supporting_air_fuel": "air_fuel" in available_categories,
            "has_supporting_timing": "timing" in available_categories,
            "missing_dependencies": sorted(dependencies),
            "manual_label": None,
            "manual_risk_label": None,
            "review_status": "unreviewed",
            "review_notes": "",
            "include_for_training": False,
        }
        row.update(axes)
        row.update(zones)
        row["seed_label"] = _seed_label(
            category,
            changed_percent,
            has_modified,
            map_recommendations,
        )
        row["ml_confidence_seed"] = _ml_confidence_seed(
            category,
            changed_percent,
            int(row.get("axis_count") or 0),
            map_recommendations,
            has_modified,
        )
        rows.append(row)

    feature_columns = sorted({key for row in rows for key in row.keys()})
    category_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}
    for row in rows:
        category = str(row.get("map_category") or "unknown")
        label = str(row.get("seed_label") or "unknown")
        category_counts[category] = category_counts.get(category, 0) + 1
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "version": "calibration-features-v1",
        "status": "feature_extraction_only",
        "training_ready": False,
        "labeling_required": True,
        "notes": [
            "Seed labels are generated from rules and should be reviewed before model training.",
            "Rows are map-level samples extracted from real calibration files and map definitions.",
        ],
        "label_schema": {
            "label_options": LABEL_OPTIONS,
            "risk_label_options": RISK_LABEL_OPTIONS,
            "required_review_fields": [
                "manual_label",
                "manual_risk_label",
                "review_status",
                "include_for_training",
            ],
            "review_status_options": [
                "unreviewed",
                "reviewed",
                "rejected",
            ],
        },
        "summary": {
            "samples": len(rows),
            "feature_count": len(feature_columns),
            "mode": "comparison" if has_modified else "original_only",
            "categories": category_counts,
            "seed_labels": label_counts,
        },
        "feature_columns": feature_columns,
        "rows": rows,
    }


def write_ml_dataset_json(dataset: dict[str, Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    return str(path)


def write_labeling_template_csv(dataset: dict[str, Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [row for row in dataset.get("rows", []) if isinstance(row, dict)]
    headers = [
        "sample_id",
        "map_name",
        "map_category",
        "source_mode",
        "changed_percent",
        "max_abs_delta",
        "direction",
        "affected_rpm_min",
        "affected_rpm_max",
        "affected_load_min",
        "affected_load_max",
        "seed_label",
        "ml_confidence_seed",
        "recommendation_priority",
        "recommendation_risk",
        "manual_label",
        "manual_risk_label",
        "review_status",
        "include_for_training",
        "review_notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(path)
