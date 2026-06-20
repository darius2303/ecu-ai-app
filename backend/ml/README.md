# Calibration ML Baseline

This folder contains the first ML baseline trained from reviewed calibration
labeling CSV files.

## 1. Build the training dataset

Run from `backend`:

```bash
python scripts/build_training_dataset.py
```

This creates:

```text
generated/training_dataset.csv
generated/training_dataset_report.json
```

## 2. Train baseline classifiers

Run from `backend`:

```bash
python ml/train_calibration_label_model.py
```

This creates:

```text
ml/artifacts/calibration_labels/calibration_label_model.joblib
ml/artifacts/calibration_labels/calibration_risk_model.joblib
ml/artifacts/calibration_labels/training_metrics.json
```

The current model is a baseline. High accuracy is expected because the dataset
is still small and many labels come from consistent review rules.

## 3. Predict labels for a raw dataset

Run from `backend`:

```bash
python ml/predict_calibration_labels.py ^
  --dataset generated/raw_datasets/can_am_renegade_1000r_stage1.json ^
  --output-csv generated/ml_predictions_renegade.csv ^
  --output-json generated/ml_predictions_renegade.json
```

Predictions are decision-support only. They should not automatically decide
tuning changes without tuner review and log validation.

## Runtime integration

The backend analysis flow loads these artifacts through:

```text
backend/app/services/calibration_ml.py
```

Predictions are attached to map results as `ml_prediction` and summarized in
`ml_summary`. Rule-based recommendations remain the primary decision layer; ML
is used only as a second opinion.
