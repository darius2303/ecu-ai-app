from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd

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

    # pipeline-ul a fost antrenat pe aceste coloane
    row = {
        "rpm": float(data.rpm),
        "boost_pressure": float(data.boost_pressure),
        "injection_quantity": float(data.injection_quantity),
        "afr": float(data.afr),
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
    }

    if data.stock_hp is not None:
        result["estimated_hp_after_stage1"] = round(float(data.stock_hp) * (1.0 + gain / 100.0), 2)

    return result
