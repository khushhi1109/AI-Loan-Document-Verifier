"""
Employer consistency check between salary slips and bank statement narrations.
Detects fraudulent/mismatched employers while accurately respecting genuine job transitions
(hard negative: applicant changes jobs between pay months and bank credits match chronologically).
"""

import re
from typing import List, Set
from rapidfuzz import fuzz
from src.config import CONFIG
from src.models import (
    ApplicantPacketData,
    MismatchFlag,
    EvidenceItem,
    SeverityLevel
)
from src.checks.salary_vs_credit_check import find_salary_credit_for_slip

STOP_WORDS = {"PVT", "LTD", "LIMITED", "PRIVATE", "INC", "LLP", "CORP", "CORPORATION", "SERVICES", "INDIA", "SAL", "SALARY", "PAYROLL", "NEFT", "RTGS", "CMS", "ACH", "INB"}

KNOWN_ACRONYMS = {
    "TCS": "TATA CONSULTANCY SERVICES",
    "INFY": "INFOSYS",
    "CTS": "COGNIZANT",
    "WIPRO": "WIPRO",
    "HCL": "HCL TECHNOLOGIES",
    "SBI": "STATE BANK OF INDIA",
    "HDFC": "HDFC BANK",
    "ICICI": "ICICI BANK",
    "L&T": "LARSEN & TOUBRO",
    "LT": "LARSEN & TOUBRO"
}

def extract_meaningful_tokens(name: str) -> Set[str]:
    """Cleans and extracts core distinctive tokens from an employer or narration string."""
    norm = re.sub(r"L\s*&\s*T", "LARSEN", name.upper())
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", norm)
    tokens = {t for t in cleaned.split() if len(t) >= 2 and t not in STOP_WORDS}
    return tokens

def is_acronym_match(short_token: str, full_name: str) -> bool:
    """Checks if a short token like 'TCS' or 'L&T' is an acronym for the full company name."""
    st = short_token.upper().strip()
    if st in KNOWN_ACRONYMS:
        known_target = KNOWN_ACRONYMS[st]
        if known_target in full_name.upper() or full_name.upper() in known_target:
            return True

    # Check first letter of all non-empty words (excluding only legal suffixes like Ltd, Pvt)
    legal_suffixes = {"LTD", "LIMITED", "PVT", "PRIVATE", "INC", "LLP"}
    words = [w for w in re.sub(r"[^a-zA-Z\s]", " ", full_name).upper().split() if w and w not in legal_suffixes]
    if len(words) >= len(st) and len(st) >= 2:
        acronym = "".join(w[0] for w in words[:len(st)])
        if st == acronym:
            return True
        all_acronym = "".join(w[0] for w in words)
        if st in all_acronym or all_acronym in st:
            return True
    return False

def check_employer_match(slip_employer: str, narration: str, threshold: float) -> bool:
    """
    Checks if a salary slip employer aligns with the bank credit transaction narration.
    """
    if not slip_employer or not narration:
        return False

    slip_emp_upper = re.sub(r"L\s*&\s*T", "LARSEN & TOUBRO", slip_employer.upper())
    narration_upper = re.sub(r"L\s*&\s*T", "LARSEN & TOUBRO", narration.upper())

    # Exact or substring match
    if slip_emp_upper in narration_upper or narration_upper in slip_emp_upper:
        return True

    # Token overlap check
    emp_tokens = extract_meaningful_tokens(slip_employer)
    narration_tokens = extract_meaningful_tokens(narration)

    # Check for direct token intersection
    if emp_tokens.intersection(narration_tokens):
        return True

    # Check acronyms (e.g., TCS vs Tata Consultancy Services)
    for nt in narration_tokens:
        if is_acronym_match(nt, slip_employer):
            return True
    for et in emp_tokens:
        if is_acronym_match(et, narration):
            return True

    # Rapidfuzz Token Set Ratio
    score = fuzz.token_set_ratio(slip_emp_upper, narration_upper)
    return score >= threshold

def check_employer_consistency(packet: ApplicantPacketData) -> List[MismatchFlag]:
    """
    Deterministic check: verifies salary slip employer against bank statement salary credits.
    Supports genuine chronological job transitions (hard negative).
    """
    flags: List[MismatchFlag] = []

    for idx, slip in enumerate(packet.salary_slips, start=1):
        if not slip.employer_name.is_found:
            continue

        slip_emp = str(slip.employer_name.value)
        matching_tx = find_salary_credit_for_slip(slip, packet.bank_statement.transactions)
        
        if not matching_tx:
            # If credit is missing, missing_credit_check already handles it
            continue

        narration = matching_tx.description
        is_match = check_employer_match(
            slip_emp, narration, CONFIG.EMPLOYER_SIMILARITY_THRESHOLD
        )

        if not is_match:
            slip_loc = slip.employer_name.location
            tx_loc = matching_tx.location

            flags.append(MismatchFlag(
                flag_id=f"FLAG_EMPLOYER_MISMATCH_SLIP_{idx}",
                check_name="employer_consistency",
                severity=SeverityLevel.HIGH,
                short_title=f"Employer Mismatch: Slip #{idx} vs Bank Narration",
                llm_explanation=(
                    f"Salary slip #{idx} lists employer as '{slip_emp}' "
                    f"({slip.document_name}, line {slip_loc.line if slip_loc else 'N/A'}), "
                    f"but bank statement salary credit narration on {matching_tx.date} reflects "
                    f"'{narration}' ({packet.bank_statement.document_name}, line {tx_loc.line if tx_loc else 'N/A'}). "
                    f"No matching employer affiliation could be confirmed for this pay cycle."
                ),
                evidence=[
                    EvidenceItem(
                        document=slip.document_name,
                        page=slip_loc.page if slip_loc else 1,
                        line=slip_loc.line if slip_loc else 1,
                        field_name="employer_name",
                        extracted_value=slip_emp,
                        raw_snippet=slip_loc.raw_text if slip_loc else ""
                    ),
                    EvidenceItem(
                        document=packet.bank_statement.document_name,
                        page=tx_loc.page if tx_loc else 1,
                        line=tx_loc.line if tx_loc else 1,
                        field_name="description",
                        extracted_value=narration,
                        raw_snippet=tx_loc.raw_text if tx_loc else ""
                    )
                ]
            ))

    return flags
