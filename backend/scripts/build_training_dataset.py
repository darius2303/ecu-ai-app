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
MIN_RECOMMENDED_CLASS_ROWS = 15

LABEL_OPTIONS = [
    "bad_stage1_change",
    "good_stage1_change",
    "safe_supporting_change",
    "risky_limiter_change",
    "torque_increase",
    "fuel_support_needed",
    "boost_support_needed",
    "afr_lambda_risk",
    "timing_risk",
    "not_power_related",
    "unknown",
]

RISK_LABEL_OPTIONS = [
    "low",
    "medium",
    "medium-high",
    "high",
    "unknown",
]


def _truthy(value: str | None) -> bool:
    """Converteste valori text din CSV in bool pentru coloanele de selectie."""
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _reviewed_training_row(row: dict[str, str]) -> bool:
    """Verifica daca un rand a fost revizuit si poate intra in training."""
    return (
        str(row.get("review_status") or "").strip().lower() == "reviewed"
        and _truthy(row.get("include_for_training"))
        and bool(str(row.get("manual_label") or "").strip())
    )


def _read_rows(input_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Citeste toate CSV-urile etichetate si pastreaza doar randurile acceptate."""
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
    """Pastreaza coloanele importante la inceputul fisierului rezultat."""
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
    """Scrie datasetul final intr-un CSV folosit la antrenarea modelelor."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _counter(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    """Numara valorile unei coloane pentru raportul de calitate."""
    return dict(Counter(str(row.get(key) or "unknown") for row in rows))


def _nested_counter(rows: list[dict[str, str]], outer: str, inner: str) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = {}
    for row in rows:
        outer_value = str(row.get(outer) or "unknown")
        inner_value = str(row.get(inner) or "unknown")
        matrix.setdefault(outer_value, Counter())[inner_value] += 1
    return {
        key: dict(counter)
        for key, counter in sorted(matrix.items())
    }


def _rare_counts(counts: dict[str, int], minimum: int) -> dict[str, int]:
    return {
        key: value
        for key, value in sorted(counts.items(), key=lambda item: (item[1], item[0]))
        if value < minimum
    }


def _unknown_values(rows: list[dict[str, str]], key: str, allowed: set[str]) -> dict[str, int]:
    values = Counter(
        str(row.get(key) or "").strip()
        for row in rows
        if str(row.get(key) or "").strip() and str(row.get(key) or "").strip() not in allowed
    )
    return dict(values)


def _collection_targets(label_counts: dict[str, int]) -> list[dict[str, Any]]:
    """Propune clasele pentru care ar trebui colectate mai multe exemple reale."""
    targets = []
    important_labels = [
        "bad_stage1_change",
        "boost_support_needed",
        "safe_supporting_change",
        "not_power_related",
        "timing_risk",
        "afr_lambda_risk",
        "fuel_support_needed",
    ]
    for label in important_labels:
        current = int(label_counts.get(label, 0))
        if current >= MIN_RECOMMENDED_CLASS_ROWS:
            continue
        targets.append(
            {
                "manual_label": label,
                "current_rows": current,
                "target_rows": MIN_RECOMMENDED_CLASS_ROWS,
                "needed_rows": MIN_RECOMMENDED_CLASS_ROWS - current,
            }
        )
    return targets


def _build_report(
    rows: list[dict[str, str]],
    files: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    """Construieste raportul JSON cu distributii, avertismente si tinte de colectare."""
    label_counts = _counter(rows, "manual_label")
    risk_counts = _counter(rows, "manual_risk_label")
    category_counts = _counter(rows, "map_category")
    source_counts = _counter(rows, "source_csv")
    rare_labels = _rare_counts(label_counts, MIN_RECOMMENDED_CLASS_ROWS)
    rare_categories = _rare_counts(category_counts, MIN_RECOMMENDED_CLASS_ROWS)
    invalid_labels = _unknown_values(rows, "manual_label", set(LABEL_OPTIONS))
    invalid_risk_labels = _unknown_values(rows, "manual_risk_label", set(RISK_LABEL_OPTIONS))
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
    if rare_labels:
        warnings.append(
            "Some labels have fewer than "
            f"{MIN_RECOMMENDED_CLASS_ROWS} reviewed rows; collect more examples for these classes."
        )
    if invalid_labels:
        warnings.append("Dataset contains manual labels outside the approved label schema.")
    if invalid_risk_labels:
        warnings.append("Dataset contains risk labels outside the approved risk schema.")
    if source_counts:
        top_source, top_count = max(source_counts.items(), key=lambda item: item[1])
        if len(rows) and top_count / len(rows) >= 0.30:
            warnings.append(
                f"Source {top_source} contributes {round((top_count / len(rows)) * 100, 2)}% "
                "of the dataset; add more vehicles/ECUs to reduce source dominance."
            )

    return {
        "output": str(output_path),
        "total_training_rows": len(rows),
        "files": files,
        "manual_label_counts": label_counts,
        "manual_risk_label_counts": risk_counts,
        "map_category_counts": category_counts,
        "source_csv_counts": source_counts,
        "rare_manual_labels": rare_labels,
        "rare_map_categories": rare_categories,
        "invalid_manual_labels": invalid_labels,
        "invalid_manual_risk_labels": invalid_risk_labels,
        "label_by_category": _nested_counter(rows, "map_category", "manual_label"),
        "risk_by_label": _nested_counter(rows, "manual_label", "manual_risk_label"),
        "recommended_next_samples": _collection_targets(label_counts),
        "quality_targets": {
            "minimum_rows_per_important_label": MIN_RECOMMENDED_CLASS_ROWS,
            "note": "Targets are curation goals, not hard requirements for running the prototype.",
        },
        "warnings": warnings,
    }


def build_training_dataset(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Orchestreaza citirea fisierelor etichetate, exportul CSV si raportul JSON."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    rows, files = _read_rows(input_dir)
    _write_training_dataset(rows, output_path)
    report = _build_report(rows, files, output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    """Entry point CLI pentru rularea scriptului din terminal."""
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
