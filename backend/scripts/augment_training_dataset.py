from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("generated/training_dataset.csv")
DEFAULT_OUTPUT_PATH = Path("generated/training_dataset_augmented.csv")
DEFAULT_REPORT_PATH = Path("generated/training_dataset_augmented_report.json")

NUMERIC_COLUMNS = {
    "changed_percent": {"min": 0.0, "max": 100.0, "relative": 0.04, "absolute": 0.25},
    "max_abs_delta": {"min": 0.0, "max": None, "relative": 0.06, "absolute": 0.05},
    "mean_delta": {"min": None, "max": None, "relative": 0.06, "absolute": 0.05},
    "affected_rpm_min": {"min": 0.0, "max": None, "relative": 0.015, "absolute": 25.0},
    "affected_rpm_max": {"min": 0.0, "max": None, "relative": 0.015, "absolute": 25.0},
    "affected_load_min": {"min": 0.0, "max": None, "relative": 0.02, "absolute": 0.5},
    "affected_load_max": {"min": 0.0, "max": None, "relative": 0.02, "absolute": 0.5},
    "ml_confidence_seed": {"min": 0.0, "max": 0.95, "relative": 0.03, "absolute": 0.01},
    "original_min": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
    "original_max": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
    "original_mean": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
    "modified_min": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
    "modified_max": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
    "modified_mean": {"min": None, "max": None, "relative": 0.015, "absolute": 0.05},
}

INTEGER_COLUMNS = {"changed_cells"}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _training_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if str(row.get("review_status") or "").strip().lower() == "reviewed"
        and _truthy(row.get("include_for_training"))
        and str(row.get("manual_label") or "").strip()
    ]


def _float_value(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_number(value: float, template: str) -> str:
    if "." not in str(template):
        return str(int(round(value)))
    return str(round(value, 6)).rstrip("0").rstrip(".")


def _jitter_numeric(value: str, config: dict[str, float | None], rng: random.Random) -> str:
    parsed = _float_value(value)
    if parsed is None:
        return value

    relative = float(config.get("relative") or 0.0)
    absolute = float(config.get("absolute") or 0.0)
    scale = max(abs(parsed) * relative, absolute)
    augmented = parsed + rng.uniform(-scale, scale)

    minimum = config.get("min")
    maximum = config.get("max")
    if minimum is not None:
        augmented = max(float(minimum), augmented)
    if maximum is not None:
        augmented = min(float(maximum), augmented)
    return _format_number(augmented, value)


def _jitter_integer(value: str, row: dict[str, str], rng: random.Random) -> str:
    parsed = _float_value(value)
    if parsed is None:
        return value
    cell_count = _float_value(row.get("cell_count"))
    upper = int(cell_count) if cell_count is not None and cell_count > 0 else None
    delta = rng.choice([-1, 0, 1])
    augmented = max(0, int(round(parsed)) + delta)
    if upper is not None:
        augmented = min(upper, augmented)
    return str(augmented)


def _augment_row(row: dict[str, str], index: int, rng: random.Random) -> dict[str, str]:
    augmented = dict(row)
    source_sample_id = row.get("sample_id") or f"row-{index}"
    augmented["sample_id"] = f"{source_sample_id}::aug{index:04d}"
    augmented["source_csv"] = f"augmented::{row.get('source_csv') or 'unknown'}"
    augmented["is_augmented"] = "True"
    augmented["augmentation_source_sample_id"] = source_sample_id
    augmented["augmentation_index"] = str(index)
    augmented["augmentation_method"] = "label_balanced_numeric_jitter"

    for column, config in NUMERIC_COLUMNS.items():
        if column in augmented:
            augmented[column] = _jitter_numeric(augmented[column], config, rng)
    for column in INTEGER_COLUMNS:
        if column in augmented:
            augmented[column] = _jitter_integer(augmented[column], row, rng)
    return augmented


def _fieldnames(rows: list[dict[str, str]]) -> list[str]:
    preferred = [
        "source_csv",
        "sample_id",
        "is_augmented",
        "augmentation_source_sample_id",
        "augmentation_index",
        "augmentation_method",
        "map_name",
        "map_category",
        "source_mode",
        "changed_percent",
        "max_abs_delta",
        "direction",
        "manual_label",
        "manual_risk_label",
        "review_status",
        "include_for_training",
    ]
    all_fields = {key for row in rows for key in row.keys()}
    return preferred + sorted(all_fields - set(preferred))


def _counts(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key) or "unknown") for row in rows))


def augment_training_dataset(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    target_per_label: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    rows = _training_rows(_load_rows(input_path))
    if not rows:
        raise ValueError("No reviewed training rows found.")

    rng = random.Random(seed)
    rows_by_label: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        label = str(row.get("manual_label") or "unknown")
        rows_by_label.setdefault(label, []).append(row)

    output_rows = []
    for row in rows:
        original = dict(row)
        original["is_augmented"] = "False"
        original["augmentation_source_sample_id"] = ""
        original["augmentation_index"] = ""
        original["augmentation_method"] = "real_reviewed_row"
        output_rows.append(original)

    augmented_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    for label, label_rows in sorted(rows_by_label.items()):
        needed = max(0, target_per_label - len(label_rows))
        if needed == 0:
            continue
        if len(label_rows) < 5:
            warnings.append(
                f"Label {label} has only {len(label_rows)} real row(s); augmented samples should be treated as weak evidence."
            )
        for offset in range(needed):
            source = rng.choice(label_rows)
            augmented_rows.append(_augment_row(source, len(augmented_rows) + 1, rng))

    output_rows.extend(augmented_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(output_rows)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    report = {
        "input": str(input_path),
        "output": str(output_path),
        "target_per_label": target_per_label,
        "seed": seed,
        "real_rows": len(rows),
        "augmented_rows": len(augmented_rows),
        "total_rows": len(output_rows),
        "label_counts_before": _counts(rows, "manual_label"),
        "label_counts_after": _counts(output_rows, "manual_label"),
        "risk_counts_after": _counts(output_rows, "manual_risk_label"),
        "warnings": warnings,
        "notes": [
            "Augmented rows are generated from reviewed rows using small numeric perturbations.",
            "They increase ML training volume but do not replace additional real ECU/map-pack samples.",
            "Use the original training_dataset.csv as the evidence dataset in documentation; use this file only for ML experiments.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a label-balanced augmented calibration training dataset."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--target-per-label", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = augment_training_dataset(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        target_per_label=args.target_per_label,
        seed=args.seed,
    )
    print(
        f"Wrote {report['total_rows']} rows "
        f"({report['real_rows']} real + {report['augmented_rows']} augmented) "
        f"to {args.output}"
    )
    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
