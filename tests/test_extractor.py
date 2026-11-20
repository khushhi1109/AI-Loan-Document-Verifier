"""
Unit tests for PDF structured extraction with line citations.
"""

import os
import pytest
from src.generator.id_generator import generate_id_pdf
from src.generator.salary_slip_generator import generate_salary_slip_pdf
from src.generator.bank_statement_generator import generate_bank_statement_pdf
from src.extractor.pdf_extractor import (
    extract_id_document,
    extract_salary_slip,
    extract_bank_statement,
    extract_packet
)

@pytest.fixture
def sample_packet_dir(tmp_path):
    pdir = tmp_path / "APP_SAMPLE_01"
    pdir.mkdir()

    # Generate ID PDF
    generate_id_pdf(
        file_path=str(pdir / "id_document.pdf"),
        applicant_name="Sunil K. Verma",
        dob_str="12/05/1988",
        id_type="PAN",
        id_number="ABCDE9999Z"
    )

    # Generate Salary Slip
    generate_salary_slip_pdf(
        file_path=str(pdir / "salary_slip_1.pdf"),
        employer_name="Infosys Technologies Ltd",
        applicant_name="Sunil K. Verma",
        slip_id="INFY_8888",
        pay_period="2023-10",
        pay_month_name="October 2023",
        dob_str="12/05/1988",
        gross_pay=100000.0,
        deductions=20000.0,
        net_pay=80000.0
    )

    # Generate Bank Statement
    txs = [{
        "date": "2023-10-31",
        "description": "ACH CR INFOSYS TECH SALARY",
        "debit": 0.0,
        "credit": 80000.0,
        "balance": 180000.0,
        "is_salary": True
    }]
    generate_bank_statement_pdf(
        file_path=str(pdir / "bank_statement.pdf"),
        bank_name="HDFC Bank",
        account_holder="Sunil K. Verma",
        account_number="50100998877",
        transactions=txs,
        dob_str="12/05/1988"
    )

    return str(pdir)

def test_extract_id_document(sample_packet_dir):
    id_pdf = os.path.join(sample_packet_dir, "id_document.pdf")
    data = extract_id_document(id_pdf)
    assert data.applicant_name.value == "Sunil K. Verma"
    assert data.date_of_birth.value == "12/05/1988"
    assert data.id_number.value == "ABCDE9999Z"
    assert data.applicant_name.location.line > 0
    assert data.applicant_name.location.document == "id_document.pdf"

def test_extract_salary_slip(sample_packet_dir):
    slip_pdf = os.path.join(sample_packet_dir, "salary_slip_1.pdf")
    slip = extract_salary_slip(slip_pdf)
    assert slip.applicant_name.value == "Sunil K. Verma"
    assert slip.gross_pay.value == 100000.0
    assert slip.deductions.value == 20000.0
    assert slip.net_pay.value == 80000.0
    assert slip.pay_period.value == "2023-10"
    assert slip.net_pay.location.line > 0

def test_extract_bank_statement(sample_packet_dir):
    bank_pdf = os.path.join(sample_packet_dir, "bank_statement.pdf")
    bdata = extract_bank_statement(bank_pdf)
    assert bdata.account_holder.value == "Sunil K. Verma"
    assert len(bdata.transactions) >= 1
    assert bdata.transactions[0].credit_amount == 80000.0
    assert bdata.transactions[0].is_salary is True
    assert bdata.transactions[0].location.line > 0

def test_extract_packet_end_to_end(sample_packet_dir):
    packet = extract_packet(sample_packet_dir)
    assert packet.applicant_id == "APP_SAMPLE_01"
    assert packet.id_document.applicant_name.value == "Sunil K. Verma"
    assert len(packet.salary_slips) == 1
    assert len(packet.bank_statement.transactions) == 1
