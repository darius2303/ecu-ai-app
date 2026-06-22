from __future__ import annotations

from typing import Any

from app.services.calibration_maps import (
    axes_payload,
    compare_values,
    delta_preview,
    extract_map_values,
    map_payload,
    preview_values,
    summarize_values,
)
from app.services.file_formats import EcuBinary
from app.services.map_definitions import MapDefinition
from app.services.calibration_power import estimate_power_from_calibration
from app.services.calibration_recommender import generate_power_recommendations
from app.services.calibration_dataset import build_ml_dataset
from app.services.calibration_ml import (
    enrich_maps_with_ml_predictions,
    enrich_recommendations_with_ml_evidence,
)


def _binary_diff(original: bytes, modified: bytes | None) -> dict[str, Any] | None:
    if modified is None:
        return None

    comparable = min(len(original), len(modified))
    changed_offsets = [
        index for index in range(comparable) if original[index] != modified[index]
    ]
    size_delta = len(modified) - len(original)
    changed_bytes = len(changed_offsets) + abs(size_delta)
    total = max(len(original), len(modified))

    regions: list[dict[str, Any]] = []
    if changed_offsets:
        start = changed_offsets[0]
        previous = start
        for offset in changed_offsets[1:]:
            if offset == previous + 1:
                previous = offset
                continue
            regions.append(
                {
                    "start": start,
                    "end": previous,
                    "start_hex": hex(start),
                    "end_hex": hex(previous),
                    "length": previous - start + 1,
                }
            )
            start = previous = offset

        regions.append(
            {
                "start": start,
                "end": previous,
                "start_hex": hex(start),
                "end_hex": hex(previous),
                "length": previous - start + 1,
            }
        )

    regions = sorted(regions, key=lambda item: item["length"], reverse=True)[:12]

    return {
        "original_size": len(original),
        "modified_size": len(modified),
        "size_delta": size_delta,
        "changed_bytes": changed_bytes,
        "changed_percent": round((changed_bytes / total) * 100.0, 4) if total else 0.0,
        "largest_regions": regions,
    }


def _finding_for_map(map_result: dict[str, Any]) -> dict[str, Any] | None:
    diff = map_result.get("diff")
    if not diff or diff["changed_cells"] == 0:
        return None

    category = map_result.get("category", "unknown")
    changed_percent = diff["changed_percent"]
    max_delta = diff["max_abs_delta"]

    severity = "low"
    if changed_percent >= 35 or max_delta >= 20:
        severity = "high"
    elif changed_percent >= 10 or max_delta >= 5:
        severity = "medium"

    messages = {
        "torque": "Torque request/limiter changed; check coherence with air/fuel strategy and drivetrain protections.",
        "boost": "Boost map changed; check pressure limiters and turbo control.",
        "air_fuel": "Air/fuel map changed; check lambda, smoke and exhaust temperatures.",
        "fuel": "Fuel quantity or injection duration changed; check rail pressure and SOI.",
        "timing": "Timing/SOI changed; check noise, EGT and cylinder pressure.",
        "rail_pressure": "Rail pressure changed; check pump and injector limits.",
        "limiter": "Limiter changed; verify that mechanical and thermal protections remain valid.",
        "unknown": "Map changed, but the category could not be identified from its name.",
    }

    return {
        "severity": severity,
        "map_name": map_result["name"],
        "category": category,
        "message": messages.get(category, messages["unknown"]),
        "changed_percent": changed_percent,
        "max_abs_delta": max_delta,
    }


def _axis_range(axis: dict[str, Any], start_index: int, end_index: int) -> dict[str, Any] | None:
    values = axis.get("values")
    if not isinstance(values, list) or not values:
        return None

    start = min(max(start_index, 0), len(values) - 1)
    end = min(max(end_index, 0), len(values) - 1)
    if end < start:
        start, end = end, start

    return {
        "label": axis.get("unit") or axis.get("label") or "axis",
        "min": values[start],
        "max": values[end],
        "start_index": start,
        "end_index": end,
    }


def _affected_zone(map_result: dict[str, Any]) -> list[dict[str, Any]]:
    diff = map_result.get("diff") or {}
    bounds = diff.get("changed_bounds") or {}
    axes = map_result.get("axes") or []
    if not isinstance(bounds, dict) or not isinstance(axes, list):
        return []

    rows = int(map_result.get("rows") or 0)
    columns = int(map_result.get("columns") or 0)
    row_min = int(bounds.get("row_min", 0))
    row_max = int(bounds.get("row_max", 0))
    column_min = int(bounds.get("column_min", 0))
    column_max = int(bounds.get("column_max", 0))

    zones: list[dict[str, Any]] = []
    for axis in axes:
        if not isinstance(axis, dict):
            continue
        count = int(axis.get("count") or 0)
        unit = str(axis.get("unit") or axis.get("label") or "").lower()
        if "rpm" in unit or count == columns:
            zone = _axis_range(axis, column_min, column_max)
        elif count == rows:
            zone = _axis_range(axis, row_min, row_max)
        elif count == columns + 1:
            zone = _axis_range(axis, column_min, column_max + 1)
        elif count == rows + 1:
            zone = _axis_range(axis, row_min, row_max + 1)
        else:
            zone = None
        if zone is not None:
            zones.append(zone)
    return zones


def _zone_text(zones: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for zone in zones[:3]:
        label = zone.get("label") or "axis"
        minimum = zone.get("min")
        maximum = zone.get("max")
        if minimum is None or maximum is None:
            continue
        parts.append(f"{label} {minimum}-{maximum}")
    return ", ".join(parts)


def _unique_preserve_order(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if len(unique) >= limit:
            break
    return unique


def _build_tuner_summary(
    recommendations: list[dict[str, Any]],
    changed_maps: list[dict[str, Any]],
    binary_diff: dict[str, Any] | None,
) -> list[str]:
    summary: list[str] = []
    changed_categories = _unique_preserve_order(
        [
            str(item.get("category") or "unknown")
            for item in sorted(
                changed_maps,
                key=lambda item: (item.get("diff") or {}).get("changed_percent", 0),
                reverse=True,
            )
        ],
        limit=4,
    )

    if changed_categories:
        summary.append(
            "Changes are concentrated in: " + ", ".join(changed_categories) + "."
        )
    elif binary_diff:
        summary.append(
            "Binary differences exist, but they could not be clearly linked to defined maps."
        )
    else:
        summary.append(
            "Analysis is running in original-only mode; recommendations are an investigation plan."
        )

    high_priority = [
        item for item in recommendations
        if str(item.get("priority") or "").lower() == "high"
    ]
    if high_priority:
        summary.append(
            "High priority: "
            + ", ".join(
                _unique_preserve_order(
                    [str(item.get("title") or "Recommendation") for item in high_priority],
                    limit=3,
                )
            )
            + "."
        )

    supporting = [
        item for item in recommendations
        if item.get("mode") == "review_supporting_map"
    ]
    if supporting:
        summary.append(
            "Supporting maps to review: "
            + ", ".join(
                _unique_preserve_order(
                    [str(item.get("title") or "Supporting map") for item in supporting],
                    limit=3,
                )
            )
            + "."
        )

    limiter_changes = [
        item for item in changed_maps
        if str(item.get("category") or "") == "limiter"
    ]
    if limiter_changes:
        summary.append(
            "Limiters are modified; verify that the changes are intentional and keep the required protections."
        )

    return summary[:4]


def _build_analysis_verdict(
    recommendations: list[dict[str, Any]],
    changed_maps: list[dict[str, Any]],
    binary_diff: dict[str, Any] | None,
    ml_summary: dict[str, Any],
    has_modified: bool,
    definitions_count: int,
) -> dict[str, Any]:
    high_risk_recommendations = [
        item for item in recommendations
        if str(item.get("risk") or "").lower() in {"high", "medium-high"}
    ]
    high_priority_recommendations = [
        item for item in recommendations
        if str(item.get("priority") or "").lower() == "high"
    ]
    supporting_reviews = [
        item for item in recommendations
        if item.get("mode") == "review_supporting_map"
    ]
    bad_stage1_count = int(ml_summary.get("bad_stage1_count") or 0)
    high_risk_count = int(ml_summary.get("high_risk_count") or 0)

    if definitions_count == 0:
        return {
            "status": "missing_context",
            "title": "Map definitions required",
            "severity": "warning",
            "message": "The binary was loaded, but the app cannot safely link changes to calibration maps without a map pack.",
            "next_step": "Load a WinOLS/map-pack export before using the recommendations for tuning decisions.",
        }

    if not has_modified:
        return {
            "status": "planning_mode",
            "title": "Planning review",
            "severity": "info",
            "message": "Only the original file was loaded, so recommendations are planning hints rather than validation of a finished tune.",
            "next_step": "Add a tuned/current file when you want to compare real changes.",
        }

    if bad_stage1_count > 0 or high_risk_count > 0:
        return {
            "status": "high_risk_pattern",
            "title": "High-risk tune pattern",
            "severity": "danger",
            "message": (
                "The analysis found changes that should be validated carefully before any further calibration work."
            ),
            "next_step": "Review the focused maps, compare real logs, and confirm fuel/air/limiter coherence.",
        }

    if high_risk_recommendations or supporting_reviews:
        titles = _unique_preserve_order(
            [str(item.get("title") or "Recommendation") for item in high_priority_recommendations or high_risk_recommendations],
            limit=2,
        )
        suffix = f" Main areas: {', '.join(titles)}." if titles else ""
        return {
            "status": "needs_validation",
            "title": "Needs validation",
            "severity": "warning",
            "message": (
                "The tune has meaningful changes and supporting maps should be checked before treating it as coherent."
                + suffix
            ),
            "next_step": "Use Focus maps on the high-priority recommendations and verify the affected RPM/load zones in logs.",
        }

    if changed_maps or binary_diff:
        return {
            "status": "looks_coherent",
            "title": "Looks coherent",
            "severity": "success",
            "message": "No major high-risk pattern was detected in the extracted map changes.",
            "next_step": "Still validate AFR/lambda, EGT, knock/noise and limiter behavior on real logs.",
        }

    return {
        "status": "no_clear_changes",
        "title": "No clear mapped changes",
        "severity": "info",
        "message": "The app did not find meaningful changes in the extracted map definitions.",
        "next_step": "Check that the correct original, tuned file and map pack were loaded.",
    }


def _build_calibration_report(
    summary: dict[str, Any],
    binary_diff: dict[str, Any] | None,
    changed_maps: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    warnings: list[str],
    verdict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    changed_sorted = sorted(
        changed_maps,
        key=lambda item: (item.get("diff") or {}).get("changed_percent", 0),
        reverse=True,
    )
    top_changes: list[dict[str, Any]] = []
    seen_changes: set[tuple[str, str]] = set()
    for item in changed_sorted:
        if len(top_changes) >= 8:
            break
        change_key = (
            str(item.get("name") or ""),
            str(item.get("address_hex") or ""),
        )
        if change_key in seen_changes:
            continue
        seen_changes.add(change_key)
        diff = item.get("diff") or {}
        zones = item.get("affected_zone") or []
        top_changes.append(
            {
                "name": item.get("name"),
                "category": item.get("category"),
                "address_hex": item.get("address_hex"),
                "changed_percent": diff.get("changed_percent", 0),
                "direction": diff.get("direction", "unchanged"),
                "max_abs_delta": diff.get("max_abs_delta", 0),
                "affected_zone": zones,
                "zone_text": _zone_text(zones),
                "unit": item.get("value_unit"),
            }
        )

    validation_checks = [
        "Compare real logs against the modified RPM/load zones.",
        "Check EGT, AFR/lambda and knock/noise where fuel, timing or air maps are affected.",
        "Keep mechanical and thermal limiters unless hardware validation proves otherwise.",
    ]
    for recommendation in recommendations[:4]:
        for check in recommendation.get("checks") or []:
            if check not in validation_checks:
                validation_checks.append(str(check))

    headline = "Calibration analysis completed."
    if binary_diff:
        headline = (
            f"{binary_diff.get('changed_bytes', 0)} bytes changed "
            f"({binary_diff.get('changed_percent', 0)}%)."
        )

    return {
        "headline": headline,
        "summary": {
            "maps_extracted": summary.get("maps_extracted", 0),
            "maps_changed": summary.get("maps_changed", 0),
            "definitions_count": summary.get("definitions_count", 0),
            "binary_changed_percent": binary_diff.get("changed_percent", 0) if binary_diff else 0,
        },
        "verdict": verdict or {},
        "tuner_summary": _build_tuner_summary(
            recommendations=recommendations,
            changed_maps=changed_maps,
            binary_diff=binary_diff,
        ),
        "top_changes": top_changes,
        "key_findings": findings[:6],
        "recommended_actions": recommendations[:4],
        "validation_checks": validation_checks[:10],
        "warnings": warnings[:6],
    }


def analyze_calibration(
    original: EcuBinary,
    modified: EcuBinary | None,
    definitions: list[MapDefinition],
    warnings: list[str] | None = None,
    engine_displacement: float | None = None,
    fuel_type: str | None = None,
    is_turbo: bool | None = None,
    stock_hp: float | None = None,
) -> dict[str, Any]:
    warnings = list(warnings or [])
    warnings.extend(original.warnings)
    if modified is not None:
        warnings.extend(modified.warnings)

    binary_diff = _binary_diff(original.content, modified.content if modified else None)
    map_results: list[dict[str, Any]] = []

    for definition in definitions[:200]:
        try:
            original_values = extract_map_values(original.content, definition)
            result = map_payload(definition, original_values)
            result["axes"] = axes_payload(original.content, definition)
        except ValueError as exc:
            warnings.append(f"Map {definition.name} was skipped: {exc}")
            continue

        if modified is not None:
            try:
                modified_values = extract_map_values(modified.content, definition)
                result["modified_summary"] = summarize_values(modified_values)
                result["modified_preview"] = preview_values(modified_values)
                result["modified_surface_preview"] = preview_values(modified_values, limit=18)
                result["diff"] = compare_values(original_values, modified_values)
                result["delta_preview"] = delta_preview(original_values, modified_values)
                result["delta_surface_preview"] = delta_preview(original_values, modified_values, limit=18)
                result["affected_zone"] = _affected_zone(result)
            except ValueError as exc:
                warnings.append(f"Map {definition.name} could not be compared: {exc}")

        map_results.append(result)

    changed_maps = [
        item for item in map_results
        if (item.get("diff") or {}).get("changed_cells", 0) > 0
    ]
    findings = [
        finding for finding in (_finding_for_map(item) for item in changed_maps)
        if finding is not None
    ]
    recommendations = generate_power_recommendations(
        map_results=map_results,
        has_modified=modified is not None,
        fuel_type=fuel_type,
        is_turbo=is_turbo,
    )
    power_estimate = estimate_power_from_calibration(
        map_results,
        engine_displacement=engine_displacement,
        fuel_type=fuel_type,
        is_turbo=is_turbo,
        stock_hp=stock_hp,
    )

    if not definitions:
        warnings.append(
            "No map definitions were loaded; analysis is limited to binary differences."
        )
    if modified is None:
        warnings.append(
            "No tuned/current file was loaded; maps can be extracted, but differences cannot be calculated."
        )

    summary = {
        "original_file": original.file_name,
        "modified_file": modified.file_name if modified else None,
        "original_format": original.file_format,
        "modified_format": modified.file_format if modified else None,
        "original_size": len(original.content),
        "modified_size": len(modified.content) if modified else None,
        "definitions_count": len(definitions),
        "maps_extracted": len(map_results),
        "maps_changed": len(changed_maps),
    }
    sorted_findings = sorted(
        findings,
        key=lambda item: {"high": 0, "medium": 1, "low": 2}[item["severity"]],
    )
    result = {
        "summary": summary,
        "binary_diff": binary_diff,
        "maps": map_results,
        "recommendations": recommendations,
        "power_estimate": power_estimate,
        "findings": sorted_findings,
        "warnings": warnings,
    }
    result["ml_dataset"] = build_ml_dataset(
        result,
        engine_displacement=engine_displacement,
        fuel_type=fuel_type,
        is_turbo=is_turbo,
        stock_hp=stock_hp,
    )
    ml_summary = enrich_maps_with_ml_predictions(
        map_results=map_results,
        ml_dataset=result["ml_dataset"],
    )
    result["ml_summary"] = ml_summary
    enrich_recommendations_with_ml_evidence(recommendations, map_results)
    recommendations.sort(
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            {"high": 0, "medium-high": 1, "medium": 2, "low": 3, "unknown": 4}.get(
                str(item.get("risk") or "unknown"),
                9,
            ),
            {"high": 0, "medium": 1, "low": 2}.get(
                str(item.get("confidence") or "low"),
                9,
            ),
        )
    )
    if ml_summary.get("available") is False:
        warnings.append(
            f"AI-assisted review is unavailable: {ml_summary.get('reason')}"
        )
    elif ml_summary.get("bad_stage1_count", 0) > 0:
        warnings.append(
            "AI-assisted review flagged "
            f"{ml_summary.get('bad_stage1_count')} map(s) as possible risky Stage 1 patterns."
        )
    verdict = _build_analysis_verdict(
        recommendations=recommendations,
        changed_maps=changed_maps,
        binary_diff=binary_diff,
        ml_summary=ml_summary,
        has_modified=modified is not None,
        definitions_count=len(definitions),
    )
    result["analysis_verdict"] = verdict
    result["report"] = _build_calibration_report(
        summary=summary,
        binary_diff=binary_diff,
        changed_maps=changed_maps,
        findings=sorted_findings,
        recommendations=recommendations,
        warnings=warnings,
        verdict=verdict,
    )

    return result
