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
        "torque": "Limiter/cerere de cuplu modificata; verifica coerenta cu smoke, boost si protectiile de transmisie.",
        "boost": "Harta de boost modificata; verifica limiterele de presiune si controlul turbo.",
        "air_fuel": "Harta aer/combustibil modificata; verifica fum/lambda si temperaturile de evacuare.",
        "fuel": "Harta de combustibil sau durata injectiei modificata; verifica rail pressure si SOI.",
        "timing": "Timing/SOI modificat; verifica zgomot, EGT si presiune cilindru.",
        "rail_pressure": "Rail pressure modificat; verifica limitele pompei si injectoarelor.",
        "limiter": "Limiter modificat; verifica daca schimbarea pastreaza protectiile mecanice si termice.",
        "unknown": "Harta modificata, dar categoria nu a fost identificata din nume.",
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


def _build_calibration_report(
    summary: dict[str, Any],
    binary_diff: dict[str, Any] | None,
    changed_maps: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    changed_sorted = sorted(
        changed_maps,
        key=lambda item: (item.get("diff") or {}).get("changed_percent", 0),
        reverse=True,
    )
    top_changes: list[dict[str, Any]] = []
    for item in changed_sorted[:8]:
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
        "Compara logurile reale cu zonele RPM/load modificate.",
        "Verifica EGT, AFR/lambda si knock/noise acolo unde hartile de fuel/timing/air sunt afectate.",
        "Pastreaza limiterele mecanice si termice daca nu exista validare hardware.",
    ]
    for recommendation in recommendations[:4]:
        for check in recommendation.get("checks") or []:
            if check not in validation_checks:
                validation_checks.append(str(check))

    headline = "Analiza calibrarii este gata."
    if binary_diff:
        headline = (
            f"{binary_diff.get('changed_bytes', 0)} bytes schimbati "
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
        "top_changes": top_changes,
        "key_findings": findings[:6],
        "recommended_actions": recommendations[:6],
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
            warnings.append(f"Harta {definition.name} a fost ignorata: {exc}")
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
                warnings.append(f"Harta {definition.name} nu a putut fi comparata: {exc}")

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
            "Nu ai incarcat definitii de harti; analiza este limitata la diferente binare."
        )
    if modified is None:
        warnings.append(
            "Nu ai incarcat fisier modificat; pot extrage harti, dar nu pot calcula diferente."
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
    report = _build_calibration_report(
        summary=summary,
        binary_diff=binary_diff,
        changed_maps=changed_maps,
        findings=sorted_findings,
        recommendations=recommendations,
        warnings=warnings,
    )

    return {
        "summary": summary,
        "binary_diff": binary_diff,
        "maps": map_results,
        "recommendations": recommendations,
        "power_estimate": power_estimate,
        "findings": sorted_findings,
        "report": report,
        "warnings": warnings,
    }
