import numpy as np
import pandas as pd


ENGINE_PROFILES = [
    # diesel
    {"fuel": "diesel", "turbo": True,  "base_gain": (6, 12)},
    {"fuel": "diesel", "turbo": False, "base_gain": (2, 5)},

    # petrol
    {"fuel": "petrol", "turbo": True,  "base_gain": (8, 15)},
    {"fuel": "petrol", "turbo": False, "base_gain": (2, 6)},
]


def generate_dataset(n_samples=8000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []

    for _ in range(n_samples):
        profile = rng.choice(ENGINE_PROFILES)

        fuel = profile["fuel"]
        is_turbo = profile["turbo"]

        displacement = rng.uniform(1.2, 3.5)
        stock_hp = (
            displacement * rng.uniform(60, 90)
            if not is_turbo
            else displacement * rng.uniform(90, 140)
        )

        rpm = rng.uniform(900, 6500)
        boost = rng.uniform(0.8, 2.2) if is_turbo else rng.uniform(0.95, 1.05)
        injection = rng.uniform(10, 85)
        afr = rng.uniform(12.0, 16.5)

        base_min, base_max = profile["base_gain"]
        load_factor = min(1.0, rpm / 4000)

        gain = rng.uniform(base_min, base_max)
        gain *= load_factor
        gain -= max(0, afr - 14.7) * 0.8
        gain += (boost - 1.0) * 2 if is_turbo else 0
        gain += rng.normal(0, 0.7)

        gain = np.clip(gain, 0, 18)

        rows.append({
            "rpm": rpm,
            "boost_pressure": boost,
            "injection_quantity": injection,
            "afr": afr,
            "engine_displacement": displacement,
            "fuel_type": fuel,
            "is_turbo": int(is_turbo),
            "stock_hp": stock_hp,
            "stage1_gain_percent": gain
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("dataset_stage1_multiengine.csv", index=False)
    print("✔ Dataset Stage 1 multi-engine generat")
