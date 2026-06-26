import base64
import struct

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _uploaded(file_name: str, content: bytes) -> dict:
    return {
        "file_name": file_name,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def test_calibration_analyze_endpoint_runs_full_csv_definition_flow():
    original = struct.pack(">HHHH", 100, 200, 300, 400)
    modified = struct.pack(">HHHH", 100, 260, 300, 500)
    definitions = (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit\n"
        "Torque request,0,2,2,u16,big,0.1,0,Nm\n"
    ).encode()

    response = client.post(
        "/api/calibration/analyze",
        json={
            "original_file": _uploaded("original.bin", original),
            "modified_file": _uploaded("modified.bin", modified),
            "definitions_file": _uploaded("maps.csv", definitions),
            "engine_displacement": 1.0,
            "fuel_type": "petrol",
            "is_turbo": False,
            "stock_hp": 78,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["maps_extracted"] == 1
    assert payload["summary"]["maps_changed"] == 1
    assert payload["binary_diff"]["changed_bytes"] == 3

    extracted_map = payload["maps"][0]
    assert extracted_map["name"] == "Torque request"
    assert extracted_map["category"] == "torque"
    assert extracted_map["preview"] == [[10.0, 20.0], [30.0, 40.0]]
    assert extracted_map["modified_preview"] == [[10.0, 26.0], [30.0, 50.0]]
    assert extracted_map["diff"]["changed_cells"] == 2
    assert extracted_map["diff"]["changed_percent"] == 50.0

    assert payload["recommendations"]
    assert payload["analysis_verdict"]["status"] in {
        "needs_validation",
        "high_risk_pattern",
        "looks_coherent",
    }


def test_calibration_analyze_endpoint_rejects_invalid_base64():
    response = client.post(
        "/api/calibration/analyze",
        json={
            "original_file": {
                "file_name": "broken.bin",
                "content_base64": "not-valid-base64",
            }
        },
    )

    assert response.status_code == 400


def test_calibration_report_endpoint_returns_pdf():
    original = struct.pack(">HHHH", 100, 200, 300, 400)
    modified = struct.pack(">HHHH", 100, 260, 300, 500)
    definitions = (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit\n"
        "Torque request,0,2,2,u16,big,0.1,0,Nm\n"
    ).encode()

    response = client.post(
        "/api/calibration/report",
        json={
            "original_file": _uploaded("original.bin", original),
            "modified_file": _uploaded("modified.bin", modified),
            "definitions_file": _uploaded("maps.csv", definitions),
            "engine_displacement": 1.0,
            "fuel_type": "petrol",
            "is_turbo": False,
            "stock_hp": 78,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert response.content.rstrip().endswith(b"%%EOF")
    assert len(response.content) > 2_000


def test_calibration_ml_dataset_endpoint_returns_feature_rows():
    original = struct.pack(">HHHH", 100, 200, 300, 400)
    modified = struct.pack(">HHHH", 100, 260, 300, 500)
    definitions = (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit\n"
        "Torque request,0,2,2,u16,big,0.1,0,Nm\n"
    ).encode()

    response = client.post(
        "/api/calibration/ml-dataset",
        json={
            "original_file": _uploaded("original.bin", original),
            "modified_file": _uploaded("modified.bin", modified),
            "definitions_file": _uploaded("maps.csv", definitions),
            "engine_displacement": 1.0,
            "fuel_type": "petrol",
            "is_turbo": False,
            "stock_hp": 78,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["version"] == "calibration-features-v1"
    assert payload["summary"]["samples"] == 1
    assert payload["rows"][0]["map_category"] == "torque"
    assert payload["rows"][0]["changed_percent"] == 50.0
    assert payload["rows"][0]["include_for_training"] is False


def test_calibration_labeling_template_endpoint_returns_review_columns():
    original = struct.pack(">HHHH", 100, 200, 300, 400)
    definitions = (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit\n"
        "Injection base map,0,2,2,u16,big,0.1,0,mg\n"
    ).encode()

    response = client.post(
        "/api/calibration/labeling-template",
        json={
            "original_file": _uploaded("original.bin", original),
            "definitions_file": _uploaded("maps.csv", definitions),
            "engine_displacement": 1.0,
            "fuel_type": "petrol",
            "is_turbo": False,
            "stock_hp": 78,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.content.decode("utf-8")
    assert "manual_label" in text.splitlines()[0]
    assert "manual_risk_label" in text.splitlines()[0]
    assert "Injection base map" in text


def test_calibration_analyze_endpoint_rejects_missing_original_file():
    response = client.post("/api/calibration/analyze", json={})

    assert response.status_code == 422


def test_calibration_analyze_endpoint_rejects_invalid_fuel_type():
    response = client.post(
        "/api/calibration/analyze",
        json={
            "original_file": _uploaded("original.bin", b"\x00\x01"),
            "fuel_type": "hydrogen",
        },
    )

    assert response.status_code == 422


def test_calibration_analyze_endpoint_rejects_oversized_ecu_file():
    oversized = b"\x00" * 16_000_001

    response = client.post(
        "/api/calibration/analyze",
        json={
            "original_file": _uploaded("too_large.bin", oversized),
        },
    )

    assert response.status_code == 413
