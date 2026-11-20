"""
Hard Stress-Test Dataset Generator: 15 challenging applicant packets (APP_061 to APP_075)
with noisy layouts, alternative document formats, and missing/unreadable fields.
Provides an honest assessment of system performance and operational boundaries.
"""

import os
import json
import random
from typing import Optional
from datetime import datetime, timedelta
from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from src.config import CONFIG

fake = Faker("en_IN")
Faker.seed(101)
random.seed(101)

COMPANIES = [
    ("Infosys Limited", "INFOSYS TECH"),
    ("Tata Consultancy Services", "TCS"),
    ("Wipro Technologies", "WIPRO"),
    ("HCL Technologies", "HCL TECH"),
    ("Cognizant Technology Solutions", "COGNIZANT"),
    ("Larsen & Toubro Infotech", "L&T TECH")
]

BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank"]

PAY_PERIODS = [
    ("2023-10", "October 2023", "2023-10-31"),
    ("2023-11", "November 2023", "2023-11-30"),
    ("2023-12", "December 2023", "2023-12-31")
]

def generate_noisy_id_pdf(file_path: str, id_type: str, id_number: str, applicant_name: str, dob_str: str):
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setStrokeColor(colors.HexColor("#334155"))
    c.setLineWidth(1.5)
    c.rect(40, height - 280, 520, 220)

    # Header banner
    if id_type.upper() == "AADHAAR":
        c.setFillColor(colors.HexColor("#7C2D12"))  # Deep red/brown for Aadhaar
        c.rect(40, height - 100, 520, 40, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, height - 78, "GOVERNMENT OF INDIA / UIDAI")
        c.setFont("Helvetica", 8)
        c.drawString(60, height - 92, "UNIQUE IDENTIFICATION AUTHORITY OF INDIA - AADHAAR CARD")
    else:
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(40, height - 100, 520, 40, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, height - 78, "INCOME TAX DEPARTMENT - GOVT. OF INDIA")
        c.setFont("Helvetica", 8)
        c.drawString(60, height - 92, "PERMANENT ACCOUNT NUMBER CARD")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)

    y = height - 130
    c.drawString(60, y, f"ID Type: {id_type.upper()}")

    y -= 22
    if id_type.upper() == "AADHAAR":
        c.drawString(60, y, f"Aadhaar Number: {id_number}")
    else:
        c.drawString(60, y, f"Permanent Account Number: {id_number}")

    y -= 22
    c.drawString(60, y, f"Applicant Name: {applicant_name}")

    y -= 22
    if dob_str:
        c.drawString(60, y, f"Date of Birth: {dob_str}")
    else:
        # Intentionally missing field
        pass

    y -= 22
    c.drawString(60, y, "Gender: MALE / FEMALE")

    c.save()

def generate_noisy_salary_slip_pdf(
    file_path: str,
    employer_name: str,
    applicant_name: str,
    slip_id: str,
    pay_period: str,
    pay_month_name: str,
    dob_str: Optional[str],
    gross_pay: float,
    deductions: float,
    net_pay: float,
    currency_label: str = "INR",
    omit_dob: bool = False
):
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Outer border
    c.setStrokeColor(colors.HexColor("#475569"))
    c.setLineWidth(1)
    c.rect(35, 35, width - 70, height - 70)

    # Employer Header
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(35, height - 105, width - 70, 70, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(55, height - 68, employer_name.upper())
    c.setFont("Helvetica", 9)
    if pay_period:
        c.drawString(55, height - 88, f"PAYSLIP FOR THE MONTH OF: {pay_month_name.upper()} (Period: {pay_period})")
    else:
        c.drawString(55, height - 88, "PAYSLIP FOR THE MONTH OF: UNKNOWN (Period: not_found)")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    y = height - 135
    c.drawString(55, y, f"Employee ID: {slip_id}")
    if pay_period:
        c.drawString(320, y, f"Pay Period: {pay_period}")

    y -= 20
    c.drawString(55, y, f"Employee Name: {applicant_name}")
    c.drawString(320, y, "Department: Engineering Operations")

    if not omit_dob and dob_str:
        y -= 20
        c.drawString(55, y, f"Date of Birth: {dob_str}")
        c.drawString(320, y, "Designation: Consultant / Analyst")
    else:
        y -= 20
        c.drawString(320, y, "Designation: Consultant / Analyst")

    y -= 25
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(55, y, width - 55, y)

    # Earnings block
    y -= 30
    c.drawString(55, y, f"Gross Pay: {currency_label} {gross_pay:,.2f}")
    c.drawString(320, y, f"Total Deductions: {currency_label} {deductions:,.2f}")

    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, y, f"NET SALARY PAYABLE: {currency_label} {net_pay:,.2f}")

    c.save()

def generate_noisy_bank_statement_pdf(
    file_path: str,
    bank_name: str,
    account_holder: str,
    account_number: str,
    transactions: list,
    dob_str: Optional[str] = "15/08/1990",
    date_format_dmy: bool = False
):
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Bank Header Banner
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(30, height - 90, width - 60, 60, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, height - 60, bank_name.upper())
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 78, "ACCOUNT STATEMENT — ELECTRONIC ADVICE")

    # Profile Block
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    y = height - 115
    c.drawString(50, y, f"Account Holder Name: {account_holder}")
    c.drawString(340, y, f"Account Number: {account_number}")

    y -= 18
    c.drawString(50, y, "Account Type: Current / Privileged Savings")
    if dob_str:
        c.drawString(340, y, f"Date of Birth: {dob_str}")

    # Transactions Table Header
    y -= 25
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.rect(30, y - 5, width - 60, 20, stroke=1, fill=1)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(40, y + 2, "TRANSACTION DATE")
    c.drawString(150, y + 2, "PARTICULARS / NARRATION")
    c.drawRightString(390, y + 2, "WITHDRAWALS (DR)")
    c.drawRightString(475, y + 2, "DEPOSITS (CR)")
    c.drawRightString(570, y + 2, "RUNNING BALANCE")

    y -= 18
    c.setFont("Helvetica", 8)
    for tx in transactions:
        t_date = tx["date"]
        if date_format_dmy:
            try:
                dt_obj = datetime.strptime(t_date, "%Y-%m-%d")
                t_date = dt_obj.strftime("%d-%b-%Y")
            except Exception:
                pass

        c.drawString(40, y, t_date)
        c.drawString(150, y, tx["description"][:38])
        dr_str = f"{tx['debit']:,.2f}" if tx["debit"] > 0 else "-"
        cr_str = f"{tx['credit']:,.2f}" if tx["credit"] > 0 else "-"
        bal_str = f"{tx['balance']:,.2f}"

        c.drawRightString(390, y, dr_str)
        c.drawRightString(475, y, cr_str)
        c.drawRightString(570, y, bal_str)
        y -= 16

    c.save()

def generate_hard_packets(base_dir: str = None) -> str:
    """Generates all 15 hard stress-test packets (APP_061 to APP_075)."""
    base_dir = base_dir or CONFIG.PACKETS_DIR
    os.makedirs(base_dir, exist_ok=True)
    hard_gt_path = os.path.join(CONFIG.DATA_DIR, "hard_ground_truth.json")

    hard_ground_truth = []

    # 15 challenging packet specifications
    specs = [
        # APP_061: Aadhaar ID format + swapped name order (Clean / Hard Negative)
        {
            "id": "APP_061",
            "is_clean": True,
            "is_hard_negative": True,
            "hn_type": "swapped_name_order",
            "name_id": "Pillai Anand",
            "name_slips": "Anand Pillai",
            "name_bank": "Anand Pillai",
            "id_type": "AADHAAR",
            "id_num": "9876 5432 1098",
            "dob": "14/07/1986",
            "comp": "Infosys Limited",
            "bank": "HDFC Bank",
            "gross": 130000.0, "ded": 15000.0, "net": 115000.0,
            "date_dmy": False,
            "currency": "Rs.",
            "planted": []
        },
        # APP_062: "INR" currency label on slips + CMS narration syntax (Clean)
        {
            "id": "APP_062",
            "is_clean": True,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Pooja Deshmukh",
            "name_slips": "Pooja Deshmukh",
            "name_bank": "Pooja Deshmukh",
            "id_type": "PAN",
            "id_num": "PDSHK4455A",
            "dob": "22/11/1992",
            "comp": "Tata Consultancy Services",
            "bank": "ICICI Bank",
            "gross": 110000.0, "ded": 12000.0, "net": 98000.0,
            "date_dmy": False,
            "currency": "INR",
            "planted": []
        },
        # APP_063: Missing DOB in Salary Slips #2 and #3 (Clean - optional field missing)
        {
            "id": "APP_063",
            "is_clean": True,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Devendra Joshi",
            "name_slips": "Devendra Joshi",
            "name_bank": "Devendra Joshi",
            "id_type": "PAN",
            "id_num": "DJOSH8812K",
            "dob": "10/05/1987",
            "comp": "Wipro Technologies",
            "bank": "Axis Bank",
            "gross": 145000.0, "ded": 20000.0, "net": 125000.0,
            "date_dmy": False,
            "currency": "Rs.",
            "omit_slip_dob": True,
            "planted": []
        },
        # APP_064: Bank statement with DD-Mon-YYYY date format & BY TRANSFER narration (Clean)
        {
            "id": "APP_064",
            "is_clean": True,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Swati Sengupta",
            "name_slips": "Swati Sengupta",
            "name_bank": "Swati Sengupta",
            "id_type": "PAN",
            "id_num": "SSENG3321L",
            "dob": "08/03/1990",
            "comp": "HCL Technologies",
            "bank": "State Bank of India",
            "gross": 125000.0, "ded": 18000.0, "net": 107000.0,
            "date_dmy": True,
            "currency": "INR",
            "planted": []
        },
        # APP_065: Job change with alternative narration format (Clean / Hard Negative)
        {
            "id": "APP_065",
            "is_clean": True,
            "is_hard_negative": True,
            "hn_type": "job_change",
            "name_id": "Girish Hegde",
            "name_slips": "Girish Hegde",
            "name_bank": "Girish Hegde",
            "id_type": "PAN",
            "id_num": "GHEGD9910B",
            "dob": "19/09/1985",
            "comp": "Cognizant Technology Solutions",
            "second_comp": "Infosys Limited",
            "bank": "Kotak Mahindra Bank",
            "gross": 135000.0, "ded": 15000.0, "net": 120000.0,
            "date_dmy": False,
            "currency": "Rs.",
            "planted": []
        },
        # APP_066: Late salary credit with rollover narration (Clean / Hard Negative)
        {
            "id": "APP_066",
            "is_clean": True,
            "is_hard_negative": True,
            "hn_type": "late_salary",
            "name_id": "Tarun Mukherjee",
            "name_slips": "Tarun Mukherjee",
            "name_bank": "Tarun Mukherjee",
            "id_type": "PAN",
            "id_num": "TMUKH7712M",
            "dob": "12/12/1989",
            "comp": "Larsen & Toubro Infotech",
            "bank": "HDFC Bank",
            "gross": 150000.0, "ded": 25000.0, "net": 125000.0,
            "late_days": 16,
            "date_dmy": False,
            "currency": "INR",
            "planted": []
        },
        # APP_067: Initials on Aadhaar card vs Full Name (Clean / Hard Negative)
        {
            "id": "APP_067",
            "is_clean": True,
            "is_hard_negative": True,
            "hn_type": "initials_vs_fullname",
            "name_id": "V. K. Singhania",
            "name_slips": "Vijay Kumar Singhania",
            "name_bank": "Vijay Kumar Singhania",
            "id_type": "AADHAAR",
            "id_num": "7812 3456 9012",
            "dob": "04/04/1983",
            "comp": "Tata Consultancy Services",
            "bank": "ICICI Bank",
            "gross": 160000.0, "ded": 25000.0, "net": 135000.0,
            "date_dmy": False,
            "currency": "Rs.",
            "planted": []
        },
        # APP_068: Planted Name Mismatch in noisy slip #1 (Mismatch)
        {
            "id": "APP_068",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Priya Nair",
            "name_slips": "Priya Nair",
            "planted_slip_1_name": "Rohan Saxena",
            "name_bank": "Priya Nair",
            "id_type": "PAN",
            "id_num": "PNAIR5512N",
            "dob": "25/01/1991",
            "comp": "Infosys Limited",
            "bank": "Axis Bank",
            "gross": 120000.0, "ded": 15000.0, "net": 105000.0,
            "date_dmy": False,
            "currency": "INR",
            "planted": [{
                "type": "name_mismatch",
                "description": "Salary slip #1 name 'Rohan Saxena' conflicts with ID proof 'Priya Nair'",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "Rohan Saxena"
            }]
        },
        # APP_069: Planted DOB Mismatch with mixed date formats (Mismatch)
        {
            "id": "APP_069",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Kunal Kapoor",
            "name_slips": "Kunal Kapoor",
            "name_bank": "Kunal Kapoor",
            "id_type": "PAN",
            "id_num": "KKAPO1122C",
            "dob": "15/08/1991",
            "planted_slip_1_dob": "1986-04-12",
            "comp": "Wipro Technologies",
            "bank": "HDFC Bank",
            "gross": 130000.0, "ded": 18000.0, "net": 112000.0,
            "date_dmy": False,
            "currency": "Rs.",
            "planted": [{
                "type": "dob_mismatch",
                "description": "Salary slip #1 DOB '1986-04-12' conflicts with ID proof '15/08/1991'",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "1986-04-12"
            }]
        },
        # APP_070: Planted Salary Gap under INR notation (Mismatch)
        {
            "id": "APP_070",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Sunita Rao",
            "name_slips": "Sunita Rao",
            "name_bank": "Sunita Rao",
            "id_type": "PAN",
            "id_num": "SRAOO6677D",
            "dob": "17/02/1988",
            "comp": "HCL Technologies",
            "bank": "ICICI Bank",
            "gross": 140000.0, "ded": 20000.0, "net": 120000.0,
            "planted_gap_amt": 92000.0,
            "date_dmy": False,
            "currency": "INR",
            "planted": [{
                "type": "salary_gap",
                "description": "Net pay on salary slip #1 is ₹120,000.00 but bank credit is only ₹92,000.00",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "₹92,000.00"
            }]
        },
        # APP_071: Planted Missing Month Credit in noisy bank statement (Mismatch)
        {
            "id": "APP_071",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Abhinav Bhasin",
            "name_slips": "Abhinav Bhasin",
            "name_bank": "Abhinav Bhasin",
            "id_type": "PAN",
            "id_num": "ABHAS8899E",
            "dob": "30/10/1987",
            "comp": "Cognizant Technology Solutions",
            "bank": "State Bank of India",
            "gross": 115000.0, "ded": 15000.0, "net": 100000.0,
            "skip_month_idx": 1,
            "date_dmy": True,
            "currency": "Rs.",
            "planted": [{
                "type": "missing_month",
                "description": "Salary credit for November 2023 missing from bank statement",
                "target_document": "bank_statement.pdf",
                "planted_value": "missing_credit_nov"
            }]
        },
        # APP_072: Planted Employer Mismatch in noisy narration (Mismatch)
        {
            "id": "APP_072",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Meera Venkat",
            "name_slips": "Meera Venkat",
            "name_bank": "Meera Venkat",
            "id_type": "PAN",
            "id_num": "MVENK3344F",
            "dob": "11/06/1993",
            "comp": "Tata Consultancy Services",
            "unrelated_emp": "RELIANCE JIO INFOCOMM",
            "bank": "Axis Bank",
            "gross": 125000.0, "ded": 15000.0, "net": 110000.0,
            "date_dmy": False,
            "currency": "INR",
            "planted": [{
                "type": "employer_mismatch",
                "description": "Salary slip claims 'Tata Consultancy Services' but bank deposit is from 'RELIANCE JIO INFOCOMM'",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "RELIANCE JIO INFOCOMM"
            }]
        },
        # APP_073: Planted Edited / Tampered Slip Math (Mismatch)
        {
            "id": "APP_073",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Deepak Chawla",
            "name_slips": "Deepak Chawla",
            "name_bank": "Deepak Chawla",
            "id_type": "PAN",
            "id_num": "DCHAW9900G",
            "dob": "05/09/1984",
            "comp": "Larsen & Toubro Infotech",
            "bank": "HDFC Bank",
            "gross": 140000.0, "ded": 15000.0, "net": 125000.0,
            "tampered_net": 138000.0,  # 13k higher than gross - ded
            "date_dmy": False,
            "currency": "Rs.",
            "planted": [{
                "type": "edited_duplicate_slip",
                "description": "Salary slip #1 arithmetic tampering: gross - deductions != stated net",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "tampered_net_138000.0"
            }]
        },
        # APP_074: Missing Essential Field — Applicant Name on ID is unreadable (Honest Limit)
        {
            "id": "APP_074",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "not_found",  # Unreadable / missing field on ID!
            "name_slips": "Siddharth Jain",
            "name_bank": "Siddharth Jain",
            "id_type": "PAN",
            "id_num": "SJAIN1144H",
            "dob": "18/12/1990",
            "comp": "Infosys Limited",
            "bank": "ICICI Bank",
            "gross": 130000.0, "ded": 15000.0, "net": 115000.0,
            "date_dmy": False,
            "currency": "INR",
            "planted": [{
                "type": "name_mismatch",
                "description": "Applicant Name could not be extracted from ID document (missing critical field)",
                "target_document": "id_document.pdf",
                "planted_value": "not_found"
            }]
        },
        # APP_075: Missing Essential Field — Salary Slip Pay Period is unreadable (Honest Limit)
        {
            "id": "APP_075",
            "is_clean": False,
            "is_hard_negative": False,
            "hn_type": None,
            "name_id": "Ananya Sen",
            "name_slips": "Ananya Sen",
            "name_bank": "Ananya Sen",
            "id_type": "PAN",
            "id_num": "ASENN7788J",
            "dob": "21/04/1992",
            "comp": "Wipro Technologies",
            "bank": "Kotak Mahindra Bank",
            "gross": 120000.0, "ded": 15000.0, "net": 105000.0,
            "omit_pay_period": True,  # Missing critical pay period!
            "date_dmy": False,
            "currency": "Rs.",
            "planted": [{
                "type": "missing_month",
                "description": "Salary slip pay period unreadable; bank credit cannot be reconciled",
                "target_document": "salary_slip_1.pdf",
                "planted_value": "missing_period"
            }]
        }
    ]

    for spec in specs:
        app_id = spec["id"]
        app_dir = os.path.join(base_dir, app_id)
        os.makedirs(app_dir, exist_ok=True)

        comp_name = spec["comp"]
        comp_short = [c[1] for c in COMPANIES if c[0] == comp_name][0]
        acc_num = f"50100{random.randint(10000000, 99999999)}"

        # 1. ID PDF
        generate_noisy_id_pdf(
            file_path=os.path.join(app_dir, "id_document.pdf"),
            id_type=spec["id_type"],
            id_number=spec["id_num"],
            applicant_name=spec["name_id"],
            dob_str=spec["dob"]
        )

        # 2. 3 Salary Slips PDF
        for m_idx, (p_code, p_name, _) in enumerate(PAY_PERIODS):
            slip_path = os.path.join(app_dir, f"salary_slip_{m_idx+1}.pdf")
            slip_name = spec.get("planted_slip_1_name") if (m_idx == 0 and "planted_slip_1_name" in spec) else spec["name_slips"]
            slip_dob = spec.get("planted_slip_1_dob") if (m_idx == 0 and "planted_slip_1_dob" in spec) else spec["dob"]
            slip_emp = spec.get("second_comp") if (m_idx == 2 and "second_comp" in spec) else comp_name
            net_amt = spec.get("tampered_net") if (m_idx == 0 and "tampered_net" in spec) else spec["net"]
            omit_dob_flag = spec.get("omit_slip_dob", False) and m_idx > 0
            p_code_val = None if (m_idx == 0 and spec.get("omit_pay_period")) else p_code

            generate_noisy_salary_slip_pdf(
                file_path=slip_path,
                employer_name=slip_emp,
                applicant_name=slip_name,
                slip_id=f"EMP_{app_id[-3:]}_{m_idx+1}",
                pay_period=p_code_val,
                pay_month_name=p_name,
                dob_str=slip_dob,
                gross_pay=spec["gross"],
                deductions=spec["ded"],
                net_pay=net_amt,
                currency_label=spec.get("currency", "INR"),
                omit_dob=omit_dob_flag
            )

        # 3. Bank Statement PDF
        txs = []
        balance = 150000.0
        late_days = spec.get("late_days", 0)
        skip_m = spec.get("skip_month_idx")

        for m_idx, (p_code, p_name, end_date_str) in enumerate(PAY_PERIODS):
            p_date = datetime.strptime(end_date_str, "%Y-%m-%d")

            # Routine debit
            txs.append({
                "date": (p_date - timedelta(days=15)).strftime("%Y-%m-%d"),
                "description": "UPI/ZOMATO/FOOD",
                "debit": 2800.0,
                "credit": 0.0,
                "balance": balance - 2800.0,
                "is_salary": False
            })
            balance -= 2800.0

            if skip_m == m_idx:
                continue

            credit_date = p_date + timedelta(days=late_days)
            credit_amt = spec.get("planted_gap_amt") if (m_idx == 0 and "planted_gap_amt" in spec) else spec["net"]

            if "unrelated_emp" in spec and m_idx == 0:
                narration = f"CMS/{spec['unrelated_emp']}/SALARY"
            elif m_idx == 2 and "second_comp" in spec:
                narration = "NEFT CR - INFOSYS TECH PAYROLL"
            else:
                narration = f"BY TRANSFER-NEFT: {comp_short} SALARY"

            balance += credit_amt
            txs.append({
                "date": credit_date.strftime("%Y-%m-%d"),
                "description": narration,
                "debit": 0.0,
                "credit": credit_amt,
                "balance": balance,
                "is_salary": True
            })

        generate_noisy_bank_statement_pdf(
            file_path=os.path.join(app_dir, "bank_statement.pdf"),
            bank_name=spec["bank"],
            account_holder=spec["name_bank"],
            account_number=acc_num,
            transactions=txs,
            dob_str=spec["dob"],
            date_format_dmy=spec.get("date_dmy", False)
        )

        # Build ground truth entry
        entry = {
            "applicant_id": app_id,
            "is_clean": spec["is_clean"],
            "is_hard_negative": spec["is_hard_negative"],
            "hard_negative_type": spec["hn_type"],
            "is_hard_test_set": True,
            "planted_mismatches": spec["planted"],
            "expected_fields": {
                "id_document": {
                    "id_type": spec["id_type"],
                    "id_number": spec["id_num"],
                    "applicant_name": spec["name_id"],
                    "date_of_birth": spec["dob"]
                },
                "salary_slips": [
                    {
                        "employer_name": spec.get("second_comp") if (m == 2 and "second_comp" in spec) else comp_name,
                        "applicant_name": spec.get("planted_slip_1_name") if (m == 0 and "planted_slip_1_name" in spec) else spec["name_slips"],
                        "slip_id": f"EMP_{app_id[-3:]}_{m+1}",
                        "pay_period": PAY_PERIODS[m][0],
                        "pay_month_name": PAY_PERIODS[m][1],
                        "gross_pay": spec["gross"],
                        "deductions": spec["ded"],
                        "net_pay": spec.get("tampered_net") if (m == 0 and "tampered_net" in spec) else spec["net"],
                        "date_of_birth": spec.get("planted_slip_1_dob") if (m == 0 and "planted_slip_1_dob" in spec) else (None if (spec.get("omit_slip_dob") and m > 0) else spec["dob"])
                    }
                    for m in range(3)
                ],
                "bank_statement": {
                    "bank_name": spec["bank"],
                    "account_holder": spec["name_bank"],
                    "account_number": acc_num,
                    "date_of_birth": spec["dob"]
                }
            }
        }
        hard_ground_truth.append(entry)

    with open(hard_gt_path, "w", encoding="utf-8") as f:
        json.dump(hard_ground_truth, f, indent=2)

    return hard_gt_path
