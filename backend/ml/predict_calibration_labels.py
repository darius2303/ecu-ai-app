from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


DEFAULT_DATASET_PATH = Path("generated/calibration_ml_dataset.json")
DEFAULT_ARTIFACTS_DIR = Path("ml/artifacts/calibration_labels")
DEFAULT_OUTPUT_CSV = Path("generated/ml_predictions.csv")
DEFAULT_OUTPUT_JSON = Path("generated/ml_predictions.json")


def _load_rows(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"ML dataset not found: {dataset_path}")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = dataset.get("rows") or []
    return [row for row in rows if isinstance(row, dict)]


def _load_bundle(artifacts_dir: Path, filename: str) -> dict[str, Any]:
    path = artifacts_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    return joblib.load(path)


def _features_frame(rows: list[dict[str, Any]], bundle: dict[str, Any]) -> pd.DataFrame:
    features = bundle["numeric_features"] + bundle["categorical_features"]
    records = []
    for row in rows:
        records.append({feature: row.get(feature) for feature in features})
    return pd.DataFrame(records, columns=features)


def _predict_with_confidence(bundle: dict[str, Any], x: pd.DataFrame) -> list[dict[str, Any]]:
    pipeline = bundle["pipeline"]
    labels = pipeline.predict(x)
    probabilities = pipeline.predict_proba(x) if hasattr(pipeline, "predict_proba") else None
    classes = list(getattr(pipeline.named_steps["model"], "classes_", []))
    output = []
    for index, label in enumerate(labels):
        confidence = None
        if probabilities is not None and classes:
            class_index = classes.index(label)
            confidence = round(float(probabilities[index][class_index]), 4)
        output.append({"label": str(label), "confidence": confidence})
    return output


def predict_labels(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR,
    output_csv: Path = DEFAULT_OUTPUT_CSV,
    output_json: Path = DEFAULT_OUTPUT_JSON,
) -> dict[str, Any]:
    rows = _load_rows(dataset_path)
    if not rows:
        raise ValueError("ML dataset has no rows.")

    label_bundle = _load_bundle(artifacts_dir, "calibration_label_model.joblib")
    risk_bundle = _load_bundle(artifacts_dir, "calibration_risk_model.joblib")
    label_predictions = _predict_with_confidence(
        label_bundle,
        _features_frame(rows, label_bundle),
    )
    risk_predictions = _predict_with_confidence(
        risk_bundle,
        _features_frame(rows, risk_bundle),
    )

    predictions: list[dict[str, Any]] = []
    for row, label_prediction, risk_prediction in zip(rows, label_predictions, risk_predictions):
        predictions.append(
            {
                "sample_id": row.get("sample_id"),
                "map_name": row.get("map_name"),
                "map_category": row.get("map_category"),
                "changed_percent": row.get("changed_percent"),
                "max_abs_delta": row.get("max_abs_delta"),
                "direction": row.get("direction"),
                "seed_label": row.get("seed_label"),
                "predicted_label": label_prediction["label"],
                "label_confidence": label_prediction["confidence"],
                "predicted_risk": risk_prediction["label"],
                "risk_confidence": risk_prediction["confidence"],
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(predictions[0].keys())
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)
    output_json.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    return {
        "rows": len(predictions),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict calibration labels using trained baseline models."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = parser.parse_args()

    result = predict_labels(
        dataset_path=args.dataset,
        artifacts_dir=args.artifacts_dir,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(f"Wrote {result['rows']} predictions to {result['output_csv']}")


if __name__ == "__main__":
    main()
