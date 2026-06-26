import csv

from scripts.build_training_dataset import build_training_dataset


def test_build_training_dataset_reports_rare_labels_and_quality_targets(tmp_path):
    input_dir = tmp_path / "labeled"
    input_dir.mkdir()
    csv_path = input_dir / "sample.csv"
    rows = [
        {
            "sample_id": "sample::0x10",
            "map_name": "Boost target",
            "map_category": "boost",
            "manual_label": "boost_support_needed",
            "manual_risk_label": "medium-high",
            "review_status": "reviewed",
            "include_for_training": "True",
        },
        {
            "sample_id": "sample::0x20",
            "map_name": "Torque request",
            "map_category": "torque",
            "manual_label": "torque_increase",
            "manual_risk_label": "medium-high",
            "review_status": "reviewed",
            "include_for_training": "True",
        },
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    report = build_training_dataset(
        input_dir=input_dir,
        output_path=tmp_path / "training.csv",
        report_path=tmp_path / "report.json",
    )

    assert report["total_training_rows"] == 2
    assert report["manual_label_counts"]["boost_support_needed"] == 1
    assert report["rare_manual_labels"]["boost_support_needed"] == 1
    assert report["label_by_category"]["boost"]["boost_support_needed"] == 1
    assert report["quality_targets"]["minimum_rows_per_important_label"] == 15
    assert any(
        item["manual_label"] == "boost_support_needed"
        for item in report["recommended_next_samples"]
    )
