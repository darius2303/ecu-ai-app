from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.map_utils import ensure_calibration_map


def dataframe_from_calibration_map(data) -> pd.DataFrame | None:
    calibration_map = ensure_calibration_map(data)
    if calibration_map is None:
        return None
    if calibration_map.get("map_type") != "fuel":
        return None

    df = pd.DataFrame(
        calibration_map["values"],
        index=[int(x) if float(x).is_integer() else round(float(x), 2) for x in calibration_map["rpm_axis"]],
        columns=[round(float(x), 2) for x in calibration_map["load_axis"]],
    )
    df.index.name = "RPM"
    df.columns.name = "Load"
    return df


def generate_fuel_map(
    rpm: float,
    boost_pressure: float,
    injection_quantity: float,
    stage1_gain_percent: float
) -> pd.DataFrame:
    """
    Generează un fuel map orientativ pentru Stage 1.
    Valorile sunt estimative și au rol de suport decizional / vizualizare.
    """

    rpm_bins = np.array([1500, 2500, 3500, 4500, 5500], dtype=float)
    boost_bins = np.array([1.0, 1.2, 1.4, 1.6, 1.8, 2.0], dtype=float)

    gain_factor = 1.0 + (stage1_gain_percent / 100.0) * 0.55

    values = []

    for r in rpm_bins:
        row = []
        for b in boost_bins:
            rpm_factor = 0.85 + (r / 5500.0) * 0.35
            boost_factor = 0.9 + (b / 2.0) * 0.4

            estimated_injection = injection_quantity * rpm_factor * boost_factor
            estimated_injection *= gain_factor

            row.append(round(float(estimated_injection), 2))
        values.append(row)

    df = pd.DataFrame(
        values,
        index=[int(x) for x in rpm_bins],
        columns=[round(float(x), 1) for x in boost_bins]
    )

    df.index.name = "RPM"
    df.columns.name = "Boost"
    return df
