import base64
import binascii
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    CalibrationAnalyzeInput,
    CalibrationUploadedFile,
)
from app.services.calibration_analyzer import analyze_calibration
from app.services.file_formats import read_ecu_binary
from app.services.map_definitions import parse_map_definitions
from pathlib import Path
from fastapi.responses import FileResponse
from app.services.report_generator import generate_calibration_report
from app.services.calibration_dataset import (
    write_labeling_template_csv,
    write_ml_dataset_json,
)
router = APIRouter(prefix="/api")

def _decode_uploaded_file(file: CalibrationUploadedFile, max_size: int) -> bytes:
    """Decodeaza fisierul trimis de frontend si verifica limita de dimensiune."""
    try:
        raw_bytes = base64.b64decode(file.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{file.file_name} nu a putut fi decodat.") from exc

    if len(raw_bytes) > max_size:
        raise HTTPException(status_code=413, detail=f"{file.file_name} is too large.")
    return raw_bytes


@router.post("/calibration/analyze")
def calibration_analyze(data: CalibrationAnalyzeInput):
    """Endpoint-ul principal: primeste fisierele ECU si returneaza analiza JSON."""
    try:
        return _run_calibration_analysis(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _run_calibration_analysis(data: CalibrationAnalyzeInput):
    """Pregateste fisierele incarcate si apeleaza serviciul central de analiza."""
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


@router.post("/calibration/report")
def calibration_report(data: CalibrationAnalyzeInput):
    """Genereaza raportul PDF pe baza aceleiasi analize folosite in interfata."""
    try:
        analysis = _run_calibration_analysis(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / "calibration_tuner_report.pdf"
    generate_calibration_report(analysis=analysis, output_path=pdf_path)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="calibration_tuner_report.pdf",
    )


@router.post("/calibration/ml-dataset")
def calibration_ml_dataset(data: CalibrationAnalyzeInput):
    """Exporta datasetul intermediar folosit pentru etichetare si experimente ML."""
    try:
        analysis = _run_calibration_analysis(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    dataset_path = output_dir / "calibration_ml_dataset.json"
    write_ml_dataset_json(
        dataset=analysis.get("ml_dataset") or {},
        output_path=dataset_path,
    )
    return FileResponse(
        path=dataset_path,
        media_type="application/json",
        filename="calibration_ml_dataset.json",
    )


@router.post("/calibration/labeling-template")
def calibration_labeling_template(data: CalibrationAnalyzeInput):
    """Exporta un CSV usor de completat manual pentru imbunatatirea datasetului."""
    try:
        analysis = _run_calibration_analysis(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / "calibration_labeling_template.csv"
    write_labeling_template_csv(
        dataset=analysis.get("ml_dataset") or {},
        output_path=csv_path,
    )
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="calibration_labeling_template.csv",
    )
