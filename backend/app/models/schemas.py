from pydantic import BaseModel
from typing import Optional, Literal


class ECUInput(BaseModel):
    rpm: float
    boost_pressure: float
    injection_quantity: float
    afr: float

    engine_displacement: float  # litri
    fuel_type: Literal["diesel", "petrol"]
    is_turbo: bool
    stock_hp: Optional[float] = None


class ECUResult(BaseModel):
    stage1_gain_percent: float
    potential_class: str
    estimated_hp_after_stage1: Optional[float] = None

class FuelMapCell(BaseModel):
    rpm: int
    boost: float
    injection: float