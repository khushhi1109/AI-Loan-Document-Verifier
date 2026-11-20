"""
Unit tests for all 6 deterministic check functions and hard negatives.
"""

from typing import Any
import pytest
from src.models import (
    ApplicantPacketData,
    IDDocumentData,
    SalarySlipData,
    BankStatementData,
    BankTransaction,
    ExtractedField,
    SourceLocation,
    SeverityLevel
)
from src.checks.name_check import check_name_consistency, are_names_equivalent, phonetic_similarity
from src.checks.dob_check import check_dob_consistency
from src.checks.salary_vs_credit_check import check_salary_vs_bank_credits
from src.checks.missing_credit_check import check_missing_month_credits
from src.checks.employer_check import check_employer_consistency
from src.checks.slip_arithmetic_check import check_slip_arithmetic_and_authenticity

def create_field(val: Any, doc="doc.pdf", page=1, line=1) -> ExtractedField:
    return ExtractedField(
        field_name="field",
        value=val,
        location=SourceLocation(document=doc, page=page, line=line, raw_text=f"Line {line}: {val}")
    )

def make_base_packet(
    applicant_name="Rajesh Sharma",
    employer="Infosys Limited",
    dob="15/08/1990",
    net_pay=75000.0,
    gross_pay=90000.0,
    deductions=15000.0
) -> ApplicantPacketData:
    id_doc = IDDocumentData(
        document_name="PAN_CARD.pdf",
        id_type="PAN",
        id_number=create_field("ABCDE1234F", "PAN_CARD.pdf", 1, 2),
        applicant_name=create_field(applicant_name, "PAN_CARD.pdf", 1, 3),
        date_of_birth=create_field(dob, "PAN_CARD.pdf", 1, 4)
    )

    slips = []
    periods = [("2024-01", "January 2024"), ("2024-02", "February 2024"), ("2024-03", "March 2024")]
    for idx, (p, p_name) in enumerate(periods, start=1):
        slips.append(SalarySlipData(
            document_name=f"SALARY_SLIP_{idx}.pdf",
            slip_id=create_field(f"SLIP_00{idx}", f"SALARY_SLIP_{idx}.pdf", 1, 2),
            applicant_name=create_field(applicant_name, f"SALARY_SLIP_{idx}.pdf", 1, 3),
            employer_name=create_field(employer, f"SALARY_SLIP_{idx}.pdf", 1, 4),
            date_of_birth=create_field(dob, f"SALARY_SLIP_{idx}.pdf", 1, 5),
            pay_period=create_field(p, f"SALARY_SLIP_{idx}.pdf", 1, 6),
            pay_month_name=create_field(p_name, f"SALARY_SLIP_{idx}.pdf", 1, 7),
            gross_pay=create_field(gross_pay, f"SALARY_SLIP_{idx}.pdf", 1, 8),
            deductions=create_field(deductions, f"SALARY_SLIP_{idx}.pdf", 1, 9),
            net_pay=create_field(net_pay, f"SALARY_SLIP_{idx}.pdf", 1, 10)
        ))

    txs = [
        BankTransaction(
            date="2024-01-31",
            description=f"ACH CR {employer.split()[0].upper()} SALARY",
            credit_amount=net_pay,
            balance=150000.0,
            is_salary=True,
            location=SourceLocation(document="BANK_STATEMENT.pdf", page=1, line=10, raw_text="2024-01-31 ACH CR")
        ),
        BankTransaction(
            date="2024-02-29",
            description=f"ACH CR {employer.split()[0].upper()} SALARY",
            credit_amount=net_pay,
            balance=225000.0,
            is_salary=True,
            location=SourceLocation(document="BANK_STATEMENT.pdf", page=1, line=15, raw_text="2024-02-29 ACH CR")
        ),
        BankTransaction(
            date="2024-03-31",
            description=f"ACH CR {employer.split()[0].upper()} SALARY",
            credit_amount=net_pay,
            balance=300000.0,
            is_salary=True,
            location=SourceLocation(document="BANK_STATEMENT.pdf", page=1, line=20, raw_text="2024-03-31 ACH CR")
        )
    ]

    bank = BankStatementData(
        document_name="BANK_STATEMENT.pdf",
        bank_name=create_field("HDFC Bank", "BANK_STATEMENT.pdf", 1, 1),
        account_holder=create_field(applicant_name, "BANK_STATEMENT.pdf", 1, 2),
        account_number=create_field("5010022334455", "BANK_STATEMENT.pdf", 1, 3),
        date_of_birth=create_field(dob, "BANK_STATEMENT.pdf", 1, 4),
        transactions=txs
    )

    return ApplicantPacketData(
        applicant_id="APP_CLEAN_01",
        id_document=id_doc,
        salary_slips=slips,
        bank_statement=bank
    )

# --- 1. NAME CHECK & HARD NEGATIVES ---
def test_name_check_clean():
    packet = make_base_packet("Rajesh Kumar Sharma")
    flags = check_name_consistency(packet)
    assert len(flags) == 0

def test_name_check_hard_negative_initials():
    # ID has initials, slips have full name
    packet = make_base_packet("K. R. Ramanathan")
    for s in packet.salary_slips:
        s.applicant_name.value = "Karthik Ramanathan"
    packet.bank_statement.account_holder.value = "Karthik Ramanathan"

    flags = check_name_consistency(packet)
    assert len(flags) == 0, f"Hard negative Initials vs Full Name must NOT be flagged: {flags}"

def test_name_check_hard_negative_swapped_order():
    # ID has "Sharma Rajesh", slip has "Rajesh Sharma"
    packet = make_base_packet("Sharma Rajesh Kumar")
    for s in packet.salary_slips:
        s.applicant_name.value = "Rajesh Kumar Sharma"
    packet.bank_statement.account_holder.value = "Rajesh Kumar Sharma"

    flags = check_name_consistency(packet)
    assert len(flags) == 0, f"Hard negative swapped order must NOT be flagged: {flags}"

def test_name_check_hard_negative_mohammed_spelling():
    packet = make_base_packet("Mohammed Ibrahim")
    for s in packet.salary_slips:
        s.applicant_name.value = "Mohammad Ibrahim"
    packet.bank_statement.account_holder.value = "Mohammad Ibrahim"

    flags = check_name_consistency(packet)
    assert len(flags) == 0, f"Hard negative Mohammed vs Mohammad must NOT be flagged: {flags}"

@pytest.mark.parametrize(("id_name", "document_name"), [
    ("Khushi Sharma", "Khusi Sharma"),
    ("Shivani Rao", "Sivani Rao"),
    ("Mohammed Ibrahim", "Muhammad Ibrahim"),
    ("Vijay Kumar", "Vijaya Kumar"),
    ("Sharma Rajesh", "Rajesh Sharma"),
])
def test_name_check_indian_spelling_and_order_hard_negatives(id_name, document_name):
    packet = make_base_packet(id_name)
    for slip in packet.salary_slips:
        slip.applicant_name.value = document_name
    packet.bank_statement.account_holder.value = document_name

    flags = check_name_consistency(packet)
    assert flags == [], f"{id_name} vs {document_name} must not be flagged: {flags}"

def test_name_check_tiered_medium_similarity_is_warning():
    packet = make_base_packet("Rajesh Sharma")
    for slip in packet.salary_slips:
        slip.applicant_name.value = "Rajesh Verma"
    packet.bank_statement.account_holder.value = "Rajesh Verma"

    flags = check_name_consistency(packet)
    assert flags
    assert all(flag.severity == SeverityLevel.MEDIUM for flag in flags)

def test_name_check_low_similarity_is_high():
    packet = make_base_packet("Rajesh Sharma")
    packet.salary_slips[0].applicant_name.value = "Suresh Verma"

    flags = check_name_consistency(packet)
    assert flags[0].severity == SeverityLevel.HIGH
    assert "Suresh Verma" in flags[0].llm_explanation

def test_name_check_phonetic_signal():
    assert phonetic_similarity("Khushi", "Khusi") >= 85.0

def test_name_check_corroborated_identity_lowers_severity():
    packet = make_base_packet("Rajesh Sharma")
    packet.salary_slips[0].applicant_name.value = "Suresh Verma"
    packet.salary_slips[0].id_number = create_field("ABCDE1234F", "SALARY_SLIP_1.pdf", 1, 2)
    packet.bank_statement.id_number = create_field("ABCDE1234F", "BANK_STATEMENT.pdf", 1, 3)

    flags = check_name_consistency(packet)
    assert flags[0].severity == SeverityLevel.MEDIUM

def test_name_check_genuine_mismatch():
    packet = make_base_packet("Rajesh Sharma")
    packet.salary_slips[0].applicant_name.value = "Suresh Verma"
    flags = check_name_consistency(packet)
    assert len(flags) >= 1
    assert "Suresh Verma" in flags[0].llm_explanation

# --- 2. DOB CHECK ---
def test_dob_check_clean():
    packet = make_base_packet(dob="15/08/1990")
    flags = check_dob_consistency(packet)
    assert len(flags) == 0

def test_dob_check_mismatch():
    packet = make_base_packet(dob="15/08/1990")
    packet.salary_slips[0].date_of_birth.value = "12/03/1985"
    flags = check_dob_consistency(packet)
    assert len(flags) == 1
    assert flags[0].severity == SeverityLevel.HIGH
    assert "12/03/1985" in flags[0].llm_explanation

# --- 3. SALARY VS CREDIT & HARD NEGATIVE (LATE CREDIT) ---
def test_salary_credit_clean():
    packet = make_base_packet(net_pay=75000.0)
    flags = check_salary_vs_bank_credits(packet)
    assert len(flags) == 0

def test_salary_credit_hard_negative_late_salary():
    # Salary for Jan 2024 credited on 10-Feb-2024 (10 days late)
    packet = make_base_packet(net_pay=75000.0)
    packet.bank_statement.transactions[0].date = "2024-02-10"
    flags = check_salary_vs_bank_credits(packet)
    assert len(flags) == 0, f"Late salary credit must NOT be flagged: {flags}"

def test_salary_credit_gap_mismatch():
    # Payslip net pay is 75000, bank credit is 52000
    packet = make_base_packet(net_pay=75000.0)
    packet.bank_statement.transactions[0].credit_amount = 52000.0
    flags = check_salary_vs_bank_credits(packet)
    assert len(flags) == 1
    assert flags[0].severity == SeverityLevel.HIGH
    assert "₹52,000.00" in flags[0].llm_explanation

# --- 4. MISSING MONTH CREDIT ---
def test_missing_credit_clean():
    packet = make_base_packet()
    flags = check_missing_month_credits(packet)
    assert len(flags) == 0

def test_missing_credit_mismatch():
    packet = make_base_packet()
    # Remove credit for month 2 (Feb 2024)
    packet.bank_statement.transactions.pop(1)
    flags = check_missing_month_credits(packet)
    assert len(flags) == 1
    assert "February 2024" in flags[0].short_title

# --- 5. EMPLOYER CHECK & HARD NEGATIVE (GENUINE JOB CHANGE) ---
def test_employer_check_clean():
    packet = make_base_packet(employer="Infosys Limited")
    flags = check_employer_consistency(packet)
    assert len(flags) == 0

def test_employer_hard_negative_job_change():
    # Applicant worked at TCS in Jan/Feb, moved to Wipro in March
    packet = make_base_packet(employer="Tata Consultancy Services")
    packet.bank_statement.transactions[0].description = "ACH CR TCS SALARY JAN"
    packet.bank_statement.transactions[1].description = "ACH CR TCS SALARY FEB"

    # Slip 3 and Tx 3 are for Wipro
    packet.salary_slips[2].employer_name.value = "Wipro Technologies"
    packet.bank_statement.transactions[2].description = "ACH CR WIPRO PAYROLL MAR"

    flags = check_employer_consistency(packet)
    assert len(flags) == 0, f"Genuine job change must NOT be flagged: {flags}"

def test_employer_mismatch():
    packet = make_base_packet(employer="Infosys Limited")
    # Bank credit narration says completely different employer
    packet.bank_statement.transactions[0].description = "ACH CR ADANI PORTS SALARY"
    flags = check_employer_consistency(packet)
    assert len(flags) == 1
    assert flags[0].severity == SeverityLevel.HIGH
    assert "ADANI PORTS" in flags[0].llm_explanation

# --- 6. SLIP ARITHMETIC & DUPLICATE ---
def test_slip_arithmetic_clean():
    packet = make_base_packet(gross_pay=100000.0, deductions=20000.0, net_pay=80000.0)
    flags = check_slip_arithmetic_and_authenticity(packet)
    assert len(flags) == 0

def test_slip_arithmetic_tampered():
    # Gross 100k, Deductions 20k, but stated Net is 95k (should be 80k)
    packet = make_base_packet(gross_pay=100000.0, deductions=20000.0, net_pay=95000.0)
    flags = check_slip_arithmetic_and_authenticity(packet)
    assert len(flags) == 3  # All 3 slips have bad math
    assert "Arithmetic mismatch" in flags[0].llm_explanation

def test_duplicate_slip_id():
    packet = make_base_packet()
    # Slips 1 and 2 share the exact same slip ID
    packet.salary_slips[1].slip_id.value = packet.salary_slips[0].slip_id.value
    flags = check_slip_arithmetic_and_authenticity(packet)
    assert any("Duplicate salary slip ID" in f.llm_explanation for f in flags)
