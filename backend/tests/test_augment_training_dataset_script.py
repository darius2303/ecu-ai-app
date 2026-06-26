import csv

from scripts.augment_training_dataset import augment_training_dataset


def test_augment_training_dataset_balances_labels_and_marks_synthetic_rows(tmp_path):
    input_path = tmp_path / "training.csv"
    rows = [
        {
            "source_csv": "sample.csv",
            "sample_id": "sample::0x10",
            "map_name": "Boost target",
            "map_category": "boost",
            "changed_percent": "10.0",
            "max_abs_delta": "2.0",
            "cell_count": "16",
            "changed_cells": "4",
            "manual_label": "boost_support_needed",
            "manual_risk_label": "medium-high",
            "review_status": "reviewed",
            "include_for_training": "True",
        },
        {
            "source_csv": "sample.csv",
            "sample_id": "sample::0x20",
            "map_name": "Torque request",
            "map_category": "torque",
            "changed_percent": "20.0",
            "max_abs_delta": "3.0",
            "cell_count": "16",
            "changed_cells": "6",
            "manual_label": "torque_increase",
            "manual_risk_label": "medium-high",
            "review_status": "reviewed",
            "include_for_training": "True",
        },
    ]
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    output_path = tmp_path / "augmented.csv"
    report = augment_training_dataset(
        input_path=input_path,
        output_path=output_path,
        report_path=tmp_path / "report.json",
        target_per_label=3,
        seed=7,
    )

    assert report["real_rows"] == 2
    assert report["augmented_rows"] == 4
    assert report["total_rows"] == 6
    assert report["label_counts_after"] == {
        "boost_support_needed": 3,
        "torque_increase": 3,
    }

    with output_path.open("r", newline="", encoding="utf-8") as handle:
        output_rows = list(csv.DictReader(handle))

    augmented = [row for row in output_rows if row["is_augmented"] == "True"]
    real = [row for row in output_rows if row["is_augmented"] == "False"]
    assert len(real) == 2
    assert len(augmented) == 4
    assert all(row["augmentation_source_sample_id"] for row in augmented)
    assert all(row["augmentation_method"] == "label_balanced_numeric_jitter" for row in augmented)
    assert any(row["changed_percent"] != "10.0" for row in augmented)
