from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml"
    / "artifacts"
    / "calibration_labels"
)
LABEL_MODEL_PATH = ARTIFACTS_DIR / "calibration_label_model.joblib"
RISK_MODEL_PATH = ARTIFACTS_DIR / "calibration_risk_model.joblib"
ADVISORY_CONFIDENCE = 0.55
STRONG_CONFIDENCE = 0.7


@lru_cache(maxsize=1)
def _load_model_bundle(model_path: str) -> dict[str, Any]:
    """Incarca modelul ML o singura data, pentru a evita citiri repetate de pe disc."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Calibration ML model not found: {path}")
    bundle = joblib.load(path)
    required = {"pipeline", "numeric_features", "categorical_features"}
    missing = required - set(bundle.keys())
    if missing:
        raise ValueError(f"Calibration ML model is missing fields: {sorted(missing)}")
    return bundle


def _features_frame(rows: list[dict[str, Any]], bundle: dict[str, Any]) -> pd.DataFrame:
    """Construieste tabelul de feature-uri in aceeasi ordine ca la antrenarea modelului."""
    features = bundle["numeric_features"] + bundle["categorical_features"]
    return pd.DataFrame(
        [{feature: row.get(feature) for feature in features} for row in rows],
        columns=features,
    )


def _predict(bundle: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ruleaza predictia pentru label sau risc si ataseaza increderea modelului."""
    if not rows:
        return []

    pipeline = bundle["pipeline"]
    frame = _features_frame(rows, bundle)
    labels = pipeline.predict(frame)
    probabilities = pipeline.predict_proba(frame) if hasattr(pipeline, "predict_proba") else None
    classes = list(getattr(pipeline.named_steps["model"], "classes_", []))

    predictions: list[dict[str, Any]] = []
    for index, label in enumerate(labels):
        confidence = None
        if probabilities is not None and classes:
            class_index = classes.index(label)
            confidence = round(float(probabilities[index][class_index]), 4)
        predictions.append(
            {
                "label": str(label),
                "confidence": confidence,
            }
        )
    return predictions


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _map_prediction(item: dict[str, Any]) -> dict[str, Any] | None:
    prediction = item.get("ml_prediction")
    return prediction if isinstance(prediction, dict) else None


def _recommendation_ml_summary(category_maps: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rezuma predictiile ML pentru toate hartile care apartin unei recomandari."""
    label_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    flagged_maps: list[str] = []
    advisory_maps: list[str] = []
    max_label_confidence = 0.0
    max_risk_confidence = 0.0

    for item in category_maps:
        prediction = _map_prediction(item)
        if not prediction:
            continue

        label = str(prediction.get("label") or "unknown")
        risk = str(prediction.get("risk") or "unknown")
        label_confidence = _confidence(prediction.get("label_confidence"))
        risk_confidence = _confidence(prediction.get("risk_confidence"))
        max_label_confidence = max(max_label_confidence, label_confidence)
        max_risk_confidence = max(max_risk_confidence, risk_confidence)

        if label_confidence >= ADVISORY_CONFIDENCE:
            label_counts[label] += 1
        if risk_confidence >= ADVISORY_CONFIDENCE:
            risk_counts[risk] += 1

        map_name = str(item.get("name") or item.get("address_hex") or "Map")
        if (
            label == "bad_stage1_change"
            and label_confidence >= ADVISORY_CONFIDENCE
        ) or (
            risk == "high"
            and risk_confidence >= STRONG_CONFIDENCE
        ):
            flagged_maps.append(map_name)
        elif label_confidence >= STRONG_CONFIDENCE or risk_confidence >= STRONG_CONFIDENCE:
            advisory_maps.append(map_name)

    if not label_counts and not risk_counts and not flagged_maps and not advisory_maps:
        return None

    headline = "No strong concern was detected for this recommendation."
    severity = "info"
    if flagged_maps:
        severity = "warning"
        headline = "Possible risky Stage 1 patterns were detected in this area."
    elif risk_counts.get("medium-high", 0) or risk_counts.get("high", 0):
        severity = "caution"
        headline = "Extra validation is recommended for this area."
    elif label_counts:
        most_common_label = label_counts.most_common(1)[0][0]
        if most_common_label in {"good_stage1_change", "safe_supporting_change"}:
            headline = "This looks broadly consistent with reviewed Stage 1 examples."
        elif most_common_label in {"fuel_support_needed", "boost_support_needed", "afr_lambda_risk", "timing_risk"}:
            headline = "Supporting maps should be validated before further changes."

    return {
        "source": "ml_baseline",
        "model_version": "calibration-label-rf-v1",
        "severity": severity,
        "headline": headline,
        "label_counts": dict(label_counts),
        "risk_counts": dict(risk_counts),
        "flagged_maps": flagged_maps[:5],
        "advisory_maps": advisory_maps[:5],
        "max_label_confidence": round(max_label_confidence, 4),
        "max_risk_confidence": round(max_risk_confidence, 4),
        "thresholds": {
            "advisory": ADVISORY_CONFIDENCE,
            "strong": STRONG_CONFIDENCE,
        },
    }


def enrich_recommendations_with_ml_evidence(
    recommendations: list[dict[str, Any]],
    map_results: list[dict[str, Any]],
) -> None:
    """Adauga evidenta ML peste recomandarile deterministe, fara sa le inlocuiasca."""
    maps_by_category: dict[str, list[dict[str, Any]]] = {}
    for item in map_results:
        category = str(item.get("category") or "unknown")
        maps_by_category.setdefault(category, []).append(item)

    for recommendation in recommendations:
        category = str(recommendation.get("category") or "unknown")
        ml_evidence = _recommendation_ml_summary(maps_by_category.get(category, []))
        if not ml_evidence:
            continue
        recommendation["ml_evidence"] = ml_evidence

        observations = recommendation.setdefault("observations", [])
        if isinstance(observations, list):
            observations.append(ml_evidence["headline"])

        actions = recommendation.setdefault("actions", [])
        if isinstance(actions, list) and ml_evidence["severity"] in {"warning", "caution"}:
            actions.insert(0, "prioritize real-log validation for AI-flagged maps")

        current_priority = str(recommendation.get("priority") or "low")
        if ml_evidence["severity"] == "warning":
            recommendation["priority"] = "high"
            if current_priority != "high":
                recommendation["priority_score"] = max(
                    int(recommendation.get("priority_score") or 0),
                    85,
                )
        if ml_evidence["risk_counts"].get("high", 0):
            recommendation["risk"] = "high"
        elif (
            recommendation.get("risk") not in {"high", "medium-high"}
            and ml_evidence["risk_counts"].get("medium-high", 0)
        ):
            recommendation["risk"] = "medium-high"


def enrich_maps_with_ml_predictions(
    map_results: list[dict[str, Any]],
    ml_dataset: dict[str, Any],
) -> dict[str, Any]:
    """Ataseaza predictiile ML la fiecare harta si intoarce un rezumat global."""
    rows = [
        row for row in (ml_dataset.get("rows") or [])
        if isinstance(row, dict)
    ]
    if not rows:
        return {
            "available": False,
            "reason": "ML dataset has no rows.",
        }

    try:
        label_bundle = _load_model_bundle(str(LABEL_MODEL_PATH))
        risk_bundle = _load_model_bundle(str(RISK_MODEL_PATH))
        label_predictions = _predict(label_bundle, rows)
        risk_predictions = _predict(risk_bundle, rows)
    except Exception as exc:
        return {
            "available": False,
            "reason": str(exc),
        }

    label_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    bad_stage1_count = 0
    high_risk_count = 0
    low_confidence_count = 0

    for index, (row, label_prediction, risk_prediction) in enumerate(
        zip(rows, label_predictions, risk_predictions)
    ):
        prediction = {
            "label": label_prediction["label"],
            "label_confidence": label_prediction["confidence"],
            "risk": risk_prediction["label"],
            "risk_confidence": risk_prediction["confidence"],
            "model_version": "calibration-label-rf-v1",
            "source": "ml_baseline",
        }
        row["ml_prediction"] = prediction
        if index < len(map_results):
            map_results[index]["ml_prediction"] = prediction

        label_counts[prediction["label"]] += 1
        risk_counts[prediction["risk"]] += 1
        if prediction["label"] == "bad_stage1_change":
            bad_stage1_count += 1
        if prediction["risk"] == "high":
            high_risk_count += 1
        label_confidence = prediction.get("label_confidence")
        if isinstance(label_confidence, (int, float)) and label_confidence < 0.6:
            low_confidence_count += 1

    return {
        "available": True,
        "rows": len(rows),
        "attached_to_maps": min(len(rows), len(map_results)),
        "label_counts": dict(label_counts),
        "risk_counts": dict(risk_counts),
        "bad_stage1_count": bad_stage1_count,
        "high_risk_count": high_risk_count,
        "low_confidence_count": low_confidence_count,
        "model_version": "calibration-label-rf-v1",
        "notes": [
            "AI-assisted checks are advisory and do not replace rule-based recommendations.",
            "Low-confidence predictions should be reviewed by a tuner.",
        ],
    }
