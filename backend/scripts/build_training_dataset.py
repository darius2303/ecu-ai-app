from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = Path("generated/labeled_datasets")
DEFAULT_OUTPUT_PATH = Path("generated/training_dataset.csv")
DEFAULT_REPORT_PATH = Path("generated/training_dataset_report.json")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _reviewed_training_row(row: dict[str, str]) -> bool:
    return (
        str(row.get("review_status") or "").strip().lower() == "reviewed"
        and _truthy(row.get("include_for_training"))
        and bool(str(row.get("manual_label") or "").strip())
    )


def _read_rows(input_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    rows: list[dict[str, str]] = []
    files: list[dict[str, Any]] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            file_rows = []
            for row in reader:
                normalized = {key: value for key, value in row.items() if key}
                normalized["source_csv"] = csv_path.name
                file_rows.append(normalized)
        included = [row for row in file_rows if _reviewed_training_row(row)]
        rows.extend(included)
        files.append(
            {
                "file": csv_path.name,
                "rows": len(file_rows),
                "included": len(included),
                "rejected_or_unreviewed": len(file_rows) - len(included),
            }
        )
    return rows, files


def _fieldnames(rows: list[dict[str, str]]) -> list[str]:
    preferred = [
        "source_csv",
        "sample_id",
        "map_name",
        "map_category",
        "source_mode",
        "changed_percent",
        "max_abs_delta",
        "direction",
        "affected_rpm_min",
        "affected_rpm_max",
        "affected_load_min",
        "affected_load_max",
        "seed_label",
        "ml_confidence_seed",
        "recommendation_priority",
        "recommendation_risk",
        "manual_label",
        "manual_risk_label",
        "review_status",
        "include_for_training",
        "review_notes",
    ]
    all_fields = {key for row in rows for key in row.keys()}
    return preferred + sorted(all_fields - set(preferred))


def _write_training_dataset(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _counter(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key) or "unknown") for row in rows))


def _build_report(
    rows: list[dict[str, str]],
    files: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    label_counts = _counter(rows, "manual_label")
    risk_counts = _counter(rows, "manual_risk_label")
    category_counts = _counter(rows, "map_category")
    source_counts = _counter(rows, "source_csv")
    warnings: list[str] = []

    if not rows:
        warnings.append("No reviewed rows were included for training.")
    if label_counts:
        largest_label = max(label_counts.values())
        smallest_label = min(label_counts.values())
        if smallest_label > 0 and largest_label / smallest_label >= 8:
            warnings.append(
                "Dataset is label-imbalanced; consider collecting more samples for underrepresented labels."
            )
    if len(label_counts) < 3:
        warnings.append("Dataset has fewer than 3 label classes; model quality will be limited.")

    return {
        "output": str(output_path),
        "total_training_rows": len(rows),
        "files": files,
        "manual_label_counts": label_counts,
        "manual_risk_label_counts": risk_counts,
        "map_category_counts": category_counts,
        "source_csv_counts": source_counts,
        "warnings": warnings,
    }


def build_training_dataset(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    rows, files = _read_rows(input_dir)
    _write_training_dataset(rows, output_path)
    report = _build_report(rows, files, output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a training CSV from reviewed calibration labeling files."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    report = build_training_dataset(
        input_dir=args.input_dir,
        output_path=args.output,
        report_path=args.report,
    )
    print(f"Wrote {report['total_training_rows']} training rows to {args.output}")
    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
