from app.services import calibration_ml


class _FakeModel:
    def __init__(self, classes):
        self.classes_ = classes


class _FakePipeline:
    def __init__(self, label: str, confidence: float, classes: list[str]):
        self.label = label
        self.confidence = confidence
        self.named_steps = {"model": _FakeModel(classes)}

    def predict(self, frame):
        return [self.label for _ in range(len(frame))]

    def predict_proba(self, frame):
        rows = []
        for _ in range(len(frame)):
            probabilities = [0.0 for _ in self.named_steps["model"].classes_]
            probabilities[self.named_steps["model"].classes_.index(self.label)] = self.confidence
            rows.append(probabilities)
        return rows


def _bundle(label: str, confidence: float, classes: list[str]):
    return {
        "pipeline": _FakePipeline(label, confidence, classes),
        "numeric_features": ["changed_percent"],
        "categorical_features": ["map_category"],
    }


def test_enrich_maps_with_ml_predictions_attaches_labels_and_summary(monkeypatch):
    def fake_load_model_bundle(path: str):
        if "risk" in path:
            return _bundle("high", 0.92, ["low", "medium", "medium-high", "high"])
        return _bundle(
            "bad_stage1_change",
            0.88,
            ["bad_stage1_change", "good_stage1_change"],
        )

    monkeypatch.setattr(calibration_ml, "_load_model_bundle", fake_load_model_bundle)
    map_results = [{"name": "Torque request", "category": "torque"}]
    ml_dataset = {
        "rows": [
            {
                "map_category": "torque",
                "changed_percent": 60,
            }
        ]
    }

    summary = calibration_ml.enrich_maps_with_ml_predictions(map_results, ml_dataset)

    assert summary["available"] is True
    assert summary["attached_to_maps"] == 1
    assert summary["bad_stage1_count"] == 1
    assert summary["high_risk_count"] == 1
    assert map_results[0]["ml_prediction"] == {
        "label": "bad_stage1_change",
        "label_confidence": 0.88,
        "risk": "high",
        "risk_confidence": 0.92,
        "model_version": "calibration-label-rf-v1",
        "source": "ml_baseline",
    }


def test_enrich_recommendations_with_ml_evidence_escalates_priority_and_risk():
    recommendations = [
        {
            "category": "torque",
            "priority": "medium",
            "risk": "medium",
            "actions": ["compare with logs"],
            "observations": [],
        }
    ]
    map_results = [
        {
            "name": "Torque request",
            "category": "torque",
            "ml_prediction": {
                "label": "bad_stage1_change",
                "label_confidence": 0.91,
                "risk": "high",
                "risk_confidence": 0.9,
            },
        }
    ]

    calibration_ml.enrich_recommendations_with_ml_evidence(recommendations, map_results)

    recommendation = recommendations[0]
    assert recommendation["priority"] == "high"
    assert recommendation["risk"] == "high"
    assert recommendation["ml_evidence"]["severity"] == "warning"
    assert recommendation["ml_evidence"]["flagged_maps"] == ["Torque request"]
    assert recommendation["actions"][0] == "prioritize real-log validation for AI-flagged maps"


def test_enrich_maps_with_ml_predictions_reports_empty_dataset():
    summary = calibration_ml.enrich_maps_with_ml_predictions([], {"rows": []})

    assert summary == {
        "available": False,
        "reason": "ML dataset has no rows.",
    }
