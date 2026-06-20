from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DEFAULT_DATASET_PATH = Path("generated/training_dataset.csv")
DEFAULT_ARTIFACTS_DIR = Path("ml/artifacts/calibration_labels")

NUMERIC_FEATURES = [
    "changed_percent",
    "max_abs_delta",
    "affected_rpm_min",
    "affected_rpm_max",
    "affected_load_min",
    "affected_load_max",
    "ml_confidence_seed",
]

CATEGORICAL_FEATURES = [
    "map_name",
    "map_category",
    "source_mode",
    "direction",
    "seed_label",
    "recommendation_priority",
    "recommendation_risk",
]

TARGETS = {
    "manual_label": "calibration_label_model.joblib",
    "manual_risk_label": "calibration_risk_model.joblib",
}


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {dataset_path}")
    df = pd.read_csv(dataset_path)
    df = df[df["review_status"].astype(str).str.lower() == "reviewed"].copy()
    df = df[df["include_for_training"].astype(str).str.lower().isin(["true", "1", "yes"])]
    df = df[df["manual_label"].notna() & (df["manual_label"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def _available_features(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = [column for column in NUMERIC_FEATURES if column in df.columns]
    categorical = [column for column in CATEGORICAL_FEATURES if column in df.columns]
    return numeric, categorical


def _build_pipeline(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                    ]
                ),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", classifier),
        ]
    )


def _split_data(
    x: pd.DataFrame,
    y: pd.Series,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    counts = y.value_counts()
    stratify = y if len(counts) > 1 and int(counts.min()) >= 2 else None
    return train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=42,
        stratify=stratify,
    )


def _feature_importance(pipeline: Pipeline, limit: int = 25) -> list[dict[str, Any]]:
    preprocessor = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    try:
        names = preprocessor.get_feature_names_out()
    except Exception:
        return []
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    ranked = sorted(
        zip(names, importances),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [
        {"feature": str(name), "importance": round(float(importance), 6)}
        for name, importance in ranked[:limit]
    ]


def _train_target(
    df: pd.DataFrame,
    target: str,
    output_path: Path,
    numeric_features: list[str],
    categorical_features: list[str],
    test_size: float,
) -> dict[str, Any]:
    target_df = df[df[target].notna() & (df[target].astype(str).str.strip() != "")].copy()
    class_counts = target_df[target].astype(str).value_counts().to_dict()
    if len(class_counts) < 2:
        return {
            "target": target,
            "trained": False,
            "reason": "target has fewer than 2 classes",
            "class_counts": class_counts,
        }

    features = numeric_features + categorical_features
    x = target_df[features].copy()
    y = target_df[target].astype(str)
    x_train, x_test, y_train, y_test = _split_data(x, y, test_size=test_size)

    pipeline = _build_pipeline(numeric_features, categorical_features)
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "target": target,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "classes": sorted(y.unique().tolist()),
        },
        output_path,
    )

    labels = sorted(y.unique().tolist())
    return {
        "target": target,
        "trained": True,
        "artifact": str(output_path),
        "rows": len(target_df),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "class_counts": class_counts,
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            zero_division=0,
            output_dict=True,
        ),
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        },
        "top_features": _feature_importance(pipeline),
    }


def train_models(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR,
    test_size: float = 0.25,
) -> dict[str, Any]:
    df = _load_dataset(dataset_path)
    if df.empty:
        raise ValueError("No reviewed training rows found.")

    numeric_features, categorical_features = _available_features(df)
    if not numeric_features and not categorical_features:
        raise ValueError("No usable features found in the training dataset.")

    results = []
    for target, filename in TARGETS.items():
        if target not in df.columns:
            results.append(
                {
                    "target": target,
                    "trained": False,
                    "reason": "target column missing",
                }
            )
            continue
        results.append(
            _train_target(
                df=df,
                target=target,
                output_path=artifacts_dir / filename,
                numeric_features=numeric_features,
                categorical_features=categorical_features,
                test_size=test_size,
            )
        )

    report = {
        "dataset": str(dataset_path),
        "rows": len(df),
        "features": {
            "numeric": numeric_features,
            "categorical": categorical_features,
        },
        "models": results,
        "notes": [
            "Baseline model only; dataset is small and likely imbalanced.",
            "Use predictions as decision-support, not as an automatic tuning decision.",
        ],
    }
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = artifacts_dir / "training_metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train baseline calibration label classifiers from reviewed CSV data."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args()

    report = train_models(
        dataset_path=args.dataset,
        artifacts_dir=args.artifacts_dir,
        test_size=args.test_size,
    )
    print(f"Rows: {report['rows']}")
    for model in report["models"]:
        if model.get("trained"):
            print(
                f"{model['target']}: accuracy={model['accuracy']} "
                f"artifact={model['artifact']}"
            )
        else:
            print(f"{model['target']}: skipped ({model.get('reason')})")


if __name__ == "__main__":
    main()
