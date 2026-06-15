from __future__ import annotations

import math
import struct
from dataclasses import asdict
from typing import Any

import numpy as np

from app.services.map_definitions import MapDefinition


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


def extract_map_values(content: bytes, definition: MapDefinition) -> list[list[float]]:
    fmt, size = DATA_TYPES.get(definition.data_type, DATA_TYPES["u16"])
    total = bytes_needed(definition)
    start = definition.address
    end = start + total

    if start < 0 or end > len(content):
        raise ValueError("Adresa hartii depaseste dimensiunea fisierului.")

    endian = "<" if definition.byte_order == "little" else ">"
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
        raise ValueError("Dimensiunile hartilor nu coincid.")

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

    return {
        "changed_cells": changed_cells,
        "total_cells": total_cells,
        "changed_percent": round(changed_percent, 2),
        "mean_delta": round(mean_delta, 4),
        "max_abs_delta": round(max_delta, 4),
        "direction": direction,
    }


def delta_preview(
    original: list[list[float]],
    modified: list[list[float]],
    limit: int = 8,
) -> list[list[float]]:
    left = np.array(original, dtype=float)
    right = np.array(modified, dtype=float)
    if left.shape != right.shape:
        raise ValueError("Dimensiunile hartilor nu coincid.")
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
        }
    )
    return payload


def finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None
