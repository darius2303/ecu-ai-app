# Dataset Scripts

## Build training dataset

Put reviewed labeling CSV files in:

```text
backend/generated/labeled_datasets/
```

Then run from the `backend` directory:

```bash
python scripts/build_training_dataset.py
```

The script writes:

```text
backend/generated/training_dataset.csv
backend/generated/training_dataset_report.json
```

Only rows with all of these are included:

- `review_status = reviewed`
- `include_for_training = True`
- `manual_label` is not empty

Rows marked `rejected`, `unreviewed`, or without a manual label are ignored.
