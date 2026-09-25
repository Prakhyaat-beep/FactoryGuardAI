"""Generate a PDF machine-analysis report from stored FactoryGuard data."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_machine_report(machine_detail):
    """Build a professional PDF using only database-backed machine detail data."""
    latest = machine_detail["latestPrediction"]
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="FactoryGuard AI Machine Analysis Report", author="FactoryGuard AI",
    )
    styles = _create_styles()
    story = [
        Paragraph("FactoryGuard AI", styles["title"]),
        Paragraph("Machine Analysis and Predictive Maintenance Report", styles["subtitle"]),
        Spacer(1, 5 * mm),
    ]

    story.append(Paragraph("Report summary", styles["section"]))
    story.append(_key_value_table([
        ("Machine identifier", machine_detail["machineId"]),
        ("Analysis timestamp", latest["timestamp"]),
        ("Predicted condition", latest["condition"]),
        ("Model-derived risk indicator", f"{latest['failureRisk']}%"),
        ("Maintenance priority", latest["maintenancePriority"]),
    ], styles))

    story.append(Paragraph("Sensor values", styles["section"]))
    inputs = latest["inputs"]
    story.append(_key_value_table([
        ("Air temperature", f"{inputs['airTemperature']} K"),
        ("Process temperature", f"{inputs['processTemperature']} K"),
        ("Rotational speed", f"{inputs['rotationalSpeed']} RPM"),
        ("Torque", f"{inputs['torque']} Nm"),
        ("Tool wear", f"{inputs['toolWear']} min"),
        ("Product type", inputs["type"]),
    ], styles))

    story.append(Paragraph("Model output and recommended action", styles["section"]))
    probabilities = latest["probabilities"]
    story.append(_key_value_table([
        ("No failure class score", f"{probabilities['noFailure']}%"),
        ("Machine failure class score", f"{probabilities['machineFailure']}%"),
        ("Recommendation", latest["recommendation"]),
    ], styles))
    story.append(Paragraph(latest["riskLabel"], styles["small"]))
    story.append(Paragraph(latest["maintenanceDisclaimer"], styles["small"]))

    story.append(Paragraph("Recent prediction history", styles["section"]))
    prediction_rows = [["Timestamp", "Condition", "Risk"]]
    prediction_rows.extend([
        [record["timestamp"], record["condition"], f"{record['failureRisk']}%"]
        for record in machine_detail["predictions"][:10]
    ])
    story.append(_history_table(prediction_rows, [96 * mm, 43 * mm, 35 * mm], styles))

    story.append(Paragraph("Maintenance history", styles["section"]))
    maintenance_records = machine_detail["maintenanceRecords"]
    if maintenance_records:
        maintenance_rows = [["Date", "Type", "Issue", "Action taken"]]
        maintenance_rows.extend([
            [record["maintenanceDate"], record["maintenanceType"], record["issue"], record["actionTaken"] or "Not recorded"]
            for record in maintenance_records[:10]
        ])
        story.append(_history_table(maintenance_rows, [28 * mm, 30 * mm, 57 * mm, 59 * mm], styles))
    else:
        story.append(Paragraph("No maintenance records are available for this machine.", styles["body"]))

    story.extend([
        Spacer(1, 5 * mm),
        Paragraph("This report is generated from stored FactoryGuard records. It supports maintenance decisions and does not guarantee machine failure.", styles["small"]),
    ])
    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()


def _create_styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle("FactoryGuardBody", parent=base["BodyText"], fontSize=9, leading=12)
    return {
        "title": ParagraphStyle("FactoryGuardTitle", parent=base["Title"], fontSize=22, leading=26, textColor=colors.HexColor("#0b4b61"), alignment=TA_LEFT),
        "subtitle": ParagraphStyle("FactoryGuardSubtitle", parent=base["Heading3"], fontSize=11, leading=14, textColor=colors.HexColor("#4d6470")),
        "section": ParagraphStyle("FactoryGuardSection", parent=base["Heading2"], fontSize=13, leading=16, textColor=colors.HexColor("#0b4b61"), spaceBefore=12, spaceAfter=6),
        "body": body,
        "label": ParagraphStyle("FactoryGuardLabel", parent=body, fontName="Helvetica-Bold"),
        "header": ParagraphStyle("FactoryGuardHeader", parent=body, fontName="Helvetica-Bold", textColor=colors.white, fontSize=8, leading=10),
        "small": ParagraphStyle("FactoryGuardSmall", parent=body, fontSize=8, leading=10, textColor=colors.HexColor("#4d6470")),
    }


def _key_value_table(rows, styles):
    formatted = [[_paragraph(label, styles["label"]), _paragraph(value, styles["body"])] for label, value in rows]
    table = Table(formatted, colWidths=[50 * mm, 124 * mm], hAlign="LEFT")
    table.setStyle(TableStyle(_base_table_style() + [("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e9f2f5"))]))
    return table


def _history_table(rows, widths, styles):
    formatted = [[_paragraph(cell, styles["header"] if row_index == 0 else styles["body"]) for cell in row] for row_index, row in enumerate(rows)]
    table = Table(formatted, colWidths=widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle(_base_table_style() + [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b4b61"))]))
    return table


def _base_table_style():
    return [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b9ced6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]


def _paragraph(value, style):
    return Paragraph(escape(str(value)), style)


def _draw_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#b9ced6"))
    canvas.line(document.leftMargin, 11 * mm, A4[0] - document.rightMargin, 11 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#4d6470"))
    canvas.drawString(document.leftMargin, 7 * mm, "FactoryGuard AI - Generated from stored analysis records")
    canvas.drawRightString(A4[0] - document.rightMargin, 7 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()
