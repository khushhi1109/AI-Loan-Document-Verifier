"""
Report Generation Module for AI Loan Document Verifier.
Exports discrepancy flags, line citations, and human underwriter decisions as PDF and CSV.
"""

import io
import csv
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.models import ApplicantPacketData, MismatchFlag, SeverityLevel

def generate_csv_report(
    packet_data: ApplicantPacketData,
    flags: List[MismatchFlag],
    actions: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generates a structured CSV report containing flags, line-level evidence, and decisions."""
    actions = actions or []
    action_map = {a.get("flag_id"): a for a in actions}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header Row
    writer.writerow([
        "Applicant ID",
        "Applicant Name",
        "Flag ID",
        "Severity",
        "Check Rule",
        "Discrepancy Title",
        "Risk Explanation",
        "Evidence Document",
        "Evidence Page",
        "Evidence Line",
        "Evidence Field",
        "Extracted Value",
        "Underwriter Decision",
        "Underwriter ID",
        "Override Rationale",
        "Decision Timestamp"
    ])

    app_id = packet_data.applicant_id
    app_name = str(packet_data.id_document.applicant_name.value) if packet_data.id_document.applicant_name.is_found else "N/A"

    if not flags:
        writer.writerow([
            app_id,
            app_name,
            "NONE",
            "CLEAN",
            "ALL_CHECKS_PASSED",
            "No discrepancies detected",
            "All submitted records align within configured policy tolerances.",
            "", "", "", "", "",
            "VERIFIED_CLEAN",
            "", "", ""
        ])
    else:
        for f in flags:
            act = action_map.get(f.flag_id, {})
            decision = act.get("action", "PENDING_REVIEW")
            uw_id = act.get("underwriter_id", "")
            rationale = act.get("rationale", "")
            timestamp = act.get("timestamp", "")

            if f.evidence:
                for ev in f.evidence:
                    writer.writerow([
                        app_id,
                        app_name,
                        f.flag_id,
                        f.severity.value,
                        f.check_name,
                        f.short_title,
                        f.llm_explanation,
                        ev.document,
                        ev.page,
                        ev.line,
                        ev.field_name,
                        ev.extracted_value,
                        decision,
                        uw_id,
                        rationale,
                        timestamp
                    ])
            else:
                writer.writerow([
                    app_id,
                    app_name,
                    f.flag_id,
                    f.severity.value,
                    f.check_name,
                    f.short_title,
                    f.llm_explanation,
                    "", "", "", "", "",
                    decision,
                    uw_id,
                    rationale,
                    timestamp
                ])

    return output.getvalue()

def generate_pdf_report(
    packet_data: ApplicantPacketData,
    flags: List[MismatchFlag],
    actions: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """Generates an executive-ready Underwriting Discrepancy & Decision Report in PDF format."""
    actions = actions or []
    action_map = {a.get("flag_id"): a for a in actions}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A")
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B")
    )
    banner_style = ParagraphStyle(
        "BannerText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#92400E")
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )
    table_header = ParagraphStyle(
        "TableHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    story = []

    # Title & Header
    story.append(Paragraph("AI Loan Document Verifier — Underwriting Verification Report", title_style))
    story.append(Paragraph("Cross-Document Consistency Analysis & Decision Audit Trail", subtitle_style))
    story.append(Spacer(1, 8))

    # Mandatory Banner Flowable
    banner_text = (
        "<b>WARNING: Decision Support Only</b><br/>"
        "This tool flags inconsistencies for review. It does not approve or reject applications. "
        "Final decisions rest with the human underwriter."
    )
    banner_table = Table(
        [[Paragraph(banner_text, banner_style)]],
        colWidths=[540]
    )
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#F59E0B")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # Applicant Overview Table
    app_id = packet_data.applicant_id
    id_name = str(packet_data.id_document.applicant_name.value) if packet_data.id_document.applicant_name.is_found else "N/A"
    id_num = str(packet_data.id_document.id_number.value) if packet_data.id_document.id_number.is_found else "N/A"
    id_type = packet_data.id_document.id_type
    bank_name = str(packet_data.bank_statement.bank_name.value) if packet_data.bank_statement.bank_name.is_found else "N/A"
    num_slips = len(packet_data.salary_slips)

    overview_data = [
        [
            Paragraph(f"<b>Applicant ID:</b> {app_id}", body_style),
            Paragraph(f"<b>Primary Name:</b> {id_name}", body_style),
            Paragraph(f"<b>ID Proof:</b> {id_type} ({id_num})", body_style)
        ],
        [
            Paragraph(f"<b>Salary Slips Verified:</b> {num_slips} submitted", body_style),
            Paragraph(f"<b>Bank Institution:</b> {bank_name}", body_style),
            Paragraph(f"<b>Total Discrepancies:</b> {len(flags)}", body_style)
        ]
    ]
    overview_table = Table(overview_data, colWidths=[180, 180, 180])
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 10))

    # Discrepancy Findings
    story.append(Paragraph(f"Discrepancy Flags & Triage Audit ({len(flags)})", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8))

    if not flags:
        no_flags_para = Paragraph(
            "<b>CLEAN APPLICATION:</b> No discrepancies detected across submitted identity, salary, or bank records. "
            "All names, earnings, payroll periods, and account entries align within established underwriting tolerances.",
            body_style
        )
        story.append(no_flags_para)
    else:
        for idx, f in enumerate(flags, start=1):
            act = action_map.get(f.flag_id, {})
            decision = act.get("action", "PENDING REVIEW")
            uw_id = act.get("underwriter_id", "N/A")
            rationale = act.get("rationale", "")

            sev_color = colors.HexColor("#EF4444") if f.severity == SeverityLevel.HIGH else (
                colors.HexColor("#F59E0B") if f.severity == SeverityLevel.MEDIUM else colors.HexColor("#3B82F6")
            )

            # Flag Card Header
            header_text = f"<b>#{idx}. {f.short_title}</b>"
            badge_text = f"<font color='white'><b>{f.severity.value}</b></font>"

            decision_text = f"<b>Decision:</b> {decision}"
            if uw_id != "N/A":
                decision_text += f" by {uw_id}"
            if rationale:
                decision_text += f"<br/><b>Rationale:</b> <i>{rationale}</i>"

            flag_summary_data = [
                [
                    Paragraph(header_text, body_style),
                    Paragraph(badge_text, ParagraphStyle("Bdg", parent=table_cell, alignment=1))
                ],
                [
                    Paragraph(f"<b>Underwriting Analysis:</b> {f.llm_explanation}", body_style),
                    Paragraph(decision_text, body_style)
                ]
            ]
            flag_summary_table = Table(flag_summary_data, colWidths=[430, 110])
            flag_summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (1, 0), (1, 0), sev_color),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("LINEBEFORE", (0, 0), (0, -1), 4, sev_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))

            # Evidence Table
            ev_table_rows = [
                [
                    Paragraph("Document", table_header),
                    Paragraph("Page", table_header),
                    Paragraph("Line", table_header),
                    Paragraph("Field Name", table_header),
                    Paragraph("Extracted Value", table_header)
                ]
            ]
            for ev in f.evidence:
                ev_table_rows.append([
                    Paragraph(ev.document, table_cell),
                    Paragraph(str(ev.page), table_cell),
                    Paragraph(str(ev.line), table_cell),
                    Paragraph(ev.field_name, table_cell),
                    Paragraph(ev.extracted_value, table_cell)
                ])

            ev_table = Table(ev_table_rows, colWidths=[150, 40, 40, 110, 200])
            ev_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))

            story.append(KeepTogether([
                flag_summary_table,
                Spacer(1, 2),
                ev_table,
                Spacer(1, 8)
            ]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
