import base64
import binascii
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    CalibrationAnalyzeInput,
    CalibrationUploadedFile,
    ECUInput,
    ECUResult,
    MapFileInput,
)
from app.services.analyzer import analyze_ecu_data
from app.services.calibration_analyzer import analyze_calibration
from app.services.file_formats import read_ecu_binary
from app.services.fuel_map import dataframe_from_calibration_map, generate_fuel_map
from app.services.map_definitions import parse_map_definitions
from app.services.map_utils import (
    decode_map_file_content,
    derive_features_from_map,
    parse_winols_map_text,
)
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from fastapi.responses import FileResponse
from app.services.visualization import generate_fuel_map_heatmap
from app.services.report_generator import generate_stage1_report
router = APIRouter(prefix="/api")

def _decode_uploaded_file(file: CalibrationUploadedFile, max_size: int) -> bytes:
    try:
        raw_bytes = base64.b64decode(file.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{file.file_name} nu a putut fi decodat.") from exc

    if len(raw_bytes) > max_size:
        raise HTTPException(status_code=413, detail=f"{file.file_name} este prea mare.")
    return raw_bytes


@router.post("/parse-map-file")
def parse_map_file(data: MapFileInput):
    try:
        raw_bytes = base64.b64decode(data.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Fisierul nu a putut fi decodat.") from exc

    if len(raw_bytes) > 2_000_000:
        raise HTTPException(status_code=413, detail="Fisierul este prea mare pentru import text.")

    try:
        raw_text = decode_map_file_content(raw_bytes)
        calibration_map = parse_winols_map_text(raw_text, map_type=data.map_type)
        derived_features = derive_features_from_map(
            calibration_map=calibration_map,
            fuel_type=data.fuel_type,
            is_turbo=data.is_turbo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "file_name": data.file_name,
        "calibration_map": calibration_map,
        "derived_features": derived_features,
    }


@router.post("/calibration/analyze")
def calibration_analyze(data: CalibrationAnalyzeInput):
    try:
        original = read_ecu_binary(
            data.original_file.file_name,
            _decode_uploaded_file(data.original_file, max_size=16_000_000),
        )
        modified = (
            read_ecu_binary(
                data.modified_file.file_name,
                _decode_uploaded_file(data.modified_file, max_size=16_000_000),
            )
            if data.modified_file is not None
            else None
        )

        definitions = []
        warnings: list[str] = []
        if data.definitions_file is not None:
            definitions, warnings = parse_map_definitions(
                data.definitions_file.file_name,
                _decode_uploaded_file(data.definitions_file, max_size=2_000_000),
            )

        return analyze_calibration(
            original=original,
            modified=modified,
            definitions=definitions,
            warnings=warnings,
            engine_displacement=data.engine_displacement,
            fuel_type=data.fuel_type,
            is_turbo=data.is_turbo,
            stock_hp=data.stock_hp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/analyze", response_model=ECUResult)
def analyze_ecu(data: ECUInput):
    try:
        return analyze_ecu_data(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/fuel-map")
def fuel_map(data: ECUInput):
    try:
        analysis = analyze_ecu_data(data)
        fuel_map_df = dataframe_from_calibration_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if fuel_map_df is None:
        features = analysis.get("derived_features") or {}
        fuel_map_df = generate_fuel_map(
            rpm=data.rpm if data.rpm is not None else features.get("rpm"),
            boost_pressure=(
                data.boost_pressure
                if data.boost_pressure is not None
                else features.get("boost_pressure")
            ),
            injection_quantity=(
                data.injection_quantity
                if data.injection_quantity is not None
                else features.get("injection_quantity")
            ),
            stage1_gain_percent=analysis["stage1_gain_percent"]
        )

    return {
        "stage1_gain_percent": analysis["stage1_gain_percent"],
        "potential_class": analysis["potential_class"],
        "derived_features": analysis.get("derived_features"),
        "fuel_map": jsonable_encoder(fuel_map_df.to_dict())
    }

@router.post("/fuel-map-image")
def fuel_map_image(data: ECUInput):
    try:
        analysis = analyze_ecu_data(data)
        fuel_map_df = dataframe_from_calibration_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if fuel_map_df is None:
        features = analysis.get("derived_features") or {}
        fuel_map_df = generate_fuel_map(
            rpm=data.rpm if data.rpm is not None else features.get("rpm"),
            boost_pressure=(
                data.boost_pressure
                if data.boost_pressure is not None
                else features.get("boost_pressure")
            ),
            injection_quantity=(
                data.injection_quantity
                if data.injection_quantity is not None
                else features.get("injection_quantity")
            ),
            stage1_gain_percent=analysis["stage1_gain_percent"]
        )

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / "fuel_map.png"
    generate_fuel_map_heatmap(fuel_map_df, output_path)

    return FileResponse(
        path=output_path,
        media_type="image/png",
        filename="fuel_map.png"
    )

@router.post("/report")
def report(data: ECUInput):
    try:
        analysis = analyze_ecu_data(data)
        fuel_map_df = dataframe_from_calibration_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if fuel_map_df is None:
        features = analysis.get("derived_features") or {}
        fuel_map_df = generate_fuel_map(
            rpm=data.rpm if data.rpm is not None else features.get("rpm"),
            boost_pressure=(
                data.boost_pressure
                if data.boost_pressure is not None
                else features.get("boost_pressure")
            ),
            injection_quantity=(
                data.injection_quantity
                if data.injection_quantity is not None
                else features.get("injection_quantity")
            ),
            stage1_gain_percent=analysis["stage1_gain_percent"]
        )

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)

    heatmap_path = output_dir / "fuel_map_report.png"
    pdf_path = output_dir / "stage1_report.pdf"

    generate_fuel_map_heatmap(fuel_map_df, heatmap_path)

    input_data = data.model_dump()

    generate_stage1_report(
        input_data=input_data,
        analysis=analysis,
        heatmap_path=heatmap_path,
        output_path=pdf_path
    )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="stage1_report.pdf"
    )
