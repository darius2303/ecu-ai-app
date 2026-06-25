import struct

import pytest

from app.services.calibration_maps import compare_values, extract_map_values
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
