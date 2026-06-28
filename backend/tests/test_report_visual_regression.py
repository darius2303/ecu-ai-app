from __future__ import annotations

from datetime import datetime
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageChops

from app.services import report_generator
from app.services.report_generator import generate_calibration_report


EXPECTED_PAGE_SIGNATURES = [
    {
        "dhash": "c990c9c4c584c180c120c080d000c010c624c420c480c7c4e0e0f0700000c820",
        "nonwhite_ratio": 0.1134,
        "colorful_ratio": 0.0174,
        "dark_ratio": 0.0632,
        "bbox": (0.068, 0.059, 0.932, 0.976),
    },
    {
        "dhash": "d000c000d002d502c582d222d002c482c180d002c082c580104000000000c800",
        "nonwhite_ratio": 0.048,
        "colorful_ratio": 0.0149,
        "dark_ratio": 0.0029,
        "bbox": (0.068, 0.048, 0.932, 0.976),
    },
    {
        "dhash": "c000c138c690c000d004d644000000000000000000000000000000000000c800",
        "nonwhite_ratio": 0.0396,
        "colorful_ratio": 0.0101,
        "dark_ratio": 0.0178,
        "bbox": (0.068, 0.048, 0.932, 0.976),
    },
]


class _FixedDatetime:
    @classmethod
    def now(cls):
        return datetime(2026, 1, 2, 10, 30)


def _surface(base: float, step: float) -> list[list[float]]:
    return [
        [
            round(base + row * step + column * step * 0.65 + ((row - 2) ** 2) * 0.35, 2)
            for column in range(6)
        ]
        for row in range(6)
    ]


def _visual_regression_analysis() -> dict:
    verdict = {
        "title": "Needs validation",
        "message": (
            "The tune has meaningful changes and supporting maps should be checked "
            "before treating it as coherent."
        ),
        "next_step": (
            "Use Focus maps on the high-priority recommendations and verify affected "
            "zones in logs."
        ),
    }
    return {
        "summary": {
            "original_file": "visual-original.bin",
            "modified_file": "visual-stage1.bin",
            "original_size": 65536,
            "modified_size": 65536,
            "definitions_count": 5,
            "maps_extracted": 5,
            "maps_changed": 4,
        },
        "binary_diff": {
            "changed_percent": 7.42,
            "changed_bytes": 4864,
        },
        "analysis_verdict": verdict,
        "maps": [
            {
                "name": "Torque request surface",
                "category": "torque",
                "address_hex": "0x1000",
                "modified_surface_preview": _surface(20, 4.2),
                "diff": {"changed_percent": 62.5, "max_abs_delta": 18.4},
                "affected_zone": [
                    {"label": "RPM", "min": 3200, "max": 7200},
                    {"label": "Load", "min": 70, "max": 100},
                ],
            },
            {
                "name": "Boost target surface",
                "category": "boost",
                "address_hex": "0x1800",
                "modified_surface_preview": _surface(110, 6.8),
                "diff": {"changed_percent": 48.0, "max_abs_delta": 12.7},
                "affected_zone": [
                    {"label": "RPM", "min": 3600, "max": 6800},
                    {"label": "MAP", "min": 120, "max": 240},
                ],
            },
            {
                "name": "Injection base map",
                "category": "fuel",
                "address_hex": "0x2000",
                "modified_surface_preview": _surface(8, 1.2),
                "diff": {"changed_percent": 33.0, "max_abs_delta": 4.5},
                "affected_zone": [
                    {"label": "RPM", "min": 2800, "max": 6500},
                ],
            },
        ],
        "report": {
            "headline": "4864 bytes changed (7.42%).",
            "tuner_summary": [
                "Changes are concentrated in: torque, boost, fuel.",
                "High priority: Torque request / torque limiters, Boost target validation.",
            ],
            "recommended_actions": [
                {
                    "category": "torque",
                    "title": "Torque request / torque limiters",
                    "priority": "high",
                    "risk": "medium-high",
                    "reason": (
                        "Torque maps changed in high-load areas and must be checked "
                        "with drivetrain protections."
                    ),
                    "target_zone": "RPM 3200-7200, Load 70-100%",
                    "suggested_change": "Validate requested torque against fuel and boost support.",
                    "actions": [
                        "compare requested torque with logged delivered torque",
                        "verify limiter coherence",
                    ],
                    "risks": [
                        "drivetrain overload",
                        "excessive EGT under sustained load",
                    ],
                    "ml_evidence": {
                        "headline": "Extra validation is recommended for this area.",
                        "flagged_maps": ["Torque request surface"],
                    },
                },
                {
                    "category": "boost",
                    "title": "Boost target validation",
                    "priority": "high",
                    "risk": "medium-high",
                    "reason": (
                        "Boost target changes require pressure limiter and turbo control "
                        "validation."
                    ),
                    "target_zone": "RPM 3600-6800, MAP 120-240 kPa",
                    "suggested_change": "Check boost target against pressure limiters.",
                    "actions": [
                        "compare requested and actual boost",
                        "check overboost protection",
                    ],
                    "risks": [
                        "compressor overspeed",
                        "thermal stress",
                    ],
                },
                {
                    "category": "fuel",
                    "title": "Fuel quantity / injection duration",
                    "priority": "medium",
                    "risk": "medium",
                    "reason": "Fuel map changes should be validated against lambda and smoke limits.",
                    "target_zone": "Mid-to-high load cells",
                    "suggested_change": "Validate AFR/lambda and EGT in logs.",
                    "actions": [
                        "review lambda trend",
                        "check injector duty margin",
                    ],
                    "risks": [
                        "rich smoke",
                        "high exhaust temperature",
                    ],
                },
            ],
            "top_changes": [
                {
                    "name": "Torque request surface",
                    "category": "torque",
                    "changed_percent": 62.5,
                    "max_abs_delta": 18.4,
                    "zone_text": "RPM 3200-7200",
                },
                {
                    "name": "Boost target surface",
                    "category": "boost",
                    "changed_percent": 48.0,
                    "max_abs_delta": 12.7,
                    "zone_text": "MAP 120-240",
                },
                {
                    "name": "Injection base map",
                    "category": "fuel",
                    "changed_percent": 33.0,
                    "max_abs_delta": 4.5,
                    "zone_text": "RPM 2800-6500",
                },
            ],
            "validation_checks": [
                "Compare logs against modified RPM/load zones.",
                "Check AFR/lambda, EGT and knock/noise.",
                "Confirm limiters remain coherent.",
            ],
            "verdict": verdict,
        },
    }


def _render_pdf_pages(pdf_path: Path) -> list[Image.Image]:
    document = fitz.open(pdf_path)
    try:
        images: list[Image.Image] = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            images.append(
                Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            )
        return images
    finally:
        document.close()


def _pdf_text(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in document)
    finally:
        document.close()


def _dhash(image: Image.Image, size: int = 16) -> str:
    gray = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixel_grid = np.asarray(gray)
    bits = (pixel_grid[:, :-1] > pixel_grid[:, 1:]).astype(np.uint8).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:0{size * size // 4}x}"


def _hamming_distance(left: str, right: str) -> int:
    return bin(int(left, 16) ^ int(right, 16)).count("1")


def _image_signature(image: Image.Image) -> dict:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixel_grid = np.asarray(rgb)
    total = width * height
    channel_max = pixel_grid.max(axis=2)
    channel_min = pixel_grid.min(axis=2)
    nonwhite = int((((255 - pixel_grid).min(axis=2) > 12) | (channel_max < 242)).sum())
    colorful = int(((channel_max - channel_min) > 45).sum())
    dark = int((channel_max < 80).sum())
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
    bbox = difference.getbbox()
    return {
        "dhash": _dhash(rgb),
        "nonwhite_ratio": round(nonwhite / total, 4),
        "colorful_ratio": round(colorful / total, 4),
        "dark_ratio": round(dark / total, 4),
        "bbox": tuple(
            round(value / (width if index % 2 == 0 else height), 3)
            for index, value in enumerate(bbox or (0, 0, 0, 0))
        ),
    }


def _assert_signature_close(actual: dict, expected: dict) -> None:
    assert _hamming_distance(actual["dhash"], expected["dhash"]) <= 18
    assert abs(actual["nonwhite_ratio"] - expected["nonwhite_ratio"]) <= 0.012
    assert abs(actual["colorful_ratio"] - expected["colorful_ratio"]) <= 0.006
    assert abs(actual["dark_ratio"] - expected["dark_ratio"]) <= 0.01
    assert all(
        abs(actual_value - expected_value) <= 0.015
        for actual_value, expected_value in zip(actual["bbox"], expected["bbox"])
    )


def _crop_signature(image: Image.Image, box: tuple[int, int, int, int]) -> dict:
    return _image_signature(image.crop(box))


def test_pdf_report_visual_regression_including_3d_surfaces(tmp_path, monkeypatch):
    monkeypatch.setattr(report_generator, "datetime", _FixedDatetime)
    pdf_path = tmp_path / "visual_regression_report.pdf"

    generate_calibration_report(
        analysis=_visual_regression_analysis(),
        output_path=pdf_path,
    )

    text = _pdf_text(pdf_path)
    assert "Visual Map Highlights" in text
    assert "Torque request surface" in text
    assert "Boost target surface" in text
    assert "Priority Recommendations" in text

    page_images = _render_pdf_pages(pdf_path)
    assert len(page_images) == 3

    for image, expected in zip(page_images, EXPECTED_PAGE_SIGNATURES):
        _assert_signature_close(_image_signature(image), expected)

    first_page_surface_area = _crop_signature(page_images[0], (50, 430, 845, 760))
    assert first_page_surface_area["nonwhite_ratio"] >= 0.07
    assert first_page_surface_area["colorful_ratio"] >= 0.012
