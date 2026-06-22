# Calibration ML Baseline

This folder contains the map-level ML baseline used by the backend as an AI-assisted second opinion.

The model does not replace the rule-based recommendation engine. It adds advisory evidence such as possible risky Stage 1 patterns, supporting-map validation needs, and map-level risk labels.

## Runtime Artifacts

The runtime artifacts are stored in:

```text
backend/ml/artifacts/calibration_labels/
```

Expected files:

```text
calibration_label_model.joblib
calibration_risk_model.joblib
training_metrics.json
```

The backend loads them from:

```text
backend/app/services/calibration_ml.py
```

At runtime, predictions are attached to extracted maps as `ml_prediction`, aggregated into `ml_summary`, and summarized into recommendation-level `ml_evidence`.

## Build Training Dataset

Reviewed labeling CSV files should be placed in:

```text
backend/generated/labeled_datasets/
```

Then run from `backend`:

```powershell
python scripts/build_training_dataset.py
```

Outputs:

```text
generated/training_dataset.csv
generated/training_dataset_report.json
```

`backend/generated/` is ignored by git. Do not commit local generated datasets.

## Train Baseline Classifiers

Run from `backend`:

```powershell
python ml/train_calibration_label_model.py
```

This trains two Random Forest classifiers:

- `manual_label` -> calibration label prediction
- `manual_risk_label` -> risk prediction

Outputs:

```text
ml/artifacts/calibration_labels/calibration_label_model.joblib
ml/artifacts/calibration_labels/calibration_risk_model.joblib
ml/artifacts/calibration_labels/training_metrics.json
```

## Predict Labels for a Raw Dataset

Run from `backend`:

```powershell
python ml/predict_calibration_labels.py `
  --dataset generated/raw_datasets/can_am_renegade_1000r_stage1.json `
  --output-csv generated/ml_predictions_renegade.csv `
  --output-json generated/ml_predictions_renegade.json
```

## Label Scope

Current labels include examples such as:

- `good_stage1_change`
- `bad_stage1_change`
- `torque_increase`
- `fuel_support_needed`
- `boost_support_needed`
- `afr_lambda_risk`
- `timing_risk`
- `risky_limiter_change`
- `safe_supporting_change`
- `not_power_related`

## Safety

Predictions are decision-support only. They should not automatically approve or reject tuning changes. Always validate with real logs, hardware limits, thermal behavior, drivetrain limits, AFR/lambda, EGT, and knock/noise checks.
