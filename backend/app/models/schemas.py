from pydantic import BaseModel
from typing import Optional, Literal


class CalibrationMap(BaseModel):
    map_type: Literal["soi", "fuel", "boost", "torque"] = "soi"
    rpm_axis: list[float]
    load_axis: list[float]
    values: list[list[float]]
    value_unit: Optional[str] = None


class MapDerivedFeatures(BaseModel):
    rpm: float
    boost_pressure: float
    injection_quantity: float
    afr: float
    map_type: str
    rows: int
    columns: int
    min_value: float
    max_value: float
    high_load_mean: float


class ECUInput(BaseModel):
    rpm: Optional[float] = None
    boost_pressure: Optional[float] = None
    injection_quantity: Optional[float] = None
    afr: Optional[float] = None

    engine_displacement: float  # litri
    fuel_type: Literal["diesel", "petrol"]
    is_turbo: bool
    stock_hp: Optional[float] = None
    calibration_map: Optional[CalibrationMap] = None
    calibration_map_text: Optional[str] = None
    calibration_map_type: Literal["soi", "fuel", "boost", "torque"] = "soi"


class MapFileInput(BaseModel):
    file_name: str
    content_base64: str
    map_type: Literal["soi", "fuel", "boost", "torque"] = "soi"
    fuel_type: Literal["diesel", "petrol"]
    is_turbo: bool


class CalibrationUploadedFile(BaseModel):
    file_name: str
    content_base64: str


class CalibrationAnalyzeInput(BaseModel):
    original_file: CalibrationUploadedFile
    modified_file: Optional[CalibrationUploadedFile] = None
    definitions_file: Optional[CalibrationUploadedFile] = None
    engine_displacement: Optional[float] = None
    fuel_type: Optional[Literal["diesel", "petrol"]] = None
    is_turbo: Optional[bool] = None
    stock_hp: Optional[float] = None


class ECUResult(BaseModel):
    stage1_gain_percent: float
    potential_class: str
    estimated_hp_after_stage1: Optional[float] = None
    derived_features: Optional[MapDerivedFeatures] = None

class FuelMapCell(BaseModel):
    rpm: int
    boost: float
    injection: float
