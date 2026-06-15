from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd

from app.services.map_utils import derive_features_from_map, ensure_calibration_map

# Calea către modelul antrenat
MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "stage1_model.joblib"

_model = None  # lazy-loaded


def _load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
    return _model


def _potential_class(gain_percent: float) -> str:
    # praguri simple + explicabile (le poți ajusta ulterior)
    if gain_percent < 4.0:
        return "Low"
    if gain_percent < 9.0:
        return "Moderate"
    return "High"


def analyze_ecu_data(data):
    """
    Primește ECUInput (pydantic) și întoarce dict compatibil ECUResult.
    Modelul prezice stage1_gain_percent (câștig relativ).
    """
    model = _load_model()
    derived_features = None
    calibration_map = ensure_calibration_map(data)

    if calibration_map is not None:
        derived_features = derive_features_from_map(
            calibration_map=calibration_map,
            fuel_type=data.fuel_type,
            is_turbo=data.is_turbo,
        )

    rpm = data.rpm if data.rpm is not None else (derived_features or {}).get("rpm")
    boost_pressure = (
        data.boost_pressure
        if data.boost_pressure is not None
        else (derived_features or {}).get("boost_pressure")
    )
    injection_quantity = (
        data.injection_quantity
        if data.injection_quantity is not None
        else (derived_features or {}).get("injection_quantity")
    )
    afr = data.afr if data.afr is not None else (derived_features or {}).get("afr")

    missing = [
        name
        for name, value in {
            "rpm": rpm,
            "boost_pressure": boost_pressure,
            "injection_quantity": injection_quantity,
            "afr": afr,
        }.items()
        if value is None
    ]
    if missing:
        raise ValueError(
            "Lipsesc valori pentru analiza: "
            + ", ".join(missing)
            + ". Completeaza campurile manual sau insereaza o harta WinOLS."
        )

    # pipeline-ul a fost antrenat pe aceste coloane
    row = {
        "rpm": float(rpm),
        "boost_pressure": float(boost_pressure),
        "injection_quantity": float(injection_quantity),
        "afr": float(afr),
        "engine_displacement": float(data.engine_displacement),
        "fuel_type": data.fuel_type,
        "is_turbo": int(bool(data.is_turbo)),
        "stock_hp": float(data.stock_hp) if data.stock_hp is not None else None,
    }

    X = pd.DataFrame([row])
    gain = float(model.predict(X)[0])

    # limite de siguranță (și pentru raport, și ca să nu iasă valori aiurea)
    gain = max(0.0, min(18.0, gain))

    result = {
        "stage1_gain_percent": round(gain, 2),
        "potential_class": _potential_class(gain),
        "estimated_hp_after_stage1": None,
        "derived_features": derived_features,
    }

    if data.stock_hp is not None:
        result["estimated_hp_after_stage1"] = round(float(data.stock_hp) * (1.0 + gain / 100.0), 2)

    return result
