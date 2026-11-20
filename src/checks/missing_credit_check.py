"""
Missing salary credit check.
Verifies that every presented salary slip month has a corresponding credit transaction
in the bank statement. Flags if any month has zero matching credit.
"""

from typing import List
from src.models import (
    ApplicantPacketData,
    MismatchFlag,
    EvidenceItem,
    SeverityLevel
)
from src.checks.salary_vs_credit_check import find_salary_credit_for_slip, get_month_window

def check_missing_month_credits(packet: ApplicantPacketData) -> List[MismatchFlag]:
    """
    Deterministic check: flags any salary slip period that completely lacks a
    matching salary credit entry in the applicant's bank statement.
    """
    flags: List[MismatchFlag] = []

    for idx, slip in enumerate(packet.salary_slips, start=1):
        if not slip.pay_period.is_found:
            continue

        matching_tx = find_salary_credit_for_slip(slip, packet.bank_statement.transactions)
        if matching_tx is None:
            # Missing credit detected for this month!
            slip_loc = slip.pay_period.location or slip.net_pay.location
            period_name = str(slip.pay_month_name.value) if slip.pay_month_name.is_found else str(slip.pay_period.value)
            net_val = f"₹{float(slip.net_pay.value):,.2f}" if slip.net_pay.is_found else "N/A"
            w_start, w_end = get_month_window(str(slip.pay_period.value))

            flags.append(MismatchFlag(
                flag_id=f"FLAG_MISSING_CREDIT_SLIP_{idx}",
                check_name="missing_month_credit",
                severity=SeverityLevel.HIGH,
                short_title=f"Missing Salary Credit in Bank Statement ({period_name})",
                llm_explanation=(
                    f"Salary slip #{idx} presents earnings of {net_val} for pay period '{period_name}' "
                    f"({slip.document_name}, line {slip_loc.line if slip_loc else 'N/A'}), "
                    f"but no corresponding salary credit transaction was found in bank statement "
                    f"'{packet.bank_statement.document_name}' between {w_start.strftime('%Y-%m-%d')} "
                    f"and {w_end.strftime('%Y-%m-%d')}."
                ),
                evidence=[
                    EvidenceItem(
                        document=slip.document_name,
                        page=slip_loc.page if slip_loc else 1,
                        line=slip_loc.line if slip_loc else 1,
                        field_name="pay_period",
                        extracted_value=f"{period_name} (Net: {net_val})",
                        raw_snippet=slip_loc.raw_text if slip_loc else ""
                    ),
                    EvidenceItem(
                        document=packet.bank_statement.document_name,
                        page=1,
                        line=1,
                        field_name="transactions",
                        extracted_value=f"No matching credit between {w_start.strftime('%d-%b-%Y')} and {w_end.strftime('%d-%b-%Y')}",
                        raw_snippet=f"Statement period checked for {period_name}"
                    )
                ]
            ))

    return flags
