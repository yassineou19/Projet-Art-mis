"""Rapport PDF d'une analyse de risque Artemis."""

from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_prediction_pdf(
    prediction: pd.Series,
    rocket_reliability: dict,
    agency_reliability: dict,
    drivers: pd.DataFrame,
    model_version: str,
) -> bytes:
    """Construit un rapport PDF compact et lisible."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Artemis - {prediction['launch_name']}",
        author="Artemis Space Analytics",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ArtemisTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#111827"),
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ArtemisSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#5B21B6"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ArtemisTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#312E81"),
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ArtemisTableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
        )
    )

    risk = float(prediction["risk_score"])
    lower = float(prediction["risk_lower"])
    upper = float(prediction["risk_upper"])
    story = [
        Paragraph("ARTEMIS SPACE ANALYTICS", styles["ArtemisTitle"]),
        Paragraph(str(prediction["launch_name"]), styles["Heading2"]),
        Paragraph(
            f"Analyse generee avec {model_version}. Ce rapport est une aide a la decision "
            "et non une garantie de resultat.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]

    summary = [
        ["Decision", "Risque estime", "Fourchette empirique"],
        [
            str(prediction["prediction"]),
            f"{risk * 100:.1f}%",
            f"{lower * 100:.1f}% - {upper * 100:.1f}%",
        ],
    ]
    summary_table = Table(summary, colWidths=[58 * mm, 45 * mm, 52 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312E81")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F5F3FF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([summary_table, Paragraph("Fiabilite historique", styles["ArtemisSection"])])

    reliability_rows = [
        [_table_cell(value, styles["ArtemisTableHeader"]) for value in ["Reference", "Tentatives", "Echecs", "Fiabilite estimee"]],
        [
            _table_cell(f"Fusee: {rocket_reliability['label']}", styles["ArtemisTableCell"]),
            _table_cell(str(rocket_reliability["attempts"]), styles["ArtemisTableCell"]),
            _table_cell(str(rocket_reliability["failures"]), styles["ArtemisTableCell"]),
            _table_cell(f"{rocket_reliability['success_rate'] * 100:.1f}%", styles["ArtemisTableCell"]),
        ],
        [
            _table_cell(f"Agence: {agency_reliability['label']}", styles["ArtemisTableCell"]),
            _table_cell(str(agency_reliability["attempts"]), styles["ArtemisTableCell"]),
            _table_cell(str(agency_reliability["failures"]), styles["ArtemisTableCell"]),
            _table_cell(f"{agency_reliability['success_rate'] * 100:.1f}%", styles["ArtemisTableCell"]),
        ],
    ]
    reliability_table = Table(reliability_rows, colWidths=[65 * mm, 30 * mm, 25 * mm, 40 * mm])
    reliability_table.setStyle(_standard_table_style())
    story.extend([reliability_table, Paragraph("Facteurs principaux", styles["ArtemisSection"])])

    driver_rows = [[_table_cell("Facteur", styles["ArtemisTableHeader"]), _table_cell("Effet", styles["ArtemisTableHeader"])]]
    for row in drivers.itertuples(index=False):
        driver_rows.append(
            [
                _table_cell(str(row.factor), styles["ArtemisTableCell"]),
                _table_cell(str(row.direction), styles["ArtemisTableCell"]),
            ]
        )
    driver_table = Table(driver_rows, colWidths=[105 * mm, 55 * mm])
    driver_table.setStyle(_standard_table_style())
    story.extend(
        [
            driver_table,
            Spacer(1, 7 * mm),
            Paragraph(
                "Lecture: la rarete des echecs rend toute estimation incertaine. Artemis "
                "combine historique, caracteristiques de mission et calibration temporelle.",
                styles["BodyText"],
            ),
        ]
    )
    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output.getvalue()


def _table_cell(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def _standard_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDE9FE")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#312E81")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def _draw_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(18 * mm, 8 * mm, "Artemis Space Analytics - Rapport confidentiel")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {document.page}")
    canvas.restoreState()
