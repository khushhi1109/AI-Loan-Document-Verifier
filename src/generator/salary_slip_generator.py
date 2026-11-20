"""
Synthetic Salary Slip Generator using ReportLab.
Renders itemized earnings and deductions with structured line items.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_salary_slip_pdf(
    file_path: str,
    employer_name: str,
    applicant_name: str,
    slip_id: str,
    pay_period: str,  # "2023-10"
    pay_month_name: str,  # "October 2023"
    dob_str: str,
    designation: str = "Senior Software Engineer",
    gross_pay: float = 95000.0,
    deductions: float = 15000.0,
    net_pay: float = 80000.0,
    applicant_id_number: str = "not_found"
) -> str:
    """Generates an authentic synthetic corporate salary slip PDF."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Outer border
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(1.5)
    c.rect(40, 40, width - 80, height - 80)

    # Employer Header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(40, height - 110, width - 80, 70, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, height - 70, employer_name.upper())
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 90, f"PAYSLIP FOR THE MONTH OF: {pay_month_name.upper()} (Period: {pay_period})")

    # Employee Information Block
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    y = height - 140
    c.drawString(60, y, f"Employee ID: {slip_id}")
    c.drawString(320, y, f"Pay Period: {pay_period}")

    y -= 20
    c.drawString(60, y, f"Employee Name: {applicant_name}")
    c.drawString(320, y, f"Designation: {designation}")

    y -= 20
    if applicant_id_number != "not_found":
        c.drawString(60, y, f"Applicant ID Number: {applicant_id_number}")

    y -= 20
    c.drawString(60, y, f"Date of Birth: {dob_str}")
    c.drawString(320, y, f"Bank Account: XXXXXXXXXX4455")

    # Separator
    y -= 15
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1)
    c.line(60, y, width - 60, y)

    # Earnings & Deductions breakdown
    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.drawString(60, y, "EARNINGS BREAKDOWN")
    c.drawString(320, y, "DEDUCTIONS BREAKDOWN")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)

    basic = gross_pay * 0.50
    hra = gross_pay * 0.30
    special = gross_pay - basic - hra

    pf = deductions * 0.80
    tax = deductions - pf

    y -= 22
    c.drawString(60, y, f"Basic Salary: Rs. {basic:,.2f}")
    c.drawString(320, y, f"Provident Fund (PF): Rs. {pf:,.2f}")

    y -= 20
    c.drawString(60, y, f"House Rent Allowance (HRA): Rs. {hra:,.2f}")
    c.drawString(320, y, f"Professional Tax: Rs. {tax:,.2f}")

    y -= 20
    c.drawString(60, y, f"Special Allowance: Rs. {special:,.2f}")

    # Totals Section
    y -= 25
    c.line(60, y, width - 60, y)
    
    y -= 22
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, f"Gross Pay: Rs. {gross_pay:,.2f}")
    c.drawString(320, y, f"Total Deductions: Rs. {deductions:,.2f}")

    # Net Pay Box
    y -= 45
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(60, y - 5, width - 120, 35, stroke=1, fill=1)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(80, y + 8, f"NET SALARY PAYABLE: Rs. {net_pay:,.2f}")

    # Footer note
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(60, 60, "Computer generated payslip. No physical signature required. Synthetic document for system testing.")

    c.save()
    return file_path
