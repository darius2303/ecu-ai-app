from __future__ import annotations

import numpy as np
import pandas as pd


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