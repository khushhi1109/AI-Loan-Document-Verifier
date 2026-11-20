"""
Synthetic Bank Statement Generator using ReportLab.
Renders account details and tabular transaction histories including salary credits.
"""

import os
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_bank_statement_pdf(
    file_path: str,
    bank_name: str,
    account_holder: str,
    account_number: str,
    transactions: List[Dict[str, Any]],
    dob_str: str = "15/08/1990",
    statement_period: str = "01-Oct-2023 to 31-Mar-2024",
    applicant_id_number: str = "not_found"
) -> str:
    """Generates a synthetic bank statement PDF with tabular transactions."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Bank Header Banner
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(30, height - 90, width - 60, 60, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, bank_name.upper())
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 78, f"ACCOUNT TRANSACTION STATEMENT | PERIOD: {statement_period}")

    # Account Profile Block
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    y = height - 115
    c.drawString(50, y, f"Account Holder Name: {account_holder}")
    c.drawString(340, y, f"Account Number: {account_number}")

    y -= 18
    c.drawString(50, y, f"Account Type: Savings Account")
    c.drawString(340, y, f"Date of Birth: {dob_str}")

    y -= 18
    if applicant_id_number != "not_found":
        c.drawString(50, y, f"Applicant ID Number: {applicant_id_number}")

    y -= 18
    c.drawString(50, y, f"IFSC Code: {bank_name[:4].upper()}0001234")
    c.drawString(340, y, f"Currency: INR (₹)")

    # Transactions Table Header
    y -= 25
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.rect(30, y - 5, width - 60, 20, stroke=1, fill=1)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y + 2, "DATE")
    c.drawString(110, y + 2, "TRANSACTION DESCRIPTION")
    c.drawRightString(370, y + 2, "WITHDRAWAL (DR)")
    c.drawRightString(465, y + 2, "DEPOSIT (CR)")
    c.drawRightString(570, y + 2, "BALANCE")

    # Transaction Rows
    c.setFont("Helvetica", 8)
    for tx in transactions:
        y -= 18
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 8)

        # Highlight salary credits lightly
        is_sal = tx.get("is_salary", False)
        if is_sal:
            c.setFillColor(colors.HexColor("#F0FDF4"))
            c.rect(30, y - 4, width - 60, 16, stroke=0, fill=1)
            c.setFillColor(colors.HexColor("#14532D"))
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)

        date_val = str(tx.get("date", ""))
        desc_val = str(tx.get("description", ""))[:35]
        dr_val = f"{float(tx['debit']):,.2f}" if tx.get("debit", 0) > 0 else "-"
        cr_val = f"{float(tx['credit']):,.2f}" if tx.get("credit", 0) > 0 else "-"
        bal_val = f"{float(tx.get('balance', 0)):,.2f}"

        c.drawString(40, y, date_val)
        c.drawString(110, y, desc_val)
        c.drawRightString(370, y, dr_val)
        c.drawRightString(465, y, cr_val)
        c.drawRightString(570, y, bal_val)

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(40, 30, "Strictly synthetic financial data generated for AI verification testing. Not a real bank instrument.")

    c.save()
    return file_path
