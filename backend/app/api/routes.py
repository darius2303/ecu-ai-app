from fastapi import APIRouter
from app.models.schemas import ECUInput, ECUResult
from app.services.analyzer import analyze_ecu_data
from app.services.fuel_map import generate_fuel_map
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from fastapi.responses import FileResponse
from app.services.visualization import generate_fuel_map_heatmap
from app.services.report_generator import generate_stage1_report
router = APIRouter(prefix="/api")

@router.post("/analyze", response_model=ECUResult)
def analyze_ecu(data: ECUInput):
    return analyze_ecu_data(data)

@router.post("/fuel-map")
def fuel_map(data: ECUInput):
    analysis = analyze_ecu_data(data)

    fuel_map_df = generate_fuel_map(
        rpm=data.rpm,
        boost_pressure=data.boost_pressure,
        injection_quantity=data.injection_quantity,
        stage1_gain_percent=analysis["stage1_gain_percent"]
    )

    return {
        "stage1_gain_percent": analysis["stage1_gain_percent"],
        "potential_class": analysis["potential_class"],
        "fuel_map": jsonable_encoder(fuel_map_df.to_dict())
    }

@router.post("/fuel-map-image")
def fuel_map_image(data: ECUInput):
    analysis = analyze_ecu_data(data)

    fuel_map_df = generate_fuel_map(
        rpm=data.rpm,
        boost_pressure=data.boost_pressure,
        injection_quantity=data.injection_quantity,
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
    analysis = analyze_ecu_data(data)

    fuel_map_df = generate_fuel_map(
        rpm=data.rpm,
        boost_pressure=data.boost_pressure,
        injection_quantity=data.injection_quantity,
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