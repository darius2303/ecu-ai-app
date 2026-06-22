from __future__ import annotations

import re
from typing import Any

import numpy as np


NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")


def _numbers_from_line(line: str) -> list[float]:
    values = []
    for match in NUMBER_RE.findall(line):
        normalized = match.replace(",", ".")
        try:
            values.append(float(normalized))
        except ValueError:
            continue
    return values


def parse_winols_map_text(raw_text: str, map_type: str = "soi") -> dict[str, Any]:
    """
    Parse a table copied from WinOLS/OLS-like text: optional X-axis line,
    followed by rows with RPM in the first column and map values after it.
    """
    numeric_lines = [
        _numbers_from_line(line)
        for line in raw_text.replace("\t", " ").splitlines()
    ]
    numeric_lines = [line for line in numeric_lines if len(line) >= 2]

    if not numeric_lines:
        raise ValueError("No numeric values were found in the copied map.")

    best_start = 0
    best_end = 0
    best_width = 0
    current_start = 0
    current_width = len(numeric_lines[0])

    for index, line in enumerate(numeric_lines + [[]]):
        width = len(line)
        contiguous = width == current_width and width >= 4
        if contiguous:
            continue

        current_len = index - current_start
        if current_len >= 2 and current_width > best_width:
            best_start = current_start
            best_end = index
            best_width = current_width

        current_start = index
        current_width = width

    data_lines = numeric_lines[best_start:best_end]
    if len(data_lines) < 2 or best_width < 4:
        data_lines = [line for line in numeric_lines if len(line) >= 4]

    if len(data_lines) < 2:
        raise ValueError("The map must contain at least two data rows.")

    value_count = min(len(line) - 1 for line in data_lines)
    if value_count < 2:
        raise ValueError("The map must contain at least two value columns.")

    rpm_axis = [float(line[0]) for line in data_lines]
    values = [line[1:value_count + 1] for line in data_lines]

    load_axis: list[float] | None = None
    if best_start > 0:
        previous_line = numeric_lines[best_start - 1]
        if len(previous_line) >= value_count:
            load_axis = [float(x) for x in previous_line[-value_count:]]

    if load_axis is None:
        load_axis = [float(index) for index in range(value_count)]

    return {
        "map_type": map_type,
        "rpm_axis": rpm_axis,
        "load_axis": load_axis,
        "values": values,
        "value_unit": "deg" if map_type == "soi" else None,
    }


def decode_map_file_content(raw_bytes: bytes) -> str:
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    if raw_bytes.count(b"\x00") > max(8, len(raw_bytes) // 20):
        raise ValueError(
            "The file appears to be binary. Export the map as TXT/CSV from WinOLS and try again."
        )

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            decoded = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        if decoded.strip():
            return decoded

    raise ValueError("The file could not be decoded as text.")


def ensure_calibration_map(data: Any) -> dict[str, Any] | None:
    if getattr(data, "calibration_map", None) is not None:
        return data.calibration_map.model_dump()

    raw_text = (getattr(data, "calibration_map_text", None) or "").strip()
    if not raw_text:
        return None

    return parse_winols_map_text(
        raw_text,
        map_type=getattr(data, "calibration_map_type", "soi") or "soi",
    )


def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.array(values, dtype=float), q))


def derive_features_from_map(
    calibration_map: dict[str, Any],
    fuel_type: str,
    is_turbo: bool,
) -> dict[str, float | int | str]:
    rpm_axis = [float(x) for x in calibration_map["rpm_axis"]]
    load_axis = [float(x) for x in calibration_map["load_axis"]]
    values = np.array(calibration_map["values"], dtype=float)
    map_type = calibration_map.get("map_type") or "soi"

    if values.ndim != 2:
        raise ValueError("Map values must be a 2D matrix.")
    if values.shape[0] != len(rpm_axis):
        raise ValueError("The row count does not match the RPM axis.")
    if values.shape[1] != len(load_axis):
        raise ValueError("The column count does not match the load/IQ axis.")

    high_load_start = max(0, int(values.shape[1] * 0.65))
    high_rpm_start = max(0, int(values.shape[0] * 0.45))
    high_load_region = values[high_rpm_start:, high_load_start:]

    representative_rpm = _percentile(rpm_axis, 70)
    representative_load = _percentile(load_axis, 75)

    if map_type == "boost":
        boost_pressure = max(0.8, min(2.4, float(np.nanmean(high_load_region))))
        injection_quantity = max(8.0, min(95.0, representative_load))
    elif map_type == "fuel":
        injection_quantity = max(8.0, min(95.0, float(np.nanmean(high_load_region))))
        boost_pressure = 1.55 if is_turbo else 1.0
    else:
        injection_quantity = max(8.0, min(95.0, representative_load))
        load_span = max(load_axis) - min(load_axis) if load_axis else 0.0
        load_ratio = 0.0 if load_span <= 0 else (representative_load - min(load_axis)) / load_span
        boost_pressure = (1.05 + load_ratio * 0.85) if is_turbo else 1.0

    if fuel_type == "diesel":
        afr = 14.7
    else:
        afr = 13.2 if is_turbo else 14.0

    return {
        "rpm": round(float(representative_rpm), 2),
        "boost_pressure": round(float(boost_pressure), 2),
        "injection_quantity": round(float(injection_quantity), 2),
        "afr": round(float(afr), 2),
        "map_type": str(map_type),
        "rows": int(values.shape[0]),
        "columns": int(values.shape[1]),
        "min_value": round(float(np.nanmin(values)), 2),
        "max_value": round(float(np.nanmax(values)), 2),
        "high_load_mean": round(float(np.nanmean(high_load_region)), 2),
    }
