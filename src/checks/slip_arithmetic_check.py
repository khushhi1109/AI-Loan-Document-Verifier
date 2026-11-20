"""
Salary slip internal arithmetic integrity and duplicate/tampering detection.
Verifies that Gross Pay - Deductions == Net Pay within tolerance, and flags
re-used slip IDs or duplicate pay periods.
"""

from typing import List, Dict
from src.config import CONFIG
from src.models import (
    ApplicantPacketData,
    MismatchFlag,
    EvidenceItem,
    SeverityLevel
)

def check_slip_arithmetic_and_authenticity(packet: ApplicantPacketData) -> List[MismatchFlag]:
    """
    Deterministic check:
    1. Validates that Gross Pay - Deductions == Net Pay for each salary slip.
    2. Detects duplicate slip IDs or re-used pay periods across submitted slips.
    """
    flags: List[MismatchFlag] = []
    seen_slip_ids: Dict[str, str] = {}
    seen_periods: Dict[str, str] = {}

    for idx, slip in enumerate(packet.salary_slips, start=1):
        # 1. Arithmetic check
        if (slip.gross_pay.is_found and
            slip.deductions.is_found and
            slip.net_pay.is_found):
            try:
                gross = float(slip.gross_pay.value)
                deductions = float(slip.deductions.value)
                stated_net = float(slip.net_pay.value)
                expected_net = gross - deductions
                diff = abs(expected_net - stated_net)

                if diff > CONFIG.ARITHMETIC_TOLERANCE_INR:
                    gross_loc = slip.gross_pay.location
                    ded_loc = slip.deductions.location
                    net_loc = slip.net_pay.location

                    flags.append(MismatchFlag(
                        flag_id=f"FLAG_SLIP_ARITHMETIC_MISMATCH_SLIP_{idx}",
                        check_name="slip_arithmetic_duplicate",
                        severity=SeverityLevel.HIGH,
                        short_title=f"Salary Slip Arithmetic Error: Slip #{idx}",
                        llm_explanation=(
                            f"Arithmetic mismatch on Salary Slip #{idx} ({slip.document_name}): "
                            f"Gross Pay of ₹{gross:,.2f} (line {gross_loc.line if gross_loc else 'N/A'}) "
                            f"minus Deductions of ₹{deductions:,.2f} (line {ded_loc.line if ded_loc else 'N/A'}) "
                            f"yields ₹{expected_net:,.2f}, which does not match the stated Net Pay of "
                            f"₹{stated_net:,.2f} (line {net_loc.line if net_loc else 'N/A'}). "
                            f"Discrepancy: ₹{diff:,.2f}."
                        ),
                        evidence=[
                            EvidenceItem(
                                document=slip.document_name,
                                page=gross_loc.page if gross_loc else 1,
                                line=gross_loc.line if gross_loc else 1,
                                field_name="gross_pay",
                                extracted_value=f"₹{gross:,.2f}",
                                raw_snippet=gross_loc.raw_text if gross_loc else ""
                            ),
                            EvidenceItem(
                                document=slip.document_name,
                                page=ded_loc.page if ded_loc else 1,
                                line=ded_loc.line if ded_loc else 1,
                                field_name="deductions",
                                extracted_value=f"₹{deductions:,.2f}",
                                raw_snippet=ded_loc.raw_text if ded_loc else ""
                            ),
                            EvidenceItem(
                                document=slip.document_name,
                                page=net_loc.page if net_loc else 1,
                                line=net_loc.line if net_loc else 1,
                                field_name="net_pay",
                                extracted_value=f"₹{stated_net:,.2f} (expected ₹{expected_net:,.2f})",
                                raw_snippet=net_loc.raw_text if net_loc else ""
                            )
                        ]
                    ))
            except (ValueError, TypeError):
                pass

        # 2. Duplicate Slip ID check
        if slip.slip_id.is_found:
            sid = str(slip.slip_id.value).strip()
            if sid in seen_slip_ids:
                prev_doc = seen_slip_ids[sid]
                sid_loc = slip.slip_id.location
                flags.append(MismatchFlag(
                    flag_id=f"FLAG_DUPLICATE_SLIP_ID_{idx}",
                    check_name="slip_arithmetic_duplicate",
                    severity=SeverityLevel.HIGH,
                    short_title=f"Duplicate Salary Slip ID: {sid}",
                    llm_explanation=(
                        f"Duplicate salary slip ID '{sid}' identified on '{slip.document_name}' "
                        f"(line {sid_loc.line if sid_loc else 'N/A'}), which was previously found on "
                        f"'{prev_doc}'. Re-use of slip identifiers indicates document duplication or editing."
                    ),
                    evidence=[
                        EvidenceItem(
                            document=prev_doc,
                            page=1,
                            line=1,
                            field_name="slip_id",
                            extracted_value=sid,
                            raw_snippet=f"Original occurrence in {prev_doc}"
                        ),
                        EvidenceItem(
                            document=slip.document_name,
                            page=sid_loc.page if sid_loc else 1,
                            line=sid_loc.line if sid_loc else 1,
                            field_name="slip_id",
                            extracted_value=sid,
                            raw_snippet=sid_loc.raw_text if sid_loc else ""
                        )
                    ]
                ))
            else:
                seen_slip_ids[sid] = slip.document_name

        # 3. Duplicate Pay Period check (e.g. submitted two slips for the same month)
        if slip.pay_period.is_found:
            period = str(slip.pay_period.value).strip()
            if period in seen_periods:
                prev_doc = seen_periods[period]
                p_loc = slip.pay_period.location
                flags.append(MismatchFlag(
                    flag_id=f"FLAG_DUPLICATE_PAY_PERIOD_{idx}",
                    check_name="slip_arithmetic_duplicate",
                    severity=SeverityLevel.HIGH,
                    short_title=f"Duplicate Pay Period Submitted: {period}",
                    llm_explanation=(
                        f"Salary slip '{slip.document_name}' claims pay period '{period}' "
                        f"(line {p_loc.line if p_loc else 'N/A'}), but pay period '{period}' "
                        f"was already submitted via '{prev_doc}'."
                    ),
                    evidence=[
                        EvidenceItem(
                            document=prev_doc,
                            page=1,
                            line=1,
                            field_name="pay_period",
                            extracted_value=period,
                            raw_snippet=f"Earlier submission in {prev_doc}"
                        ),
                        EvidenceItem(
                            document=slip.document_name,
                            page=p_loc.page if p_loc else 1,
                            line=p_loc.line if p_loc else 1,
                            field_name="pay_period",
                            extracted_value=period,
                            raw_snippet=p_loc.raw_text if p_loc else ""
                        )
                    ]
                ))
            else:
                seen_periods[period] = slip.document_name

    return flags
