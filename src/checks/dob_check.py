"""
Date of Birth (DOB) consistency check across loan applicant documents.
Parses various date formats (DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY) and flags genuine mismatches.
"""

from typing import List, Optional
from datetime import datetime
from dateutil import parser
from src.models import (
    ApplicantPacketData,
    MismatchFlag,
    EvidenceItem,
    SeverityLevel
)

def parse_dob(date_str: str) -> Optional[datetime]:
    if not date_str or date_str.strip().lower() == "not_found":
        return None
    try:
        # Standardize common Indian formats like 15/08/1990, 1990-08-15, 15-Aug-1990
        return parser.parse(date_str.strip(), dayfirst=True)
    except (ValueError, TypeError):
        return None

def check_dob_consistency(packet: ApplicantPacketData) -> List[MismatchFlag]:
    """
    Deterministic check comparing Date of Birth from ID proof against any other
    document stating DOB (e.g. salary slip or bank account record).
    """
    flags: List[MismatchFlag] = []
    id_dob_field = packet.id_document.date_of_birth

    if not id_dob_field.is_found:
        flags.append(MismatchFlag(
            flag_id="FLAG_DOB_ID_MISSING",
            check_name="dob_consistency",
            severity=SeverityLevel.HIGH,
            short_title="Date of Birth Missing on ID Proof",
            llm_explanation=(
                f"Date of birth could not be found or extracted from ID proof "
                f"'{packet.id_document.document_name}'."
            ),
            evidence=[EvidenceItem(
                document=packet.id_document.document_name,
                page=id_dob_field.location.page if id_dob_field.location else 1,
                line=id_dob_field.location.line if id_dob_field.location else 1,
                field_name="date_of_birth",
                extracted_value="not_found"
            )]
        ))
        return flags

    id_dob_raw = str(id_dob_field.value)
    id_dob = parse_dob(id_dob_raw)
    if not id_dob:
        return flags

    primary_loc = id_dob_field.location

    # 1. Check against salary slips if employee DOB is recorded
    for idx, slip in enumerate(packet.salary_slips, start=1):
        if slip.date_of_birth and slip.date_of_birth.is_found:
            slip_dob_raw = str(slip.date_of_birth.value)
            slip_dob = parse_dob(slip_dob_raw)
            if slip_dob and id_dob.date() != slip_dob.date():
                slip_loc = slip.date_of_birth.location
                flags.append(MismatchFlag(
                    flag_id=f"FLAG_DOB_MISMATCH_SLIP_{idx}",
                    check_name="dob_consistency",
                    severity=SeverityLevel.HIGH,
                    short_title=f"DOB Mismatch: ID Proof vs Salary Slip #{idx}",
                    llm_explanation=(
                        f"Date of birth mismatch: ID proof '{packet.id_document.document_name}' "
                        f"states '{id_dob_raw}' (line {primary_loc.line if primary_loc else 'N/A'}), "
                        f"whereas Salary Slip #{idx} '{slip.document_name}' "
                        f"states '{slip_dob_raw}' (line {slip_loc.line if slip_loc else 'N/A'})."
                    ),
                    evidence=[
                        EvidenceItem(
                            document=packet.id_document.document_name,
                            page=primary_loc.page if primary_loc else 1,
                            line=primary_loc.line if primary_loc else 1,
                            field_name="date_of_birth",
                            extracted_value=id_dob_raw,
                            raw_snippet=primary_loc.raw_text if primary_loc else ""
                        ),
                        EvidenceItem(
                            document=slip.document_name,
                            page=slip_loc.page if slip_loc else 1,
                            line=slip_loc.line if slip_loc else 1,
                            field_name="date_of_birth",
                            extracted_value=slip_dob_raw,
                            raw_snippet=slip_loc.raw_text if slip_loc else ""
                        )
                    ]
                ))

    # 2. Check against bank statement account holder DOB if present
    if packet.bank_statement.date_of_birth and packet.bank_statement.date_of_birth.is_found:
        bank_dob_raw = str(packet.bank_statement.date_of_birth.value)
        bank_dob = parse_dob(bank_dob_raw)
        if bank_dob and id_dob.date() != bank_dob.date():
            bank_loc = packet.bank_statement.date_of_birth.location
            flags.append(MismatchFlag(
                flag_id="FLAG_DOB_MISMATCH_BANK",
                check_name="dob_consistency",
                severity=SeverityLevel.HIGH,
                short_title="DOB Mismatch: ID Proof vs Bank Statement",
                llm_explanation=(
                    f"Date of birth mismatch: ID proof '{packet.id_document.document_name}' "
                    f"shows '{id_dob_raw}' (line {primary_loc.line if primary_loc else 'N/A'}), "
                    f"while Bank Statement profile '{packet.bank_statement.document_name}' "
                    f"shows '{bank_dob_raw}' (line {bank_loc.line if bank_loc else 'N/A'})."
                ),
                evidence=[
                    EvidenceItem(
                        document=packet.id_document.document_name,
                        page=primary_loc.page if primary_loc else 1,
                        line=primary_loc.line if primary_loc else 1,
                        field_name="date_of_birth",
                        extracted_value=id_dob_raw,
                        raw_snippet=primary_loc.raw_text if primary_loc else ""
                    ),
                    EvidenceItem(
                        document=packet.bank_statement.document_name,
                        page=bank_loc.page if bank_loc else 1,
                        line=bank_loc.line if bank_loc else 1,
                        field_name="date_of_birth",
                        extracted_value=bank_dob_raw,
                        raw_snippet=bank_loc.raw_text if bank_loc else ""
                    )
                ]
            ))

    return flags
