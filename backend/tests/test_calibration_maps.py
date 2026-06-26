import struct

import pytest

from app.services.calibration_maps import compare_values, delta_preview, extract_map_values
from app.services.map_definitions import MapDefinition


def test_extracts_scaled_map_values_from_binary_content():
    content = struct.pack(">HHHH", 100, 200, 300, 400)
    definition = MapDefinition(
        name="Injection base map",
        address=0,
        rows=2,
        columns=2,
        data_type="u16",
        byte_order="big",
        factor=0.1,
        offset=1,
    )

    values = extract_map_values(content, definition)

    assert values == [[11.0, 21.0], [31.0, 41.0]]


def test_compares_original_and_modified_map_values():
    original = [[10.0, 20.0], [30.0, 40.0]]
    modified = [[10.0, 25.0], [30.0, 50.0]]

    diff = compare_values(original, modified)

    assert diff["changed_cells"] == 2
    assert diff["total_cells"] == 4
    assert diff["changed_percent"] == 50.0
    assert diff["mean_delta"] == 3.75
    assert diff["max_abs_delta"] == 10.0
    assert diff["direction"] == "increase"
    assert diff["changed_bounds"] == {
        "row_min": 0,
        "row_max": 1,
        "column_min": 1,
        "column_max": 1,
    }


def test_compare_values_rejects_mismatched_shapes():
    with pytest.raises(ValueError, match="dimensions"):
        compare_values([[1.0, 2.0]], [[1.0], [2.0]])


def test_extracts_signed_little_endian_values():
    content = struct.pack("<hh", -10, 20)
    definition = MapDefinition(
        name="Spark advance correction",
        address=0,
        rows=1,
        columns=2,
        data_type="s16",
        byte_order="little",
        factor=0.5,
        offset=0,
    )

    values = extract_map_values(content, definition)

    assert values == [[-5.0, 10.0]]


def test_delta_preview_limits_and_rounds_values():
    original = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    modified = [[1.5, 1.0, 3.0], [4.0, 7.25, 9.0]]

    preview = delta_preview(original, modified, limit=2)

    assert preview == [[0.5, -1.0], [0.0, 2.25]]
