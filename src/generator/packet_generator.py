"""
Synthetic Dataset Orchestrator: generates 80 synthetic applicant packets
(40 clean with hard negatives, 40 with planted mismatches) and ground_truth.json.
"""

import os
import json
import random
from datetime import datetime, timedelta
from faker import Faker
from src.config import CONFIG
from src.generator.id_generator import generate_id_pdf
from src.generator.salary_slip_generator import generate_salary_slip_pdf
from src.generator.bank_statement_generator import generate_bank_statement_pdf

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

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

def generate_random_pan() -> str:
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    digits = "".join(random.choices("0123456789", k=4))
    last = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{letters}{digits}{last}"

def generate_transactions(
    employer_short: str,
    net_pay: float,
    months=PAY_PERIODS,
    late_days=0,
    planted_gap_month=None,
    gap_amount=None,
    skip_month=None,
    mismatch_employer_narration=None
):
    txs = []
    balance = 120000.0
    
    # Routine monthly expenses
    for m_idx, (period, p_name, end_date_str) in enumerate(months):
        p_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Add a couple of grocery/utility debits
        txs.append({
            "date": (p_date - timedelta(days=20)).strftime("%Y-%m-%d"),
            "description": "UPI/SWIGGY/GROCERY",
            "debit": 3200.0,
            "credit": 0.0,
            "balance": balance - 3200.0,
            "is_salary": False
        })
        balance -= 3200.0

        txs.append({
            "date": (p_date - timedelta(days=10)).strftime("%Y-%m-%d"),
            "description": "NEFT/HOUSE RENT",
            "debit": 25000.0,
            "credit": 0.0,
            "balance": balance - 25000.0,
            "is_salary": False
        })
        balance -= 25000.0

        # Salary credit
        if skip_month == m_idx:
            # Planted missing month credit!
            continue

        credit_date = p_date + timedelta(days=late_days)
        credit_amt = net_pay
        if planted_gap_month == m_idx and gap_amount is not None:
            credit_amt = gap_amount

        narration = f"ACH CR {employer_short} SALARY"
        if mismatch_employer_narration and m_idx == 0:
            narration = f"ACH CR {mismatch_employer_narration} SALARY"

        balance += credit_amt
        txs.append({
            "date": credit_date.strftime("%Y-%m-%d"),
            "description": narration,
            "debit": 0.0,
            "credit": credit_amt,
            "balance": balance,
            "is_salary": True
        })

    return txs

def generate_all_packets(base_dir: str = None) -> str:
    """Generates all 60 synthetic applicant packets and ground_truth.json."""
    base_dir = base_dir or CONFIG.PACKETS_DIR
    ground_truth_path = CONFIG.GROUND_TRUTH_PATH
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(ground_truth_path)), exist_ok=True)

    ground_truth = []

    for i in range(1, 81):
        packet_number = i if i <= 60 else i + 15
        app_id = f"APP_{packet_number:03d}"
        app_dir = os.path.join(base_dir, app_id)
        os.makedirs(app_dir, exist_ok=True)

        # Base applicant profile
        first_name = fake.first_name()
        last_name = fake.last_name()
        primary_name = f"{first_name} {last_name}"
        dob_dt = fake.date_of_birth(minimum_age=24, maximum_age=55)
        dob_str = dob_dt.strftime("%d/%m/%Y")
        pan_no = generate_random_pan()
        father_name = f"{fake.first_name_male()} {last_name}"
        
        comp_name, comp_short = random.choice(COMPANIES)
        bank_name = random.choice(BANKS)
        acc_num = f"50100{random.randint(10000000, 99999999)}"

        gross_pay = float(random.randint(70, 160) * 1000)
        deductions = float(random.randint(10, 25) * 1000)
        net_pay = gross_pay - deductions

        # Document attributes initialized
        id_name = primary_name
        slip_names = [primary_name, primary_name, primary_name]
        bank_holder_name = primary_name
        
        slip_dobs = [dob_str, dob_str, dob_str]
        bank_dob = dob_str

        slip_employers = [comp_name, comp_name, comp_name]
        slip_gross = [gross_pay, gross_pay, gross_pay]
        slip_ded = [deductions, deductions, deductions]
        slip_net = [net_pay, net_pay, net_pay]
        slip_ids = [f"EMP{packet_number:03d}_{m+1}" for m in range(3)]

        is_clean = i <= 30 or 61 <= i <= 70
        is_hard_negative = False
        hn_type = None
        planted_mismatches = []

        late_days = 0
        planted_gap_m = None
        gap_amt = None
        skip_m = None
        mismatch_narr = None

        if is_clean:
            # Original clean packets with hard negatives
            if 1 <= i <= 5:
                # HN 1: Initials vs Full Name
                is_hard_negative = True
                hn_type = "initials_vs_fullname"
                initial = first_name[0]
                id_name = f"{initial}. {last_name}"
                slip_names = [primary_name, primary_name, primary_name]
                bank_holder_name = primary_name
            elif 6 <= i <= 10:
                # HN 2: Mohammed vs Mohammad
                is_hard_negative = True
                hn_type = "mohammed_spelling"
                id_name = f"Mohammed {last_name}"
                slip_names = [f"Mohammad {last_name}"] * 3
                bank_holder_name = f"Mohammad {last_name}"
            elif 11 <= i <= 15:
                # HN 3: Salary Credited Late (e.g. 10 days late into next month)
                is_hard_negative = True
                hn_type = "late_salary"
                late_days = 11
            elif 16 <= i <= 20:
                # HN 4: Genuine Job Change (Months 1 & 2 at Comp A, Month 3 at Comp B)
                is_hard_negative = True
                hn_type = "job_change"
                second_comp, second_short = COMPANIES[(COMPANIES.index((comp_name, comp_short)) + 1) % len(COMPANIES)]
                slip_employers[2] = second_comp
            elif 21 <= i <= 25:
                # HN 5: Swapped Name Order
                is_hard_negative = True
                hn_type = "swapped_name_order"
                id_name = f"{last_name} {first_name}"
                slip_names = [primary_name, primary_name, primary_name]
                bank_holder_name = primary_name
            elif 61 <= i <= 70:
                # Paired spelling/order hard negatives appear in both evaluation splits.
                spelling_variants = [
                    ("Khushi", "Khusi", "khushi_vs_khusi"),
                    ("Shivani", "Sivani", "shivani_vs_sivani"),
                    ("Mohammed", "Muhammad", "mohammed_vs_muhammad"),
                    ("Vijay", "Vijaya", "vijay_vs_vijaya"),
                    (None, None, "surname_first_order"),
                ]
                name_from_id, name_from_documents, hn_type = spelling_variants[(i - 61) // 2]
                is_hard_negative = True
                if hn_type == "surname_first_order":
                    id_name = f"{last_name} {first_name}"
                    name_from_documents = primary_name
                else:
                    id_name = f"{name_from_id} {last_name}"
                    name_from_documents = f"{name_from_documents} {last_name}"
                slip_names = [name_from_documents] * 3
                bank_holder_name = name_from_documents
            else:
                # 26 to 30: Standard pure clean packets
                pass
        else:
            # 30 Planted Mismatch packets (indices 31 to 60)
            if 31 <= i <= 35:
                # Mismatch 1: Name Mismatch
                fake_other = f"{fake.first_name()} {fake.last_name()}"
                slip_names[0] = fake_other
                planted_mismatches.append({
                    "type": "name_mismatch",
                    "description": f"Salary slip #1 name '{fake_other}' conflicts with ID proof '{primary_name}'",
                    "target_document": "salary_slip_1.pdf",
                    "planted_value": fake_other
                })
            elif 36 <= i <= 40:
                # Mismatch 2: DOB Mismatch
                wrong_dob = (dob_dt + timedelta(days=1825)).strftime("%d/%m/%Y")
                slip_dobs[0] = wrong_dob
                planted_mismatches.append({
                    "type": "dob_mismatch",
                    "description": f"Salary slip #1 DOB '{wrong_dob}' conflicts with ID proof '{dob_str}'",
                    "target_document": "salary_slip_1.pdf",
                    "planted_value": wrong_dob
                })
            elif 41 <= i <= 45:
                # Mismatch 3: Salary vs Bank Credit Gap
                planted_gap_m = 0
                gap_amt = net_pay - 22000.0  # Significant deficit
                planted_mismatches.append({
                    "type": "salary_gap",
                    "description": f"Net pay on salary slip #1 is ₹{net_pay:,.2f} but bank credit is only ₹{gap_amt:,.2f}",
                    "target_document": "salary_slip_1.pdf",
                    "planted_value": f"₹{gap_amt:,.2f}"
                })
            elif 46 <= i <= 50:
                # Mismatch 4: Missing Month Credit
                skip_m = 1  # November credit missing
                planted_mismatches.append({
                    "type": "missing_month",
                    "description": "Salary credit for November 2023 missing from bank statement",
                    "target_document": "bank_statement.pdf",
                    "planted_value": "missing_credit_nov"
                })
            elif 51 <= i <= 55:
                # Mismatch 5: Employer Mismatch
                unrelated_emp = "RELIANCE RETAIL VENTURES"
                mismatch_narr = unrelated_emp
                planted_mismatches.append({
                    "type": "employer_mismatch",
                    "description": f"Salary slip claims '{comp_name}' but bank deposit is from '{unrelated_emp}'",
                    "target_document": "salary_slip_1.pdf",
                    "planted_value": unrelated_emp
                })
            elif 56 <= i <= 60:
                # Mismatch 6: Edited / Duplicate Slip (Math tampering or duplicate slip ID)
                if i % 2 == 0:
                    # Tampered arithmetic: stated net is 15k higher than gross - ded
                    slip_net[0] = (slip_gross[0] - slip_ded[0]) + 15000.0
                    planted_mismatches.append({
                        "type": "edited_duplicate_slip",
                        "description": "Salary slip #1 arithmetic tampering: gross - deductions != stated net",
                        "target_document": "salary_slip_1.pdf",
                        "planted_value": f"tampered_net_{slip_net[0]}"
                    })
                else:
                    # Duplicate slip ID
                    slip_ids[1] = slip_ids[0]
                    planted_mismatches.append({
                        "type": "edited_duplicate_slip",
                        "description": f"Salary slip #2 re-uses slip ID '{slip_ids[0]}' from slip #1",
                        "target_document": "salary_slip_2.pdf",
                        "planted_value": slip_ids[0]
                    })
            elif 71 <= i <= 80:
                # Additional name mismatches balance the added clean hard negatives.
                fake_other = f"{fake.first_name()} {fake.last_name()}"
                slip_names[0] = fake_other
                planted_mismatches.append({
                    "type": "name_mismatch",
                    "description": f"Salary slip #1 name '{fake_other}' conflicts with ID proof '{primary_name}'",
                    "target_document": "salary_slip_1.pdf",
                    "planted_value": fake_other
                })

        # 1. Generate ID Proof PDF
        id_pdf_path = os.path.join(app_dir, "id_document.pdf")
        generate_id_pdf(
            file_path=id_pdf_path,
            applicant_name=id_name,
            dob_str=dob_str,
            id_type="PAN",
            id_number=pan_no,
            father_name=father_name
        )

        # 2. Generate 3 Salary Slips PDF
        for m_idx, (p_code, p_name, _) in enumerate(PAY_PERIODS):
            slip_path = os.path.join(app_dir, f"salary_slip_{m_idx+1}.pdf")
            generate_salary_slip_pdf(
                file_path=slip_path,
                employer_name=slip_employers[m_idx],
                applicant_name=slip_names[m_idx],
                slip_id=slip_ids[m_idx],
                pay_period=p_code,
                pay_month_name=p_name,
                dob_str=slip_dobs[m_idx],
                gross_pay=slip_gross[m_idx],
                deductions=slip_ded[m_idx],
                net_pay=slip_net[m_idx],
                applicant_id_number=pan_no
            )

        # 3. Generate Bank Statement PDF
        txs = generate_transactions(
            employer_short=comp_short if not (is_hard_negative and hn_type == "job_change") else comp_short,
            net_pay=net_pay,
            late_days=late_days,
            planted_gap_month=planted_gap_m,
            gap_amount=gap_amt,
            skip_month=skip_m,
            mismatch_employer_narration=mismatch_narr
        )
        if is_hard_negative and hn_type == "job_change":
            # Update month 3 transaction to second employer
            if len(txs) >= 3:
                txs[-1]["description"] = f"ACH CR {second_short} SALARY"

        bank_pdf_path = os.path.join(app_dir, "bank_statement.pdf")
        generate_bank_statement_pdf(
            file_path=bank_pdf_path,
            bank_name=bank_name,
            account_holder=bank_holder_name,
            account_number=acc_num,
            transactions=txs,
            dob_str=bank_dob,
            applicant_id_number=pan_no
        )

        # Record Ground Truth Entry
        ground_truth.append({
            "applicant_id": app_id,
            "is_clean": is_clean,
            "is_hard_negative": is_hard_negative,
            "hard_negative_type": hn_type,
            "planted_mismatches": planted_mismatches,
            "expected_fields": {
                "id_document": {
                    "id_type": "PAN",
                    "id_number": pan_no,
                    "applicant_name": id_name,
                    "date_of_birth": dob_str
                },
                "salary_slips": [
                    {
                        "employer_name": slip_employers[m],
                        "applicant_name": slip_names[m],
                        "applicant_id_number": pan_no,
                        "slip_id": slip_ids[m],
                        "pay_period": PAY_PERIODS[m][0],
                        "pay_month_name": PAY_PERIODS[m][1],
                        "gross_pay": slip_gross[m],
                        "deductions": slip_ded[m],
                        "net_pay": slip_net[m],
                        "date_of_birth": slip_dobs[m]
                    }
                    for m in range(3)
                ],
                "bank_statement": {
                    "bank_name": bank_name,
                    "account_holder": bank_holder_name,
                    "account_number": acc_num,
                    "applicant_id_number": pan_no,
                    "date_of_birth": bank_dob
                }
            }
        })

    with open(ground_truth_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    return ground_truth_path
