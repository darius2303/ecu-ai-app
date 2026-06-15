from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from app.services.map_utils import decode_map_file_content


@dataclass
class MapDefinition:
    name: str
    address: int
    rows: int
    columns: int
    data_type: str = "u16"
    byte_order: str = "big"
    factor: float = 1.0
    offset: float = 0.0
    category: str = "unknown"


def _first(row: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value not in (None, ""):
            return value
    return default


def _parse_int(value: Any, field_name: str) -> int:
    if value is None or value == "":
        raise ValueError(f"Lipseste campul {field_name}.")
    text = str(value).strip()
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(float(text))
    except ValueError as exc:
        raise ValueError(f"Campul {field_name} nu este numeric: {value}") from exc


def _parse_float(value: Any, default: float) -> float:
    if value in (None, ""):
        return default
    return float(str(value).strip().replace(",", "."))


def _category_from_name(name: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ("torque", "nm", "driver wish", "pedal")):
        return "torque"
    if any(token in lower for token in ("boost", "pressure", "turbo")):
        return "boost"
    if any(token in lower for token in ("smoke", "lambda", "afr", "air")):
        return "air_fuel"
    if any(token in lower for token in ("duration", "injection", "iq", "fuel")):
        return "fuel"
    if any(token in lower for token in ("soi", "start", "timing", "angle")):
        return "timing"
    if any(token in lower for token in ("rail", "cr pressure")):
        return "rail_pressure"
    return "unknown"


def _definition_from_row(row: dict[str, Any], index: int) -> MapDefinition:
    name = str(_first(row, ["name", "map", "map_name", "id", "title"], f"Map {index}")).strip()
    address = _parse_int(
        _first(row, ["address", "addr", "start", "offset", "start_address"]),
        "address",
    )
    rows = _parse_int(_first(row, ["rows", "height", "y_size", "ysize"], 1), "rows")
    columns = _parse_int(_first(row, ["columns", "cols", "width", "x_size", "xsize"], 1), "columns")
    data_type = str(_first(row, ["data_type", "datatype", "type", "value_type"], "u16")).strip().lower()
    byte_order = str(_first(row, ["byte_order", "endian", "endianness"], "big")).strip().lower()
    if byte_order in {"motorola", "msb", "be"}:
        byte_order = "big"
    if byte_order in {"intel", "lsb", "le"}:
        byte_order = "little"

    return MapDefinition(
        name=name,
        address=address,
        rows=rows,
        columns=columns,
        data_type=data_type,
        byte_order=byte_order,
        factor=_parse_float(_first(row, ["factor", "scale", "multiplier"], 1.0), 1.0),
        offset=_parse_float(_first(row, ["offset", "add", "bias"], 0.0), 0.0),
        category=str(_first(row, ["category", "map_type"], _category_from_name(name))).strip(),
    )


def parse_map_definitions(file_name: str, raw_bytes: bytes) -> tuple[list[MapDefinition], list[str]]:
    if not raw_bytes:
        return [], ["Fisierul de definitii este gol."]

    text = decode_map_file_content(raw_bytes)
    suffix = Path(file_name).suffix.lower()
    rows: list[dict[str, Any]]

    if suffix == ".json" or text.lstrip().startswith(("{", "[")):
        payload = json.loads(text)
        if isinstance(payload, dict):
            payload = payload.get("maps") or payload.get("definitions") or []
        if not isinstance(payload, list):
            raise ValueError("JSON-ul de definitii trebuie sa contina o lista de harti.")
        rows = [item for item in payload if isinstance(item, dict)]
    else:
        reader = csv.DictReader(StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV-ul de definitii trebuie sa aiba header.")
        rows = list(reader)

    definitions: list[MapDefinition] = []
    warnings: list[str] = []
    for index, row in enumerate(rows, start=1):
        try:
            definition = _definition_from_row(row, index)
        except ValueError as exc:
            warnings.append(f"Definitia {index} a fost ignorata: {exc}")
            continue
        if definition.rows <= 0 or definition.columns <= 0:
            warnings.append(f"Definitia {definition.name} are dimensiuni invalide.")
            continue
        definitions.append(definition)

    if not definitions:
        warnings.append("Nu am gasit definitii de harti utilizabile.")

    return definitions, warnings
