from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas


PDF_DARK = colors.HexColor("#0F172A")
PDF_BLUE = colors.HexColor("#2563EB")
PDF_TEAL = colors.HexColor("#0F766E")
PDF_AMBER = colors.HexColor("#B45309")
PDF_RED = colors.HexColor("#B91C1C")
PDF_MUTED = colors.HexColor("#64748B")
PDF_LINE = colors.HexColor("#E2E8F0")
PDF_PANEL = colors.HexColor("#F8FAFC")


def _format_value(value):
    """Formateaza valorile pentru afisarea in PDF."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _paragraph(
    text: str,
    font_size: int = 9,
    leading: int | None = None,
    text_color: str = "#334155",
    bold: bool = False,
) -> Paragraph:
    """Construieste un paragraf ReportLab cu stilul folosit in raport."""
    styles = getSampleStyleSheet()
    style = styles["BodyText"]
    style.fontName = "Helvetica-Bold" if bold else "Helvetica"
    style.fontSize = font_size
    style.leading = leading or font_size + 4
    style.textColor = colors.HexColor(text_color)
    style.spaceBefore = 0
    style.spaceAfter = 0
    return Paragraph(text, style)


def _draw_paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: int = 9,
    text_color: str = "#334155",
    bold: bool = False,
) -> float:
    """Deseneaza un paragraf si returneaza noua pozitie verticala."""
    paragraph = _paragraph(
        text,
        font_size=font_size,
        text_color=text_color,
        bold=bold,
    )
    _, paragraph_height = paragraph.wrap(width, 400)
    paragraph.drawOn(c, x, y - paragraph_height)
    return y - paragraph_height


def _paragraph_height(
    text: str,
    width: float,
    font_size: int = 9,
    text_color: str = "#334155",
    bold: bool = False,
) -> float:
    paragraph = _paragraph(
        text,
        font_size=font_size,
        text_color=text_color,
        bold=bold,
    )
    _, paragraph_height = paragraph.wrap(width, 400)
    return paragraph_height


def _draw_pdf_footer(c: canvas.Canvas, width: float, margin_x: float):
    """Adauga footer-ul comun pe fiecare pagina a raportului."""
    c.setStrokeColor(PDF_LINE)
    c.setLineWidth(0.7)
    c.line(margin_x, 35, width - margin_x, 35)
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(PDF_MUTED)
    c.drawString(margin_x, 22, "Generated automatically by ECU Calibration Analyzer.")


def _new_report_page(c: canvas.Canvas, width: float, height: float, margin_x: float) -> float:
    """Finalizeaza pagina curenta si pregateste urmatoarea pagina."""
    _draw_pdf_footer(c, width, margin_x)
    c.showPage()
    return height - 50


def _ensure_space(
    c: canvas.Canvas,
    y: float,
    needed: float,
    width: float,
    height: float,
    margin_x: float,
) -> float:
    """Verifica daca mai exista spatiu suficient, altfel trece pe pagina noua."""
    if y - needed >= 55:
        return y
    return _new_report_page(c, width, height, margin_x)


def _draw_modern_section_title(c: canvas.Canvas, title: str, x: float, y: float):
    """Deseneaza titlul vizual al unei sectiuni din raport."""
    c.setFillColor(PDF_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    c.setStrokeColor(PDF_BLUE)
    c.setLineWidth(2)
    c.line(x, y - 5, x + 72, y - 5)


def _draw_badge(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    fill,
    stroke=None,
    text_color=PDF_DARK,
) -> float:
    """Deseneaza un badge colorat pentru risc, prioritate sau mod de analiza."""
    label = str(text)
    width = max(54, c.stringWidth(label, "Helvetica-Bold", 7.5) + 18)
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.roundRect(x, y - 16, width, 16, 7, stroke=1, fill=1)
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(x + width / 2, y - 11, label)
    return x + width + 6


def _risk_color(value: str | None):
    """Mapeaza nivelul de risc la culorile folosite in PDF."""
    risk = (value or "").lower()
    if risk == "high":
        return colors.HexColor("#FEE2E2"), colors.HexColor("#FCA5A5"), PDF_RED
    if risk == "medium-high":
        return colors.HexColor("#FEF3C7"), colors.HexColor("#FCD34D"), PDF_AMBER
    if risk == "unknown":
        return colors.HexColor("#F1F5F9"), colors.HexColor("#CBD5E1"), PDF_MUTED
    return colors.HexColor("#ECFDF5"), colors.HexColor("#A7F3D0"), PDF_TEAL


def _priority_color(value: str | None):
    """Mapeaza prioritatea recomandarii la culorile folosite in PDF."""
    priority = (value or "").lower()
    if priority == "high":
        return colors.HexColor("#DBEAFE"), colors.HexColor("#93C5FD"), PDF_BLUE
    if priority == "medium":
        return colors.HexColor("#FEF3C7"), colors.HexColor("#FCD34D"), PDF_AMBER
    return colors.HexColor("#F1F5F9"), colors.HexColor("#CBD5E1"), PDF_MUTED


def _draw_bullets(
    c: canvas.Canvas,
    items: list,
    x: float,
    y: float,
    width: float,
    limit: int = 4,
    color=PDF_TEAL,
    font_size: int = 8,
) -> float:
    """Deseneaza o lista scurta cu bullets in interiorul raportului."""
    current_y = y
    for item in items[:limit]:
        text = escape(str(item))
        paragraph = _paragraph(text, font_size=font_size)
        _, paragraph_height = paragraph.wrap(width - 16, 120)
        c.setFillColor(color)
        c.circle(x + 3, current_y - 7, 2.2, stroke=0, fill=1)
        paragraph.drawOn(c, x + 13, current_y - paragraph_height)
        current_y -= paragraph_height + 4
    return current_y


def _bullets_height(
    items: list,
    width: float,
    limit: int = 4,
    font_size: int = 8,
) -> float:
    """Estimeaza inaltimea listei pentru a evita suprapunerea continutului."""
    total_height = 0.0
    for item in items[:limit]:
        text = escape(str(item))
        paragraph = _paragraph(text, font_size=font_size)
        _, paragraph_height = paragraph.wrap(width - 16, 120)
        total_height += paragraph_height + 4
    return total_height


def _draw_labeled_value(
    c: canvas.Canvas,
    label: str,
    value: str,
    x: float,
    y: float,
    width: float,
) -> float:
    """Deseneaza o pereche label-valoare in sectiunile compacte."""
    label_width = 68
    c.setFillColor(PDF_MUTED)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x, y - 8, label)
    return _draw_paragraph(
        c,
        escape(value or "-"),
        x + label_width,
        y,
        width - label_width,
        font_size=8,
        text_color="#475569",
    )


def _ml_evidence_text(item: dict) -> str:
    """Extrage un text scurt din evidenta ML atasata unei recomandari."""
    evidence = item.get("ml_evidence")
    if not isinstance(evidence, dict):
        return ""

    text = str(evidence.get("headline") or "AI-assisted review available.")
    flagged_maps = evidence.get("flagged_maps")
    if isinstance(flagged_maps, list) and flagged_maps:
        names = ", ".join(str(name) for name in flagged_maps[:3])
        return f"{text} Review maps: {names}."
    return text


def _draw_metric_cards(
    c: canvas.Canvas,
    metrics: list[tuple[str, str]],
    x: float,
    y: float,
    width: float,
) -> float:
    """Deseneaza cardurile cu metrice principale din raport."""
    gap = 8
    card_width = (width - gap * 2) / 3
    card_height = 42
    current_x = x
    current_y = y
    for index, (label, value) in enumerate(metrics):
        if index and index % 3 == 0:
            current_x = x
            current_y -= card_height + gap
        c.setFillColor(PDF_PANEL)
        c.setStrokeColor(PDF_LINE)
        c.roundRect(current_x, current_y - card_height, card_width, card_height, 8, stroke=1, fill=1)
        c.setFillColor(PDF_MUTED)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(current_x + 10, current_y - 15, label.upper())
        c.setFillColor(PDF_DARK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(current_x + 10, current_y - 31, _format_value(value))
        current_x += card_width + gap
    rows = ((len(metrics) - 1) // 3) + 1 if metrics else 0
    return y - rows * card_height - max(0, rows - 1) * gap


def _draw_key_value_grid(
    c: canvas.Canvas,
    data: list[tuple[str, str]],
    x: float,
    y: float,
    width: float,
) -> float:
    """Deseneaza o grila simpla de informatii cheie."""
    columns = 2
    col_width = width / columns
    current_y = y
    for index in range(0, len(data), columns):
        row = data[index:index + columns]
        for column_index, (label, value) in enumerate(row):
            current_x = x + column_index * col_width
            c.setFillColor(PDF_MUTED)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(current_x, current_y, label.upper())
            c.setFillColor(PDF_DARK)
            c.setFont("Helvetica", 9)
            display_value = _format_value(value)
            c.drawString(current_x, current_y - 14, display_value[:46])
        current_y -= 32
    return current_y


def _matrix(value) -> list[list[float]]:
    """Normalizeaza un preview de harta intr-o matrice numerica."""
    if not isinstance(value, list):
        return []
    matrix: list[list[float]] = []
    for row in value:
        if not isinstance(row, list):
            continue
        parsed = [float(cell) for cell in row if isinstance(cell, (int, float))]
        if parsed:
            matrix.append(parsed)
    return matrix


def _is_renderable_surface(matrix: list[list[float]]) -> bool:
    """Verifica daca matricea are suficiente date pentru randare 3D."""
    rows = len(matrix)
    columns = min((len(row) for row in matrix), default=0)
    if rows < 3 or columns < 3:
        return False
    values = [value for row in matrix for value in row[:columns]]
    if len(values) < 9:
        return False
    return max(values) - min(values) > 0.000001


def _lerp_color(start: str, end: str, amount: float):
    """Interpoleaza intre doua culori pentru suprafata 3D."""
    amount = max(0.0, min(1.0, amount))
    a = colors.HexColor(start)
    b = colors.HexColor(end)
    return colors.Color(
        a.red + (b.red - a.red) * amount,
        a.green + (b.green - a.green) * amount,
        a.blue + (b.blue - a.blue) * amount,
    )


def _surface_color(normalized: float):
    """Alege culoarea unei celule din suprafata in functie de valoarea normalizata."""
    if normalized < 0.5:
        return _lerp_color("#38BDF8", "#FACC15", normalized / 0.5)
    return _lerp_color("#FACC15", "#DC2626", (normalized - 0.5) / 0.5)


def _draw_surface_preview(
    c: canvas.Canvas,
    matrix: list[list[float]],
    x: float,
    y: float,
    width: float,
    height: float,
) -> bool:
    """Randeaza o suprafata 3D simplificata pentru o harta ECU."""
    rows = len(matrix)
    columns = min((len(row) for row in matrix), default=0)
    if not _is_renderable_surface(matrix):
        return False

    values = sorted(value for row in matrix for value in row[:columns])
    low = values[int(len(values) * 0.05)]
    high = values[min(len(values) - 1, int(len(values) * 0.95))]
    span = high - low if abs(high - low) > 0.000001 else 1.0
    z_height = (rows + columns) * 0.46

    def norm(row: int, column: int) -> float:
        return max(0.0, min(1.0, (matrix[row][column] - low) / span))

    def logical_project(row: int, column: int) -> tuple[float, float]:
        normalized = norm(row, column)
        return (
            float(column - row),
            (column + row) * 0.52 - normalized * z_height,
        )

    logical = [
        [logical_project(row, column) for column in range(columns)]
        for row in range(rows)
    ]
    min_x = min(point[0] for row in logical for point in row)
    max_x = max(point[0] for row in logical for point in row)
    min_y = min(point[1] for row in logical for point in row)
    max_y = max(point[1] for row in logical for point in row)
    logical_width = max(max_x - min_x, 1.0)
    logical_height = max(max_y - min_y, 1.0)
    padding = 8
    scale = min((width - padding * 2) / logical_width, (height - padding * 2) / logical_height)
    drawn_width = logical_width * scale
    drawn_height = logical_height * scale
    offset_x = x + (width - drawn_width) / 2 - min_x * scale
    offset_y = y - (height - drawn_height) / 2 + min_y * scale

    def project(row: int, column: int) -> tuple[float, float]:
        px, py = logical[row][column]
        return px * scale + offset_x, offset_y - py * scale

    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(PDF_LINE)
    c.roundRect(x, y - height, width, height, 8, stroke=1, fill=1)

    for row in range(rows - 2, -1, -1):
        for column in range(columns - 1):
            points = [
                project(row, column),
                project(row, column + 1),
                project(row + 1, column + 1),
                project(row + 1, column),
            ]
            normalized = (
                norm(row, column)
                + norm(row, column + 1)
                + norm(row + 1, column + 1)
                + norm(row + 1, column)
            ) / 4.0
            path = c.beginPath()
            path.moveTo(points[0][0], points[0][1])
            for point_x, point_y in points[1:]:
                path.lineTo(point_x, point_y)
            path.close()
            c.setFillColor(_surface_color(normalized))
            c.setStrokeColor(colors.HexColor("#64748B"))
            c.setLineWidth(0.3)
            c.drawPath(path, stroke=1, fill=1)
    return True


def _visual_candidates(analysis: dict, recommendations: list[dict]) -> list[dict]:
    """Alege hartile cele mai potrivite pentru sectiunea vizuala din PDF."""
    maps = analysis.get("maps") or []
    if not isinstance(maps, list):
        return []
    preferred_categories = ["torque", "fuel", "air_fuel", "boost", "timing", "limiter"]
    recommendation_categories = [
        str(item.get("category"))
        for item in recommendations
        if isinstance(item, dict) and item.get("category")
    ]
    category_order = recommendation_categories + preferred_categories

    candidates: list[dict] = []
    seen_addresses: set[str] = set()
    for category in category_order:
        category_maps = [
            item for item in maps
            if isinstance(item, dict) and str(item.get("category")) == category
        ]
        category_maps.sort(
            key=lambda item: (item.get("diff") or {}).get("changed_percent", 0),
            reverse=True,
        )
        for item in category_maps:
            address = str(item.get("address_hex") or item.get("name") or "")
            if address in seen_addresses:
                continue
            surface = item.get("modified_surface_preview") or item.get("surface_preview")
            matrix = _matrix(surface)
            if _is_renderable_surface(matrix):
                seen_addresses.add(address)
                candidates.append(item)
                break
        if len(candidates) >= 2:
            break
    return candidates[:2]


def generate_calibration_report(
    analysis: dict,
    output_path: str | Path,
) -> str:
    """Genereaza fisierul PDF final pe baza rezultatului de analiza."""
    output_path = str(output_path)
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    margin_x = 42
    content_width = width - 2 * margin_x
    y = height - 50

    report = analysis.get("report") or {}
    summary = analysis.get("summary") or {}
    binary_diff = analysis.get("binary_diff") or {}
    recommendations = report.get("recommended_actions") or []
    tuner_summary = report.get("tuner_summary") or []
    top_changes = report.get("top_changes") or []
    checks = report.get("validation_checks") or []
    verdict = report.get("verdict") or analysis.get("analysis_verdict") or {}

    c.setFillColor(PDF_DARK)
    c.roundRect(margin_x, y - 66, content_width, 66, 12, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 19)
    c.drawString(margin_x + 16, y - 25, "ECU Calibration Analyzer")
    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.drawString(margin_x + 16, y - 43, f"Generated on {generated_at}")
    mode = "Review tuned change" if summary.get("modified_file") else "Original-only planning"
    _draw_badge(
        c,
        mode,
        margin_x + content_width - 142,
        y - 24,
        colors.HexColor("#DBEAFE"),
        colors.HexColor("#93C5FD"),
        PDF_BLUE,
    )
    y -= 88

    y = _ensure_space(c, y, 110, width, height, margin_x)
    context_top = y
    context_height = 88
    c.setFillColor(PDF_PANEL)
    c.setStrokeColor(PDF_LINE)
    c.roundRect(margin_x, context_top - context_height, content_width, context_height, 10, stroke=1, fill=1)
    context_data = [
        ("Original file", summary.get("original_file") or "-"),
        ("Tuned/current file", summary.get("modified_file") or "Not provided"),
        ("Original size", _format_file_size(summary.get("original_size"))),
        ("Tuned size", _format_file_size(summary.get("modified_size"))),
    ]
    _draw_key_value_grid(c, context_data, margin_x + 12, context_top - 18, content_width - 24)
    y = context_top - context_height - 26

    headline = escape(report.get("headline") or "Calibration analysis completed.")
    verdict_title = escape(str(verdict.get("title") or ""))
    verdict_message = escape(str(verdict.get("message") or ""))
    verdict_text = (
        f"<b>{verdict_title}</b> - {verdict_message}"
        if verdict_title and verdict_message
        else verdict_title or verdict_message
    )
    headline_height = _paragraph_height(
        headline,
        content_width - 24,
        font_size=10,
        text_color="#1E3A8A",
        bold=True,
    )
    verdict_height = (
        _paragraph_height(
            verdict_text,
            content_width - 24,
            font_size=8.4,
            text_color="#334155",
        )
        + 8
        if verdict_text
        else 0
    )
    summary_bullets_height = _bullets_height(
        tuner_summary,
        content_width - 24,
        limit=4,
        font_size=8,
    ) if tuner_summary else 0
    summary_card_height = (
        28
        + headline_height
        + verdict_height
        + (8 + summary_bullets_height if tuner_summary else 0)
        + 12
    )

    y = _ensure_space(c, y, summary_card_height + 60, width, height, margin_x)
    _draw_modern_section_title(c, "Executive Summary", margin_x, y)
    y -= 22
    summary_top = y
    c.setFillColor(colors.HexColor("#EFF6FF"))
    c.setStrokeColor(colors.HexColor("#BFDBFE"))
    c.roundRect(margin_x, summary_top - summary_card_height, content_width, summary_card_height, 10, stroke=1, fill=1)
    content_y = _draw_paragraph(
        c,
        headline,
        margin_x + 12,
        summary_top - 15,
        content_width - 24,
        font_size=10,
        text_color="#1E3A8A",
        bold=True,
    )
    if verdict_text:
        content_y -= 8
        content_y = _draw_paragraph(
            c,
            verdict_text,
            margin_x + 12,
            content_y,
            content_width - 24,
            font_size=8.4,
            text_color="#334155",
        )
    if tuner_summary:
        content_y -= 8
        _draw_bullets(
            c,
            tuner_summary,
            margin_x + 12,
            content_y,
            content_width - 24,
            limit=4,
            color=PDF_BLUE,
        )
    y = summary_top - summary_card_height - 30

    y = _ensure_space(c, y, 110, width, height, margin_x)
    _draw_modern_section_title(c, "Key Metrics", margin_x, y)
    y -= 20
    y = _draw_metric_cards(
        c,
        [
            ("Maps extracted", summary.get("maps_extracted", 0)),
            ("Maps changed", summary.get("maps_changed", 0)),
            ("Definitions", summary.get("definitions_count", 0)),
            ("Binary changed", f"{binary_diff.get('changed_percent', 0)}%"),
            ("Changed bytes", binary_diff.get("changed_bytes", 0)),
            ("Recommendations", len(recommendations)),
        ],
        margin_x,
        y,
        content_width,
    )
    y -= 22

    visual_maps = _visual_candidates(analysis, recommendations)
    if visual_maps:
        y = _ensure_space(c, y, 185, width, height, margin_x)
        _draw_modern_section_title(c, "Visual Map Highlights", margin_x, y)
        y -= 20
        card_gap = 10
        card_width = (content_width - card_gap) / 2
        card_height = 150
        drawn_visuals = 0
        for index, item in enumerate(visual_maps):
            card_x = margin_x + index * (card_width + card_gap)
            card_y = y
            surface = item.get("modified_surface_preview") or item.get("surface_preview")
            surface_matrix = _matrix(surface)
            if not _is_renderable_surface(surface_matrix):
                continue
            c.setFillColor(PDF_PANEL)
            c.setStrokeColor(PDF_LINE)
            c.roundRect(card_x, card_y - card_height, card_width, card_height, 10, stroke=1, fill=1)
            c.setFillColor(PDF_DARK)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(card_x + 10, card_y - 16, str(item.get("name") or "Map")[:42])
            c.setFillColor(PDF_MUTED)
            c.setFont("Helvetica", 7.5)
            diff = item.get("diff") or {}
            zone = ", ".join(
                f"{zone_item.get('label')} {zone_item.get('min')}-{zone_item.get('max')}"
                for zone_item in (item.get("affected_zone") or [])[:2]
                if isinstance(zone_item, dict)
            )
            c.drawString(
                card_x + 10,
                card_y - 29,
                f"{item.get('category', '-')} | changed {diff.get('changed_percent', 0)}% | max delta {diff.get('max_abs_delta', 0)}",
            )
            if zone:
                c.drawString(card_x + 10, card_y - 40, f"Zone: {zone[:46]}")
            if _draw_surface_preview(c, surface_matrix, card_x + 10, card_y - 48, card_width - 20, 92):
                drawn_visuals += 1
        if drawn_visuals:
            y -= card_height + 22

    if recommendations:
        y = _ensure_space(c, y, 250, width, height, margin_x)
        _draw_modern_section_title(c, "Priority Recommendations", margin_x, y)
        y -= 22
        for item in recommendations[:6]:
            column_width = (content_width - 34) / 2
            reason_text = escape(str(item.get("reason") or ""))
            target_text = str(item.get("target_zone") or "-")
            suggested_text = str(item.get("suggested_change") or "-")
            ml_text = _ml_evidence_text(item)
            reason_height = _paragraph_height(reason_text, content_width - 24, font_size=8.2)
            target_height = max(
                12,
                _paragraph_height(escape(target_text), content_width - 92, font_size=8),
            )
            suggested_height = max(
                12,
                _paragraph_height(escape(suggested_text), content_width - 92, font_size=8),
            )
            ml_height = (
                max(12, _paragraph_height(escape(ml_text), content_width - 92, font_size=8))
                + 6
                if ml_text
                else 0
            )
            actions_height = _bullets_height(item.get("actions") or [], column_width, limit=2, font_size=7.4)
            risks_height = _bullets_height(item.get("risks") or [], column_width, limit=2, font_size=7.4)
            card_height = max(
                164,
                20
                + 22
                + reason_height
                + 12
                + target_height
                + 6
                + suggested_height
                + ml_height
                + 24
                + max(actions_height, risks_height)
                + 18,
            )
            y = _ensure_space(c, y, card_height + 14, width, height, margin_x)
            card_top = y
            c.setFillColor(colors.white)
            c.setStrokeColor(PDF_LINE)
            c.roundRect(margin_x, card_top - card_height, content_width, card_height, 10, stroke=1, fill=1)
            c.setFillColor(PDF_DARK)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin_x + 12, card_top - 18, str(item.get("title") or "Recommendation")[:70])
            badge_x = margin_x + 12
            priority_fill, priority_stroke, priority_text = _priority_color(item.get("priority"))
            badge_x = _draw_badge(c, f"Priority: {item.get('priority', '-')}", badge_x, card_top - 32, priority_fill, priority_stroke, priority_text)
            risk_fill, risk_stroke, risk_text = _risk_color(item.get("risk"))
            _draw_badge(
                c,
                f"Risk: {item.get('risk', '-')}",
                badge_x,
                card_top - 32,
                risk_fill,
                risk_stroke,
                risk_text,
            )
            y_text = _draw_paragraph(
                c,
                reason_text,
                margin_x + 12,
                card_top - 54,
                content_width - 24,
                font_size=8.2,
            )
            info_y = y_text - 10
            info_y = _draw_labeled_value(
                c,
                "TARGET ZONE",
                target_text,
                margin_x + 12,
                info_y,
                content_width - 24,
            ) - 5
            info_y = _draw_labeled_value(
                c,
                "SUGGESTED",
                suggested_text,
                margin_x + 12,
                info_y,
                content_width - 24,
            )
            if ml_text:
                info_y = _draw_labeled_value(
                    c,
                    "AI REVIEW",
                    ml_text,
                    margin_x + 12,
                    info_y - 5,
                    content_width - 24,
                )
            columns_title_y = info_y - 18
            c.setFillColor(PDF_TEAL)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin_x + 12, columns_title_y, "Recommended actions")
            actions_bottom = _draw_bullets(
                c,
                item.get("actions") or [],
                margin_x + 12,
                columns_title_y - 12,
                column_width,
                limit=2,
                color=PDF_TEAL,
                font_size=7.4,
            )
            c.setFillColor(PDF_AMBER)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin_x + 26 + column_width, columns_title_y, "Risks to watch")
            risks_bottom = _draw_bullets(
                c,
                item.get("risks") or [],
                margin_x + 26 + column_width,
                columns_title_y - 12,
                column_width,
                limit=2,
                color=PDF_AMBER,
                font_size=7.4,
            )
            y = min(card_top - card_height, actions_bottom, risks_bottom) - 14

    if top_changes:
        y = _ensure_space(c, y, 150, width, height, margin_x)
        _draw_modern_section_title(c, "Top Modified Maps", margin_x, y)
        y -= 24
        compact_changes: list[dict] = []
        name_counts: dict[str, int] = {}
        for item in top_changes:
            name = str(item.get("name") or "-")
            if name_counts.get(name, 0) >= 2:
                continue
            name_counts[name] = name_counts.get(name, 0) + 1
            compact_changes.append(item)
            if len(compact_changes) >= 6:
                break
        headers = ["Map", "Category", "Changed", "Max delta", "Zone"]
        col_widths = [190, 70, 52, 62, content_width - 374]
        row_height = 18
        c.setFillColor(PDF_DARK)
        c.roundRect(margin_x, y - row_height, content_width, row_height, 6, stroke=0, fill=1)
        current_x = margin_x + 8
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7.5)
        for header, col_width in zip(headers, col_widths):
            c.drawString(current_x, y - 12, header)
            current_x += col_width
        y -= row_height
        for item in compact_changes:
            y = _ensure_space(c, y, 28, width, height, margin_x)
            c.setFillColor(colors.white)
            c.setStrokeColor(PDF_LINE)
            c.rect(margin_x, y - row_height, content_width, row_height, stroke=1, fill=1)
            values = [
                str(item.get("name") or "-")[:32],
                str(item.get("category") or "-")[:12],
                f"{item.get('changed_percent', 0)}%",
                str(item.get("max_abs_delta", 0))[:12],
                str(item.get("zone_text") or "-")[:32],
            ]
            current_x = margin_x + 8
            c.setFillColor(PDF_DARK)
            c.setFont("Helvetica", 7.3)
            for value, col_width in zip(values, col_widths):
                c.drawString(current_x, y - 12, value)
                current_x += col_width
            y -= row_height
        y -= 18

    if checks:
        y = _ensure_space(c, y, 125, width, height, margin_x)
        _draw_modern_section_title(c, "Validation Checklist", margin_x, y)
        y -= 20
        y = _draw_bullets(c, checks, margin_x, y, content_width, limit=8, color=PDF_TEAL, font_size=8)
        y -= 12

    y = _ensure_space(c, y, 70, width, height, margin_x)
    c.setFillColor(colors.HexColor("#FFF7ED"))
    c.setStrokeColor(colors.HexColor("#FDBA74"))
    c.roundRect(margin_x, y - 54, content_width, 54, 9, stroke=1, fill=1)
    _draw_paragraph(
        c,
        "Recommendations are decision-support guidance. Validate all changes with logs, dyno testing where appropriate, and hardware-specific safety limits. Do not remove thermal or mechanical protections blindly.",
        margin_x + 12,
        y - 14,
        content_width - 24,
        font_size=8,
        text_color="#9A3412",
    )

    _draw_pdf_footer(c, width, margin_x)
    c.save()
    return output_path


def _format_file_size(value) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.2f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{int(value)} B"
