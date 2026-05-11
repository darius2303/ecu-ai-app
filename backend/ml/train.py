import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib


ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_data():
    return pd.read_csv("dataset_stage1_multiengine.csv")


def build_pipeline():
    numeric_features = [
        "rpm",
        "boost_pressure",
        "injection_quantity",
        "afr",
        "engine_displacement",
        "stock_hp",
        "is_turbo",
    ]

    categorical_features = ["fuel_type"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=18,
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def train():
    df = load_data()

    X = df.drop(columns=["stage1_gain_percent"])
    y = df["stage1_gain_percent"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"MAE: {mae:.2f} %")
    print(f"R²: {r2:.3f}")

    joblib.dump(pipeline, ARTIFACTS_DIR / "stage1_model.joblib")

    metrics = {
        "mae_percent": mae,
        "r2": r2,
        "n_samples": len(df),
        "model": "RandomForestRegressor",
        "stage": "Stage 1",
    }

    with open(ARTIFACTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)


if __name__ == "__main__":
    train()
