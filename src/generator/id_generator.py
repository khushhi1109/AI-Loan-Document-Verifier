"""
Synthetic ID Proof Generator (PAN / Aadhaar) using ReportLab.
Strictly synthetic data only.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_id_pdf(
    file_path: str,
    applicant_name: str,
    dob_str: str,
    id_type: str = "PAN",
    id_number: str = "ABCDE1234F",
    father_name: str = "Suresh Sharma"
) -> str:
    """Generates a synthetic government ID card PDF with structured text lines."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Card border (approx ID card dimensions scaled on page)
    c.setStrokeColor(colors.HexColor("#1E3A8A"))
    c.setLineWidth(2)
    c.rect(50, height - 260, 500, 200, stroke=1, fill=0)

    # Header banner
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.rect(50, height - 100, 500, 40, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    if id_type.upper() == "PAN":
        c.drawString(70, height - 80, "INCOME TAX DEPARTMENT - GOVT. OF INDIA")
        c.setFont("Helvetica", 9)
        c.drawString(70, height - 95, "PERMANENT ACCOUNT NUMBER CARD (SYNTHETIC SPECIMEN)")
    else:
        c.drawString(70, height - 80, "UNIQUE IDENTIFICATION AUTHORITY OF INDIA")
        c.setFont("Helvetica", 9)
        c.drawString(70, height - 95, "AADHAAR CARD (SYNTHETIC SPECIMEN)")

    # Body fields
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    
    y = height - 130
    c.drawString(70, y, f"ID Type: {id_type.upper()}")
    
    y -= 22
    c.drawString(70, y, f"Permanent Account Number: {id_number}")

    y -= 22
    c.drawString(70, y, f"Applicant Name: {applicant_name}")

    y -= 22
    c.drawString(70, y, f"Father's Name: {father_name}")

    y -= 22
    c.drawString(70, y, f"Date of Birth: {dob_str}")

    y -= 22
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(70, y, "Notice: Strictly synthetic test document generated for automated underwriter verification.")

    c.save()
    return file_path
