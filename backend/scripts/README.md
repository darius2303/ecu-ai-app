# Dataset Scripts

Utilities for preparing reviewed calibration datasets for the ML baseline.

These scripts are for development/training only. They are not part of the final user-facing app workflow.

## Folder Layout

Generated and reviewed files live under:

```text
backend/generated/
```

Important subfolders:

```text
backend/generated/raw_datasets/      JSON feature datasets exported from real analyses
backend/generated/labeled_datasets/  Reviewed CSV files used for training
```

`backend/generated/` is ignored by git. Keep generated datasets local unless there is a deliberate reason to version a sanitized sample.

## Build Training Dataset

Put reviewed labeling CSV files in:

```text
backend/generated/labeled_datasets/
```

Then run from `backend`:

```powershell
python scripts/build_training_dataset.py
```

Outputs:

```text
backend/generated/training_dataset.csv
backend/generated/training_dataset_report.json
```

Only rows with all of these are included:

- `review_status = reviewed`
- `include_for_training = True`
- `manual_label` is not empty

Rows marked `rejected`, `unreviewed`, or without a manual label are ignored.

## Expected Review Fields

Each reviewed CSV should include the generated feature columns plus:

```text
manual_label
manual_risk_label
review_status
include_for_training
review_notes
```

Recommended `review_status` values:

```text
reviewed
rejected
unreviewed
```

## Training

After building the merged dataset, train the baseline from `backend`:

```powershell
python ml/train_calibration_label_model.py
```

See `backend/ml/README.md` for the model workflow.
