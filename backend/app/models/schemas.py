from pydantic import BaseModel
from typing import Optional, Literal


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
