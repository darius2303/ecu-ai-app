from __future__ import annotations

from typing import Any

from app.services.calibration_maps import (
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
        except ValueError as exc:
            warnings.append(f"Harta {definition.name} a fost ignorata: {exc}")
            continue

        if modified is not None:
            try:
                modified_values = extract_map_values(modified.content, definition)
                result["modified_summary"] = summarize_values(modified_values)
                result["modified_preview"] = preview_values(modified_values)
                result["diff"] = compare_values(original_values, modified_values)
                result["delta_preview"] = delta_preview(original_values, modified_values)
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

    return {
        "summary": {
            "original_file": original.file_name,
            "modified_file": modified.file_name if modified else None,
            "original_format": original.file_format,
            "modified_format": modified.file_format if modified else None,
            "original_size": len(original.content),
            "modified_size": len(modified.content) if modified else None,
            "definitions_count": len(definitions),
            "maps_extracted": len(map_results),
            "maps_changed": len(changed_maps),
        },
        "binary_diff": binary_diff,
        "maps": map_results,
        "recommendations": recommendations,
        "power_estimate": power_estimate,
        "findings": sorted(
            findings,
            key=lambda item: {"high": 0, "medium": 1, "low": 2}[item["severity"]],
        ),
        "warnings": warnings,
    }
