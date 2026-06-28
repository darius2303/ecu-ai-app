from pydantic import BaseModel
from typing import Optional, Literal


class CalibrationUploadedFile(BaseModel):
    """Reprezinta un fisier trimis prin API, codificat Base64 de catre frontend."""
    file_name: str
    content_base64: str


class CalibrationAnalyzeInput(BaseModel):
    """Modelul cererii comune pentru analiza, raport PDF si exporturi ML."""
    original_file: CalibrationUploadedFile
    modified_file: Optional[CalibrationUploadedFile] = None
    definitions_file: Optional[CalibrationUploadedFile] = None
    engine_displacement: Optional[float] = None
    fuel_type: Optional[Literal["diesel", "petrol"]] = None
    is_turbo: Optional[bool] = None
    stock_hp: Optional[float] = None
