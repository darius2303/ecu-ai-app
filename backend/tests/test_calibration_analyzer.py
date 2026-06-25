import struct

from app.services.calibration_analyzer import analyze_calibration
from app.services.file_formats import EcuBinary
from app.services.map_definitions import MapDefinition


def _ecu(name: str, values: list[int]) -> EcuBinary:
    return EcuBinary(
        file_name=name,
        content=struct.pack(">" + "H" * len(values), *values),
        file_format="binary",
    )


def _definition(
    name: str,
    category: str,
    address: int,
    rows: int = 2,
    columns: int = 2,
) -> MapDefinition:
    return MapDefinition(
        name=name,
        address=address,
        rows=rows,
        columns=columns,
        data_type="u16",
        byte_order="big",
        factor=0.1,
        offset=0,
        category=category,
        value_unit="Nm" if category == "torque" else None,
    )


def test_analyze_calibration_reports_missing_context_without_definitions():
    result = analyze_calibration(
        original=_ecu("original.bin", [100, 200, 300, 400]),
        modified=_ecu("modified.bin", [100, 260, 300, 500]),
        definitions=[],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=78,
    )

    assert result["summary"]["definitions_count"] == 0
    assert result["summary"]["maps_extracted"] == 0
    assert result["analysis_verdict"]["status"] == "missing_context"
    assert any("No map definitions were loaded" in item for item in result["warnings"])


def test_analyze_calibration_enters_planning_mode_without_modified_file():
    result = analyze_calibration(
        original=_ecu("original.bin", [100, 200, 300, 400]),
        modified=None,
        definitions=[_definition("Torque request", "torque", 0)],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=78,
    )

    assert result["summary"]["maps_extracted"] == 1
    assert result["summary"]["maps_changed"] == 0
    assert result["binary_diff"] is None
    assert result["analysis_verdict"]["status"] == "planning_mode"
    assert any("No tuned/current file was loaded" in item for item in result["warnings"])


def test_analyze_calibration_skips_definition_outside_file_size():
    result = analyze_calibration(
        original=_ecu("original.bin", [100, 200, 300, 400]),
        modified=_ecu("modified.bin", [100, 260, 300, 500]),
        definitions=[_definition("Broken map", "torque", 100)],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=78,
    )

    assert result["summary"]["maps_extracted"] == 0
    assert any("Broken map was skipped" in item for item in result["warnings"])


def test_analyze_calibration_generates_torque_and_supporting_fuel_recommendations():
    original = _ecu("original.bin", [100, 200, 300, 400, 50, 60, 70, 80])
    modified = _ecu("modified.bin", [100, 260, 300, 500, 50, 60, 70, 80])
    definitions = [
        _definition("Torque request", "torque", 0),
        _definition("Injection base map", "fuel", 8),
    ]

    result = analyze_calibration(
        original=original,
        modified=modified,
        definitions=definitions,
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=78,
    )

    recommendations = result["recommendations"]
    torque_recommendation = next(
        item for item in recommendations
        if item["category"] == "torque"
    )
    fuel_recommendation = next(
        item for item in recommendations
        if item["category"] == "fuel"
    )

    assert result["summary"]["maps_changed"] == 1
    assert torque_recommendation["mode"] == "review_existing_change"
    assert "fuel" in torque_recommendation["supporting_maps_to_review"]
    assert fuel_recommendation["mode"] == "review_supporting_map"
    assert fuel_recommendation["priority"] in {"medium", "high"}


def test_analyze_calibration_continues_when_ml_artifacts_are_unavailable(monkeypatch):
    def raise_missing_model(*args, **kwargs):
        raise FileNotFoundError("missing model for test")

    monkeypatch.setattr(
        "app.services.calibration_ml._load_model_bundle",
        raise_missing_model,
    )

    result = analyze_calibration(
        original=_ecu("original.bin", [100, 200, 300, 400]),
        modified=_ecu("modified.bin", [100, 260, 300, 500]),
        definitions=[_definition("Torque request", "torque", 0)],
        engine_displacement=1.0,
        fuel_type="petrol",
        is_turbo=False,
        stock_hp=78,
    )

    assert result["ml_summary"]["available"] is False
    assert "missing model for test" in result["ml_summary"]["reason"]
    assert result["recommendations"]
    assert any("AI-assisted review is unavailable" in item for item in result["warnings"])
