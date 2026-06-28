from __future__ import annotations

import csv
import io
import json
import math
import re
import struct
import zipfile
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from app.services.map_utils import decode_map_file_content


@dataclass
class AxisDefinition:
    """Descrie o axa a hartii, de exemplu RPM sau sarcina motor."""
    label: str
    address: int
    count: int
    factor: float = 1.0
    offset: float = 0.0
    unit: str | None = None
    byte_order: str = "auto"


@dataclass
class MapDefinition:
    """Descrie pozitia si conversia unei harti ECU in fisierul binar."""
    name: str
    address: int
    rows: int
    columns: int
    data_type: str = "u16"
    byte_order: str = "big"
    factor: float = 1.0
    offset: float = 0.0
    category: str = "unknown"
    value_unit: str | None = None
    short_name: str | None = None
    units: list[str] = field(default_factory=list)
    source: str = "manual"
    axes: list[AxisDefinition] = field(default_factory=list)


def _first(row: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    """Cauta aceeasi informatie sub mai multe nume posibile de coloana."""
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value not in (None, ""):
            return value
    return default


def _parse_int(value: Any, field_name: str) -> int:
    """Parseaza numere scrise fie zecimal, fie hexazecimal cu prefix 0x."""
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
    """Incadreaza automat o harta intr-o categorie tehnica dupa numele ei."""
    lower = name.lower()
    if any(token in lower for token in ("rpm limiter", "limiter", "speed limit", "maximum speed")):
        return "limiter"
    if "idle engine speed" in lower:
        return "limiter"
    if "throttle" in lower:
        return "air_fuel"
    if any(token in lower for token in ("torque", "nm", "driver wish", "pedal")):
        return "torque"
    if any(token in lower for token in ("engine load", "requested load", "desired load")):
        return "torque"
    if any(token in lower for token in ("boost", "pressure", "turbo")):
        return "boost"
    if any(token in lower for token in ("smoke", "lambda", "afr", "air", "volumetric", "throttle", "exhaust gas", "egt")):
        return "air_fuel"
    if any(token in lower for token in ("duration", "injection", "iq", "fuel")):
        return "fuel"
    if any(token in lower for token in ("soi", "start", "timing", "angle", "spark", "advance", "ignition", "btdc")):
        return "timing"
    if any(token in lower for token in ("rail", "cr pressure")):
        return "rail_pressure"
    return "unknown"


def _definition_from_row(row: dict[str, Any], index: int) -> MapDefinition:
    """Transforma un rand CSV/JSON intr-o definitie interna de harta."""
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

    units = [
        str(value).strip()
        for value in str(_first(row, ["unit", "units", "value_unit"], "")).split("|")
        if str(value).strip()
    ]
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
        value_unit=units[0] if units else None,
        short_name=_first(row, ["short_name", "symbol", "ols_name"]),
        units=units,
    )


def _read_u32_le(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset:offset + 4], "little", signed=False)


def _read_f64_le(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 8 > len(data):
        return None
    value = struct.unpack("<d", data[offset:offset + 8])[0]
    return value if math.isfinite(value) else None


def _is_printable_ascii(data: bytes) -> bool:
    return bool(data) and all(byte == 0 or 32 <= byte < 127 for byte in data)


def _is_unit_ascii(data: bytes) -> bool:
    return bool(data) and all(32 <= byte < 127 for byte in data)


def _read_kp_intern(raw_bytes: bytes) -> bytes | None:
    """Extrage sectiunea interna dintr-un fisier WinOLS .kp, daca structura permite."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            return archive.read("intern")
    except (KeyError, zipfile.BadZipFile):
        return None


def _kp_record_name(intern: bytes, start: int) -> str | None:
    """Incearca sa citeasca numele unei harti dintr-un record WinOLS."""
    name_length = _read_u32_le(intern, start + 0x1B)
    if name_length is None or not 4 <= name_length <= 80:
        return None

    name_bytes = intern[start + 0x1F:start + 0x1F + name_length]
    if len(name_bytes) != name_length or not _is_printable_ascii(name_bytes):
        return None

    name = name_bytes.rstrip(b"\x00").decode("latin1", errors="replace").strip()
    if len(name) < 6 or name.startswith("%"):
        return None
    if not any(character.isalpha() for character in name):
        return None
    return name


def _clean_kp_text(value: str) -> str:
    return value.replace("\x00", "").strip()


def _kp_record_strings(intern: bytes, start: int, limit: int = 0x260) -> list[str]:
    """Colecteaza fragmente text utile dintr-un record, precum unitati sau nume scurte."""
    record = intern[start:min(len(intern), start + limit)]
    values: list[str] = []
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-/().%")
    for match in re.finditer(rb"[\x20-\x7e]{3,}", record):
        text = _clean_kp_text(match.group().decode("latin1", errors="replace"))
        if not text:
            continue
        if not any(character.isalpha() for character in text):
            continue
        if sum(character not in allowed for character in text) > 1:
            continue
        if text not in values:
            values.append(text)
    return values


def _kp_record_metadata(intern: bytes, start: int, name: str) -> tuple[str | None, list[str]]:
    strings = _kp_record_strings(intern, start)
    remaining = [value for value in strings if value.rstrip() != name.rstrip()]
    short_name = next(
        (
            value
            for value in remaining
            if len(value) <= 32 and " " not in value and any(character == "_" for character in value)
        ),
        None,
    )

    unit_markers = ("%", "rpm", "hpa", "bar", "deg", "btdc", "factor", "ms", "lambda", "afr")
    units = [
        value
        for value in remaining
        if value != short_name and any(marker in value.lower() for marker in unit_markers)
    ]
    return short_name, units[:6]


def _kp_scale_block(
    intern: bytes,
    dim_offset: int,
    address_offset: int,
) -> tuple[str | None, float, float]:
    """Extrage unitatea, factorul si offsetul folosite pentru valorile hartii."""
    unit_length = _read_u32_le(intern, dim_offset + 0x18)
    if unit_length is None or not 1 <= unit_length <= 32:
        return None, 1.0, 0.0

    unit_start = dim_offset + 0x1C
    factor_offset = unit_start + unit_length
    offset_offset = factor_offset + 8
    if offset_offset + 8 > address_offset:
        return None, 1.0, 0.0

    unit_bytes = intern[unit_start:factor_offset]
    if not _is_printable_ascii(unit_bytes):
        return None, 1.0, 0.0

    factor = _read_f64_le(intern, factor_offset)
    offset = _read_f64_le(intern, offset_offset)
    if factor is None or offset is None:
        return None, 1.0, 0.0
    if not (1e-9 <= abs(factor) <= 100000):
        return None, 1.0, 0.0
    if not (-100000000 <= offset <= 100000000):
        return None, 1.0, 0.0

    return _clean_kp_text(unit_bytes.decode("latin1", errors="replace")), factor, offset


def _kp_axis_blocks(
    intern: bytes,
    start: int,
    address_offset: int,
    map_address: int,
    rows: int,
    columns: int,
) -> list[AxisDefinition]:
    """Cauta blocuri de axe in jurul unei harti WinOLS si le transforma in definitii."""
    candidates: list[dict[str, Any]] = []
    for block_start in range(address_offset + 4, min(start + 0x280, len(intern) - 32)):
        unit_length = _read_u32_le(intern, block_start)
        if unit_length is None or not 1 <= unit_length <= 32:
            continue

        unit_start = block_start + 4
        unit_end = unit_start + unit_length
        unit_bytes = intern[unit_start:unit_end]
        if len(unit_bytes) != unit_length or not _is_unit_ascii(unit_bytes):
            continue

        unit = _clean_kp_text(unit_bytes.decode("latin1", errors="replace"))
        if not unit or not any(character.isalpha() or character == "%" for character in unit):
            continue

        factor_offset = unit_end
        offset_offset = factor_offset + 8
        address_candidate_offset = offset_offset + 12
        factor = _read_f64_le(intern, factor_offset)
        value_offset = _read_f64_le(intern, offset_offset)
        address = _read_u32_le(intern, address_candidate_offset)
        if factor is None or value_offset is None or address is None:
            continue
        if not (1e-9 <= abs(factor) <= 100000):
            continue
        if not (-100000000 <= value_offset <= 100000000):
            continue
        if not (0x100 <= address < map_address):
            continue

        candidates.append(
            {
                "unit": unit,
                "address": address,
                "factor": factor,
                "offset": value_offset,
                "block_start": block_start,
            }
        )

    deduped: list[dict[str, Any]] = []
    seen_addresses: set[int] = set()
    for candidate in sorted(candidates, key=lambda item: item["block_start"]):
        if candidate["address"] in seen_addresses:
            continue
        seen_addresses.add(candidate["address"])
        deduped.append(candidate)

    addresses = sorted(candidate["address"] for candidate in deduped)
    expected_counts = list(dict.fromkeys([rows, columns, rows + 1, columns + 1]))
    axes: list[AxisDefinition] = []
    for index, candidate in enumerate(deduped):
        next_address = next(
            (address for address in addresses if address > candidate["address"]),
            map_address,
        )
        inferred_count = None
        if next_address > candidate["address"] and (next_address - candidate["address"]) % 2 == 0:
            raw_count = (next_address - candidate["address"]) // 2
            if raw_count in expected_counts:
                inferred_count = raw_count

        unit_lower = str(candidate["unit"]).lower()
        if "rpm" in unit_lower and inferred_count == columns + 1:
            inferred_count = columns
        if inferred_count is None:
            if "rpm" in unit_lower:
                inferred_count = columns
            elif "acc" in unit_lower or "pedal" in unit_lower:
                inferred_count = columns
            elif "%" in unit_lower or "hpa" in unit_lower or "bar" in unit_lower:
                inferred_count = rows if rows != max(rows, columns) else columns
            else:
                inferred_count = rows if index == 0 else columns

        if inferred_count <= 0 or inferred_count > 128:
            continue

        label = "rpm_axis" if "rpm" in unit_lower else "load_axis" if index < 2 else f"axis_{index + 1}"
        axes.append(
            AxisDefinition(
                label=label,
                address=int(candidate["address"]),
                count=int(inferred_count),
                factor=float(candidate["factor"]),
                offset=float(candidate["offset"]),
                unit=str(candidate["unit"]),
                byte_order="auto",
            )
        )

    return axes[:4]


def _kp_record_definition(intern: bytes, start: int, name: str) -> MapDefinition | None:
    # WinOLS stores map records with unaligned little-endian fields. A map is
    # accepted only when its address range matches rows * columns * 2 bytes.
    for dim_offset in range(start + 0x80, min(start + 0x190, len(intern) - 20)):
        columns = _read_u32_le(intern, dim_offset)
        rows = _read_u32_le(intern, dim_offset + 4)
        type_hint = _read_u32_le(intern, dim_offset + 16)
        if columns is None or rows is None or type_hint is None:
            continue
        if not (1 <= columns <= 80 and 1 <= rows <= 80 and 0 <= type_hint <= 20):
            continue

        byte_count = rows * columns * 2
        if not 2 <= byte_count <= 20000:
            continue

        for address_offset in range(dim_offset + 20, min(dim_offset + 200, len(intern) - 8)):
            address = _read_u32_le(intern, address_offset)
            end_address = _read_u32_le(intern, address_offset + 4)
            if address is None or end_address is None:
                continue
            if not (0x100 <= address < end_address <= 0x400000):
                continue
            if end_address - address != byte_count:
                continue

            short_name, units = _kp_record_metadata(intern, start, name)
            value_unit, factor, value_offset = _kp_scale_block(
                intern,
                dim_offset,
                address_offset,
            )
            all_units = [
                unit
                for unit in ([value_unit] if value_unit else []) + units
                if unit
            ]
            all_units = list(dict.fromkeys(all_units))
            axes = _kp_axis_blocks(
                intern,
                start,
                address_offset,
                address,
                rows,
                columns,
            )
            return MapDefinition(
                name=name,
                address=address,
                rows=rows,
                columns=columns,
                data_type="u16",
                byte_order="auto",
                factor=factor,
                offset=value_offset,
                category=_category_from_name(name),
                value_unit=value_unit,
                short_name=short_name,
                units=all_units,
                source="winols_kp",
                axes=axes,
            )
    return None


def _parse_winols_kp_definitions(raw_bytes: bytes) -> tuple[list[MapDefinition], list[str]]:
    """Parseaza definitii de harti direct dintr-un map pack WinOLS .kp."""
    intern = _read_kp_intern(raw_bytes)
    if intern is None:
        return [], [
            "The WinOLS .kp file could not be read because the internal map section was not found.",
            "Export map definitions from WinOLS as CSV/JSON if the .kp parser cannot read this file.",
        ]

    definitions: list[MapDefinition] = []
    seen: set[tuple[int, int, int]] = set()
    for start in range(0, max(0, len(intern) - 0x180)):
        if intern[start + 4:start + 10] != b"\x00\x00\xff\xff\xff\xff":
            continue

        name = _kp_record_name(intern, start)
        if name is None:
            continue
        definition = _kp_record_definition(intern, start, name)
        if definition is None:
            continue

        key = (definition.address, definition.rows, definition.columns)
        if key in seen:
            continue
        seen.add(key)
        definitions.append(definition)

    if definitions:
        return definitions, []

    return [], [
        "No usable map definitions could be extracted from the WinOLS .kp file.",
        "Export map definitions from WinOLS as CSV/JSON if this map pack cannot be parsed.",
    ]


def _parse_kp_metadata(raw_bytes: bytes) -> tuple[list[MapDefinition], list[str]]:
    """Pastreaza un strat separat pentru .kp, unde pot exista si metadate auxiliare."""
    definitions, warnings = _parse_winols_kp_definitions(raw_bytes)
    strings = [
        item.decode("latin1", errors="replace")
        for item in re.findall(rb"[\x20-\x7e]{4,}", raw_bytes)
    ]
    categories = [
        item
        for item in strings
        if item
        in {
            "Air Control",
            "Engine Torque",
            "Injection System",
            "Limiters",
            "Spark Advance",
            "Potential maps",
            "exhaust gas",
        }
    ]
    categories = list(dict.fromkeys(categories))

    return definitions, warnings


def parse_map_definitions(file_name: str, raw_bytes: bytes) -> tuple[list[MapDefinition], list[str]]:
    """Citeste definitii de harti din CSV, JSON sau WinOLS .kp."""
    if not raw_bytes:
        return [], ["The definitions file is empty."]

    suffix = Path(file_name).suffix.lower()
    if suffix == ".kp":
        return _parse_kp_metadata(raw_bytes)

    text = decode_map_file_content(raw_bytes)
    rows: list[dict[str, Any]]

    if suffix == ".json" or text.lstrip().startswith(("{", "[")):
        payload = json.loads(text)
        if isinstance(payload, dict):
            payload = payload.get("maps") or payload.get("definitions") or []
        if not isinstance(payload, list):
            raise ValueError("The definitions JSON must contain a list of maps.")
        rows = [item for item in payload if isinstance(item, dict)]
    else:
        reader = csv.DictReader(StringIO(text))
        if not reader.fieldnames:
            raise ValueError("The definitions CSV must include a header row.")
        rows = list(reader)

    definitions: list[MapDefinition] = []
    warnings: list[str] = []
    for index, row in enumerate(rows, start=1):
        try:
            definition = _definition_from_row(row, index)
        except ValueError as exc:
            warnings.append(f"Definition {index} was skipped: {exc}")
            continue
        if definition.rows <= 0 or definition.columns <= 0:
            warnings.append(f"Definition {definition.name} has invalid dimensions.")
            continue
        definitions.append(definition)

    if not definitions:
        warnings.append("No usable map definitions were found.")

    return definitions, warnings
