"""
Structured PDF extraction engine using pdfplumber.
Extracts document fields with exact source locations (document, page, line number, raw text).
Strictly sets unreadable or missing fields to 'not_found' without hallucination.
"""

import os
import re
from typing import List, Tuple
import pdfplumber

from src.models import (
    SourceLocation,
    ExtractedField,
    IDDocumentData,
    SalarySlipData,
    BankTransaction,
    BankStatementData,
    ApplicantPacketData
)

def clean_amount(val_str: str) -> float:
    """Extracts float amount from currency formatted string."""
    cleaned = re.sub(r"[^\d.]", "", val_str)
    return float(cleaned) if cleaned else 0.0

def get_pdf_lines(pdf_path: str) -> List[Tuple[int, int, str]]:
    """
    Reads a PDF using pdfplumber and returns a list of (page_number, line_number, raw_text).
    Page and line numbers are 1-indexed.
    """
    lines_output = []
    with pdfplumber.open(pdf_path) as pdf:
        for p_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=False) or ""
            page_lines = [l.strip() for l in text.split("\n") if l.strip()]
            for l_idx, line in enumerate(page_lines, start=1):
                lines_output.append((p_idx, l_idx, line))
    return lines_output

def extract_id_document(pdf_path: str) -> IDDocumentData:
    """Extracts structured fields from an ID proof PDF with line citations."""
    doc_name = os.path.basename(pdf_path)
    if not os.path.exists(pdf_path):
        return IDDocumentData(
            document_name=doc_name,
            id_type="PAN",
            id_number=ExtractedField(field_name="id_number", value="not_found", location=None),
            applicant_name=ExtractedField(field_name="applicant_name", value="not_found", location=None),
            date_of_birth=ExtractedField(field_name="date_of_birth", value="not_found", location=None)
        )

    lines = get_pdf_lines(pdf_path)

    id_type = "PAN"
    id_number_val = "not_found"
    id_number_loc = None

    applicant_name_val = "not_found"
    applicant_name_loc = None

    dob_val = "not_found"
    dob_loc = None

    for page_num, line_num, line in lines:
        upper_l = line.upper()

        if "AADHAAR" in upper_l or "UIDAI" in upper_l:
            id_type = "AADHAAR"

        # ID Number (PAN or Aadhaar/UID)
        pan_match = re.search(r"(?:PERMANENT ACCOUNT NUMBER|AADHAAR NUMBER|UID):\s*([A-Z0-9\s]+)", line, re.IGNORECASE)
        if pan_match:
            id_number_val = pan_match.group(1).strip()
            id_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Name
        name_match = re.search(r"APPLICANT NAME:\s*([A-Za-z.\s]+)", line, re.IGNORECASE)
        if name_match:
            val = name_match.group(1).strip()
            if val.lower() != "not_found" and val:
                applicant_name_val = val
                applicant_name_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # DOB
        dob_match = re.search(r"DATE OF BIRTH:\s*([\d\-/A-Za-z]+)", line, re.IGNORECASE)
        if dob_match:
            val = dob_match.group(1).strip()
            if val.lower() != "not_found" and val:
                dob_val = val
                dob_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

    return IDDocumentData(
        document_name=doc_name,
        id_type=id_type,
        id_number=ExtractedField(field_name="id_number", value=id_number_val, location=id_number_loc),
        applicant_name=ExtractedField(field_name="applicant_name", value=applicant_name_val, location=applicant_name_loc),
        date_of_birth=ExtractedField(field_name="date_of_birth", value=dob_val, location=dob_loc)
    )

def extract_salary_slip(pdf_path: str) -> SalarySlipData:
    """Extracts structured earnings, deductions, and metadata from a salary slip PDF."""
    doc_name = os.path.basename(pdf_path)
    if not os.path.exists(pdf_path):
        return SalarySlipData(
            document_name=doc_name,
            slip_id=ExtractedField(field_name="slip_id", value="not_found", location=None),
            applicant_name=ExtractedField(field_name="applicant_name", value="not_found", location=None),
            applicant_id_number=ExtractedField(field_name="applicant_id_number", value="not_found", location=None),
            employer_name=ExtractedField(field_name="employer_name", value="not_found", location=None),
            date_of_birth=None,
            pay_period=ExtractedField(field_name="pay_period", value="not_found", location=None),
            pay_month_name=ExtractedField(field_name="pay_month_name", value="not_found", location=None),
            gross_pay=ExtractedField(field_name="gross_pay", value="not_found", location=None),
            deductions=ExtractedField(field_name="deductions", value="not_found", location=None),
            net_pay=ExtractedField(field_name="net_pay", value="not_found", location=None)
        )

    lines = get_pdf_lines(pdf_path)

    employer_name_val = "not_found"
    employer_loc = None

    slip_id_val = "not_found"
    slip_id_loc = None

    applicant_name_val = "not_found"
    applicant_name_loc = None

    applicant_id_number_val = "not_found"
    applicant_id_number_loc = None

    dob_val = "not_found"
    dob_loc = None

    pay_period_val = "not_found"
    pay_period_loc = None

    pay_month_name_val = "not_found"
    pay_month_loc = None

    gross_pay_val = "not_found"
    gross_loc = None

    deductions_val = "not_found"
    ded_loc = None

    net_pay_val = "not_found"
    net_loc = None
    id_number_val = "not_found"
    id_number_loc = None

    # First line is typically the employer header
    if lines:
        p_n, l_n, first_line = lines[0]
        employer_name_val = first_line.strip()
        employer_loc = SourceLocation(document=doc_name, page=p_n, line=l_n, raw_text=first_line)

    for page_num, line_num, line in lines:
        # Pay month name & period
        month_match = re.search(r"PAYSLIP FOR THE MONTH OF:\s*([A-Za-z0-9\s]+?)\s*\(Period:\s*([\d\-]+)\)", line, re.IGNORECASE)
        if month_match:
            pay_month_name_val = month_match.group(1).strip()
            pay_period_val = month_match.group(2).strip()
            pay_period_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)
            pay_month_loc = pay_period_loc

        # Employee ID
        id_match = re.search(r"EMPLOYEE ID:\s*([A-Za-z0-9_]+)", line, re.IGNORECASE)
        if id_match:
            slip_id_val = id_match.group(1).strip()
            slip_id_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Optional applicant ID number, when present in a payslip
        applicant_id_match = re.search(r"(?:ID NUMBER|PAN NUMBER|AADHAAR NUMBER):\s*([A-Z0-9\s]+)", line, re.IGNORECASE)
        if applicant_id_match:
            id_number_val = applicant_id_match.group(1).strip()
            id_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Employee Name
        name_match = re.search(r"EMPLOYEE NAME:\s*([A-Za-z.\s]+?)(?=\s+(?:Designation|Department|Dept|Designation:|$):?|$)", line, re.IGNORECASE)
        if name_match:
            applicant_name_val = name_match.group(1).strip()
            applicant_name_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        applicant_id_match = re.search(r"APPLICANT ID NUMBER:\s*([A-Z0-9\s-]+)", line, re.IGNORECASE)
        if applicant_id_match:
            applicant_id_number_val = applicant_id_match.group(1).strip()
            applicant_id_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # DOB
        dob_match = re.search(r"DATE OF BIRTH:\s*([\d\-/A-Za-z]+)", line, re.IGNORECASE)
        if dob_match:
            dob_val = dob_match.group(1).strip()
            dob_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Gross Pay
        gross_match = re.search(r"GROSS PAY:\s*(?:Rs\.|INR)?\s*([\d,.]+)", line, re.IGNORECASE)
        if gross_match:
            gross_pay_val = clean_amount(gross_match.group(1))
            gross_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Total Deductions
        ded_match = re.search(r"TOTAL DEDUCTIONS:\s*(?:Rs\.|INR)?\s*([\d,.]+)", line, re.IGNORECASE)
        if ded_match:
            deductions_val = clean_amount(ded_match.group(1))
            ded_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Net Salary Payable
        net_match = re.search(r"NET SALARY PAYABLE:\s*(?:Rs\.|INR)?\s*([\d,.]+)", line, re.IGNORECASE)
        if net_match:
            net_pay_val = clean_amount(net_match.group(1))
            net_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

    return SalarySlipData(
        document_name=doc_name,
        slip_id=ExtractedField(field_name="slip_id", value=slip_id_val, location=slip_id_loc),
        applicant_name=ExtractedField(field_name="applicant_name", value=applicant_name_val, location=applicant_name_loc),
        applicant_id_number=ExtractedField(
            field_name="applicant_id_number",
            value=applicant_id_number_val,
            location=applicant_id_number_loc
        ),
        employer_name=ExtractedField(field_name="employer_name", value=employer_name_val, location=employer_loc),
        date_of_birth=ExtractedField(field_name="date_of_birth", value=dob_val, location=dob_loc) if dob_val != "not_found" else None,
        pay_period=ExtractedField(field_name="pay_period", value=pay_period_val, location=pay_period_loc),
        pay_month_name=ExtractedField(field_name="pay_month_name", value=pay_month_name_val, location=pay_month_loc),
        gross_pay=ExtractedField(field_name="gross_pay", value=gross_pay_val, location=gross_loc),
        deductions=ExtractedField(field_name="deductions", value=deductions_val, location=ded_loc),
        net_pay=ExtractedField(field_name="net_pay", value=net_pay_val, location=net_loc),
        id_number=ExtractedField(field_name="id_number", value=id_number_val, location=id_number_loc) if id_number_val != "not_found" else None
    )

def extract_bank_statement(pdf_path: str) -> BankStatementData:
    """Extracts account profile and transactions from a bank statement PDF."""
    doc_name = os.path.basename(pdf_path)
    if not os.path.exists(pdf_path):
        return BankStatementData(
            document_name=doc_name,
            bank_name=ExtractedField(field_name="bank_name", value="not_found", location=None),
            account_holder=ExtractedField(field_name="account_holder", value="not_found", location=None),
            account_number=ExtractedField(field_name="account_number", value="not_found", location=None),
            applicant_id_number=ExtractedField(field_name="applicant_id_number", value="not_found", location=None),
            date_of_birth=None,
            transactions=[]
        )

    lines = get_pdf_lines(pdf_path)

    bank_name_val = "not_found"
    bank_name_loc = None

    account_holder_val = "not_found"
    account_holder_loc = None

    applicant_id_number_val = "not_found"
    applicant_id_number_loc = None

    account_number_val = "not_found"
    account_number_loc = None

    dob_val = "not_found"
    dob_loc = None
    id_number_val = "not_found"
    id_number_loc = None

    transactions: List[BankTransaction] = []

    # First line is usually Bank Name
    if lines:
        p_n, l_n, first_line = lines[0]
        bank_name_val = first_line.strip()
        bank_name_loc = SourceLocation(document=doc_name, page=p_n, line=l_n, raw_text=first_line)

    # Date pattern: YYYY-MM-DD or DD-MM-YYYY or DD-Mon-YYYY
    date_regex = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}|\d{2}-[A-Za-z]{3}-\d{4})\s+(.+)$")

    for page_num, line_num, line in lines:
        # Account Holder
        holder_match = re.search(r"ACCOUNT HOLDER NAME:\s*([A-Za-z.\s]+?)(?=\s+Account Number|\s+Acc No|$)", line, re.IGNORECASE)
        if holder_match:
            account_holder_val = holder_match.group(1).strip()
            account_holder_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Account Number
        acc_match = re.search(r"ACCOUNT NUMBER:\s*([A-Za-z0-9]+)", line, re.IGNORECASE)
        if acc_match:
            account_number_val = acc_match.group(1).strip()
            account_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        applicant_id_match = re.search(r"APPLICANT ID NUMBER:\s*([A-Z0-9\s-]+)", line, re.IGNORECASE)
        if applicant_id_match:
            applicant_id_number_val = applicant_id_match.group(1).strip()
            applicant_id_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Optional applicant ID number, when present in a statement profile
        applicant_id_match = re.search(r"(?:ID NUMBER|PAN NUMBER|AADHAAR NUMBER):\s*([A-Z0-9\s]+)", line, re.IGNORECASE)
        if applicant_id_match:
            id_number_val = applicant_id_match.group(1).strip()
            id_number_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Date of Birth
        dob_match = re.search(r"DATE OF BIRTH:\s*([\d\-/A-Za-z]+)", line, re.IGNORECASE)
        if dob_match:
            dob_val = dob_match.group(1).strip()
            dob_loc = SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)

        # Tabular Transaction Row: e.g. "2023-10-31 ACH CR INFOSYS TECH SALARY - 80,000.00 180,000.00"
        m = date_regex.match(line)
        if m:
            tx_date = m.group(1)
            remainder = m.group(2).strip()

            tokens = remainder.split()
            # The last token is balance
            # The second to last token is either credit/debit or '-'
            if len(tokens) >= 3:
                bal_amt = clean_amount(tokens[-1])
                
                # Check for deposit or withdrawal
                is_credit = bool(re.search(r"\b(?:ACH\s+CR|NEFT\s+CR|CR|CREDIT|SALARY|PAYROLL|DEPOSIT)\b", remainder, re.IGNORECASE))
                
                # Find all amount tokens in the tail
                num_tokens = [t for t in tokens[-3:] if re.search(r"\d", t)]
                if len(num_tokens) >= 2:
                    tx_amt = clean_amount(num_tokens[-2])
                elif len(num_tokens) == 1:
                    tx_amt = clean_amount(num_tokens[0])
                else:
                    tx_amt = 0.0

                credit_val = tx_amt if is_credit else 0.0
                debit_val = tx_amt if not is_credit else 0.0

                # Description is everything preceding the last 2 or 3 tokens
                desc = " ".join([t for t in tokens if t not in ["-"] and not re.match(r"^[\d,.]+$", t)])
                is_salary_tx = ("SALARY" in desc.upper()) or ("PAYROLL" in desc.upper()) or ("ACH CR" in desc.upper())

                transactions.append(BankTransaction(
                    date=tx_date,
                    description=desc,
                    credit_amount=credit_val,
                    debit_amount=debit_val,
                    balance=bal_amt,
                    is_salary=is_salary_tx,
                    location=SourceLocation(document=doc_name, page=page_num, line=line_num, raw_text=line)
                ))

    return BankStatementData(
        document_name=doc_name,
        bank_name=ExtractedField(field_name="bank_name", value=bank_name_val, location=bank_name_loc),
        account_holder=ExtractedField(field_name="account_holder", value=account_holder_val, location=account_holder_loc),
        account_number=ExtractedField(field_name="account_number", value=account_number_val, location=account_number_loc),
        applicant_id_number=ExtractedField(
            field_name="applicant_id_number",
            value=applicant_id_number_val,
            location=applicant_id_number_loc
        ),
        date_of_birth=ExtractedField(field_name="date_of_birth", value=dob_val, location=dob_loc) if dob_val != "not_found" else None,
        id_number=ExtractedField(field_name="id_number", value=id_number_val, location=id_number_loc) if id_number_val != "not_found" else None,
        transactions=transactions
    )

def extract_packet(packet_dir: str) -> ApplicantPacketData:
    """Extracts all documents for a single applicant packet folder."""
    app_id = os.path.basename(os.path.normpath(packet_dir))

    id_path = os.path.join(packet_dir, "id_document.pdf")
    id_doc = extract_id_document(id_path)

    slips: List[SalarySlipData] = []
    # Collect salary_slip_1.pdf, salary_slip_2.pdf, salary_slip_3.pdf in order
    slip_files = sorted([f for f in os.listdir(packet_dir) if f.startswith("salary_slip") and f.endswith(".pdf")])
    for sf in slip_files:
        slips.append(extract_salary_slip(os.path.join(packet_dir, sf)))

    bank_path = os.path.join(packet_dir, "bank_statement.pdf")
    bank_data = extract_bank_statement(bank_path)

    return ApplicantPacketData(
        applicant_id=app_id,
        id_document=id_doc,
        salary_slips=slips,
        bank_statement=bank_data
    )
