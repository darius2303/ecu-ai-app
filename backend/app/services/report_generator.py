from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas


def _draw_section_title(c: canvas.Canvas, title: str, x: float, y: float):
    c.setFillColor(colors.HexColor("#1F4E79"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y, title)
    c.setStrokeColor(colors.HexColor("#1F4E79"))
    c.setLineWidth(1.2)
    c.line(x, y - 3, x + 180, y - 3)


def _format_value(value):
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _draw_key_value_block(
    c: canvas.Canvas,
    data: dict,
    x: float,
    y: float,
    label_width: float = 210,
    line_height: float = 18
):
    c.setFillColor(colors.black)
    current_y = y

    for key, value in data.items():
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, current_y, f"{key}:")

        c.setFont("Helvetica", 10)
        c.drawString(x + label_width, current_y, _format_value(value))

        current_y -= line_height

    return current_y


def _draw_summary(c: canvas.Canvas, text: str, x: float, y: float, width: float):
    styles = getSampleStyleSheet()
    style = styles["BodyText"]
    style.fontName = "Helvetica"
    style.fontSize = 10
    style.leading = 14
    style.spaceAfter = 0
    style.spaceBefore = 0

    paragraph = Paragraph(text, style)
    w, h = paragraph.wrap(width, 200)
    paragraph.drawOn(c, x, y - h)
    return y - h


def generate_stage1_report(
    input_data: dict,
    analysis: dict,
    heatmap_path: str | Path,
    output_path: str | Path
) -> str:
    output_path = str(output_path)
    heatmap_path = str(heatmap_path)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    margin_x = 50
    content_width = width - 2 * margin_x
    y = height - 50

    # ===== Header =====
    c.setFillColor(colors.HexColor("#1F1F1F"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, "ECU Stage 1 Analysis Report")

    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(margin_x, y - 18, f"Generated on: {generated_at}")

    y -= 45

    # ===== Intro box =====
    c.setFillColor(colors.HexColor("#F4F6F8"))
    c.roundRect(margin_x, y - 45, content_width, 42, 8, stroke=0, fill=1)

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(
        margin_x + 10,
        y - 18,
        "This report provides an estimated Stage 1 tuning assessment based on ECU/OBD parameters."
    )
    c.drawString(
        margin_x + 10,
        y - 32,
        "The output is intended for analysis and decision support, not for direct ECU flashing."
    )

    y -= 65

    # ===== Input section =====
    _draw_section_title(c, "Input Data", margin_x, y)
    y -= 22

    derived = analysis.get("derived_features") or {}

    input_labels = {
        "RPM": input_data.get("rpm") or derived.get("rpm"),
        "Boost Pressure": input_data.get("boost_pressure") or derived.get("boost_pressure"),
        "Injection Quantity": input_data.get("injection_quantity") or derived.get("injection_quantity"),
        "AFR": input_data.get("afr") or derived.get("afr"),
        "Engine Displacement (L)": input_data.get("engine_displacement"),
        "Fuel Type": input_data.get("fuel_type"),
        "Turbo": input_data.get("is_turbo"),
        "Stock HP": input_data.get("stock_hp"),
    }

    if derived:
        input_labels.update({
            "Calibration Map": f"{derived.get('rows')}x{derived.get('columns')} {derived.get('map_type')}",
            "Map Value Range": f"{derived.get('min_value')} .. {derived.get('max_value')}",
            "High Load Mean": derived.get("high_load_mean"),
        })

    y = _draw_key_value_block(c, input_labels, margin_x, y)
    y -= 8

    # ===== Analysis section =====
    _draw_section_title(c, "Analysis Result", margin_x, y)
    y -= 22

    analysis_labels = {
        "Estimated Stage 1 Gain (%)": analysis.get("stage1_gain_percent"),
        "Potential Class": analysis.get("potential_class"),
        "Estimated HP After Stage 1": analysis.get("estimated_hp_after_stage1"),
    }

    y = _draw_key_value_block(c, analysis_labels, margin_x, y)
    y -= 14

    # ===== Interpretation =====
    _draw_section_title(c, "Interpretation", margin_x, y)
    y -= 20

    gain = analysis.get("stage1_gain_percent")
    potential = analysis.get("potential_class")
    est_hp = analysis.get("estimated_hp_after_stage1")

    summary_parts = [
        f"The model estimates a Stage 1 gain of <b>{_format_value(gain)}%</b>, ",
        f"which places this configuration in the <b>{_format_value(potential)}</b> potential category. "
    ]

    if est_hp is not None:
        summary_parts.append(
            f"Based on the provided stock power value, the estimated output after Stage 1 is <b>{_format_value(est_hp)} HP</b>. "
        )

    summary_parts.append(
        "The generated fuel map below is indicative and is intended to support interpretation of the result."
    )

    summary_text = "".join(summary_parts)
    y = _draw_summary(c, summary_text, margin_x, y, content_width)
    y -= 22

    # ===== Heatmap =====
    if Path(heatmap_path).exists():
        _draw_section_title(c, "Fuel Map Heatmap", margin_x, y)
        y -= 18

        image = ImageReader(heatmap_path)
        img_width = content_width
        img_height = 8.2 * cm

        if y - img_height < 60:
            c.showPage()
            y = height - 50

        c.drawImage(
            image,
            margin_x,
            y - img_height,
            width=img_width,
            height=img_height,
            preserveAspectRatio=True
        )
        y -= img_height + 10

    # ===== Footer =====
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.8)
    c.line(margin_x, 35, width - margin_x, 35)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(margin_x, 22, "Generated automatically by the ECU AI Analyzer backend.")

    c.save()
    return output_path
