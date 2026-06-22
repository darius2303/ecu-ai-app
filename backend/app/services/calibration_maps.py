from __future__ import annotations

import math
import struct
from dataclasses import asdict
from typing import Any

import numpy as np

from app.services.map_definitions import AxisDefinition, MapDefinition


DATA_TYPES = {
    "u8": ("B", 1),
    "uint8": ("B", 1),
    "s8": ("b", 1),
    "int8": ("b", 1),
    "u16": ("H", 2),
    "uint16": ("H", 2),
    "s16": ("h", 2),
    "int16": ("h", 2),
    "u32": ("I", 4),
    "uint32": ("I", 4),
    "s32": ("i", 4),
    "int32": ("i", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
}


def bytes_needed(definition: MapDefinition) -> int:
    _, size = DATA_TYPES.get(definition.data_type, DATA_TYPES["u16"])
    return definition.rows * definition.columns * size


def _unpack_values(
    content: bytes,
    address: int,
    count: int,
    data_type: str,
    byte_order: str,
    factor: float,
    offset_value: float,
) -> list[float]:
    fmt, size = DATA_TYPES.get(data_type, DATA_TYPES["u16"])
    start = address
    end = start + (count * size)
    if start < 0 or end > len(content):
        raise ValueError("The address exceeds the file size.")

    endian = "<" if byte_order == "little" else ">"
    values: list[float] = []
    raw = content[start:end]
    for raw_offset in range(0, len(raw), size):
        value = struct.unpack(endian + fmt, raw[raw_offset:raw_offset + size])[0]
        scaled = (float(value) * factor) + offset_value
        values.append(round(scaled, 6))
    return values


def _axis_score(values: list[float], unit: str | None) -> float:
    if not values:
        return -1_000_000.0

    unit_lower = (unit or "").lower()
    finite_values = [value for value in values if math.isfinite(value)]
    if len(finite_values) != len(values):
        return -1_000_000.0

    monotonic = sum(
        1 for left, right in zip(values, values[1:]) if right >= left
    )
    monotonic_ratio = monotonic / max(1, len(values) - 1)
    span = max(values) - min(values)
    score = monotonic_ratio * 10.0
    if span > 0:
        score += 2.0

    minimum = min(values)
    maximum = max(values)
    tail_monotonic = len(values) > 3 and all(
        right >= left for left, right in zip(values[1:], values[2:])
    )
    if "rpm" in unit_lower:
        if 0 <= minimum <= 3000 and 1000 <= maximum <= 12000:
            score += 10.0
        if maximum > 20000:
            score -= 15.0
        if tail_monotonic and values[0] > values[1] * 1.5:
            score -= 8.0
    elif "%" in unit_lower:
        if -10 <= minimum <= 150 and 0 <= maximum <= 250:
            score += 8.0
        if maximum > 500:
            score -= 12.0
    elif "hpa" in unit_lower:
        if 0 <= minimum <= 1500 and 50 <= maximum <= 5000:
            score += 8.0
        if maximum > 10000:
            score -= 12.0
        if tail_monotonic and values[1] > 50 and values[0] < values[1] * 0.2:
            score -= 6.0
    elif "km/h" in unit_lower:
        if 0 <= minimum <= 300 and 0 <= maximum <= 500:
            score += 8.0
    elif "deg" in unit_lower or "btdc" in unit_lower:
        if -100 <= minimum <= 100 and -100 <= maximum <= 100:
            score += 8.0
    elif "factor" in unit_lower:
        if -10 <= minimum <= 10 and -10 <= maximum <= 10:
            score += 8.0
    else:
        if abs(maximum) < 100000:
            score += 2.0

    return score


def _extract_axis_values(content: bytes, axis: AxisDefinition) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for address_shift in (0, 2):
        for byte_order in ("little", "big"):
            try:
                values = _unpack_values(
                    content,
                    axis.address + address_shift,
                    axis.count,
                    "u16",
                    byte_order,
                    axis.factor,
                    axis.offset,
                )
            except ValueError:
                continue
            attempts.append(
                {
                    "values": values,
                    "byte_order": byte_order,
                    "address_shift": address_shift,
                    "score": _axis_score(values, axis.unit),
                }
            )

    if not attempts:
        raise ValueError("Axa depaseste dimensiunea fisierului.")

    best = max(attempts, key=lambda item: float(item["score"]))
    if float(best["score"]) < 5.0:
        raise ValueError("Axa nu are valori plauzibile.")
    payload = asdict(axis)
    payload.update(
        {
            "address_hex": hex(axis.address),
            "resolved_address_hex": hex(axis.address + int(best["address_shift"])),
            "resolved_byte_order": best["byte_order"],
            "values": best["values"],
            "min": round(float(min(best["values"])), 4),
            "max": round(float(max(best["values"])), 4),
        }
    )
    return payload


def _resolve_auto_byte_order(content: bytes, definition: MapDefinition) -> str:
    if definition.byte_order != "auto":
        return definition.byte_order

    axis_orders: list[str] = []
    for axis in definition.axes:
        try:
            payload = _extract_axis_values(content, axis)
        except ValueError:
            continue
        byte_order = payload.get("resolved_byte_order")
        if byte_order in {"little", "big"}:
            axis_orders.append(str(byte_order))

    if axis_orders:
        return "big" if axis_orders.count("big") > axis_orders.count("little") else "little"
    return "little"


def extract_map_values(content: bytes, definition: MapDefinition) -> list[list[float]]:
    fmt, size = DATA_TYPES.get(definition.data_type, DATA_TYPES["u16"])
    total = bytes_needed(definition)
    start = definition.address
    end = start + total

    if start < 0 or end > len(content):
        raise ValueError("The map address exceeds the file size.")

    byte_order = _resolve_auto_byte_order(content, definition)
    endian = "<" if byte_order == "little" else ">"
    values: list[float] = []
    raw = content[start:end]
    for offset in range(0, len(raw), size):
        value = struct.unpack(endian + fmt, raw[offset:offset + size])[0]
        scaled = (float(value) * definition.factor) + definition.offset
        values.append(round(scaled, 6))

    return [
        values[row_start:row_start + definition.columns]
        for row_start in range(0, len(values), definition.columns)
    ]


def summarize_values(values: list[list[float]]) -> dict[str, float]:
    array = np.array(values, dtype=float)
    return {
        "min": round(float(np.nanmin(array)), 4),
        "max": round(float(np.nanmax(array)), 4),
        "mean": round(float(np.nanmean(array)), 4),
    }


def preview_values(values: list[list[float]], limit: int = 8) -> list[list[float]]:
    return [row[:limit] for row in values[:limit]]


def compare_values(original: list[list[float]], modified: list[list[float]]) -> dict[str, Any]:
    left = np.array(original, dtype=float)
    right = np.array(modified, dtype=float)
    if left.shape != right.shape:
        raise ValueError("The map dimensions do not match.")

    delta = right - left
    changed = np.abs(delta) > 1e-9
    changed_cells = int(np.count_nonzero(changed))
    total_cells = int(delta.size)
    changed_percent = (changed_cells / total_cells) * 100.0 if total_cells else 0.0
    abs_delta = np.abs(delta)

    mean_delta = float(np.nanmean(delta)) if total_cells else 0.0
    max_delta = float(np.nanmax(abs_delta)) if total_cells else 0.0
    direction = "unchanged"
    if changed_cells:
        direction = "increase" if mean_delta > 0 else "decrease" if mean_delta < 0 else "mixed"
        changed_indexes = np.argwhere(changed)
        row_min = int(np.min(changed_indexes[:, 0]))
        row_max = int(np.max(changed_indexes[:, 0]))
        column_min = int(np.min(changed_indexes[:, 1]))
        column_max = int(np.max(changed_indexes[:, 1]))
        changed_bounds = {
            "row_min": row_min,
            "row_max": row_max,
            "column_min": column_min,
            "column_max": column_max,
        }
    else:
        changed_bounds = None

    return {
        "changed_cells": changed_cells,
        "total_cells": total_cells,
        "changed_percent": round(changed_percent, 2),
        "mean_delta": round(mean_delta, 4),
        "max_abs_delta": round(max_delta, 4),
        "direction": direction,
        "changed_bounds": changed_bounds,
    }


def delta_preview(
    original: list[list[float]],
    modified: list[list[float]],
    limit: int = 8,
) -> list[list[float]]:
    left = np.array(original, dtype=float)
    right = np.array(modified, dtype=float)
    if left.shape != right.shape:
        raise ValueError("The map dimensions do not match.")
    delta = right - left
    preview = delta[:limit, :limit]
    return [[round(float(value), 6) for value in row] for row in preview]


def map_payload(definition: MapDefinition, values: list[list[float]]) -> dict[str, Any]:
    payload = asdict(definition)
    payload.update(
        {
            "address_hex": hex(definition.address),
            "bytes": bytes_needed(definition),
            "summary": summarize_values(values),
            "preview": preview_values(values),
            "surface_preview": preview_values(values, limit=18),
        }
    )
    return payload


def axes_payload(content: bytes, definition: MapDefinition) -> list[dict[str, Any]]:
    axes: list[dict[str, Any]] = []
    for axis in definition.axes:
        try:
            axes.append(_extract_axis_values(content, axis))
        except ValueError:
            continue
    return axes


def finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None
