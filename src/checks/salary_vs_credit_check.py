"""
Salary vs Bank Credit discrepancy check.
Compares Net Pay from each salary slip against corresponding bank salary credits
within a flexible calendar window and tolerance threshold.
Properly treats late salary credit (e.g. credited 7-15 days late) as acceptable (hard negative).
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import calendar
from dateutil import parser
from src.config import CONFIG
from src.models import (
    ApplicantPacketData,
    SalarySlipData,
    BankTransaction,
    MismatchFlag,
    EvidenceItem,
    SeverityLevel
)

def get_month_window(pay_period_str: str) -> Tuple[datetime, datetime]:
    """
    Returns (window_start, window_end) for a pay period formatted like '2024-01' or 'January 2024'.
    Salaries for month M are paid near month-end (from the 20th onwards) or in the following month
    (up to SALARY_DATE_WINDOW_FUTURE_DAYS days after month end, handling late payments).
    """
    try:
        dt = parser.parse(pay_period_str.strip())
        year = dt.year
        month = dt.month
    except Exception:
        # Fallback to 2024-01
        year = 2024
        month = 1

    _, last_day = calendar.monthrange(year, month)
    # Salaries are disbursed towards the end of the pay month or following month
    window_start = datetime(year, month, 20)
    window_end = datetime(year, month, last_day) + timedelta(days=CONFIG.SALARY_DATE_WINDOW_FUTURE_DAYS)
    return window_start, window_end

def find_salary_credit_for_slip(
    slip: SalarySlipData,
    transactions: List[BankTransaction]
) -> Optional[BankTransaction]:
    """
    Finds the matching salary credit transaction for a salary slip within the permissible date window.
    """
    if not slip.pay_period.is_found:
        return None

    window_start, window_end = get_month_window(str(slip.pay_period.value))
    candidates: List[BankTransaction] = []

    for tx in transactions:
        try:
            tx_date = parser.parse(tx.date)
        except Exception:
            continue

        if window_start <= tx_date <= window_end and tx.credit_amount > 0:
            desc = tx.description.upper()
            is_sal = tx.is_salary or any(kw in desc for kw in (
                "SAL", "PAYROLL", "CREDIT", "NEFT CR", "NEFT-CR",
                "BY TRANSFER", "CMS", "IMPS CR", "RTGS CR"
            ))
            if is_sal:
                candidates.append(tx)

    if not candidates:
        return None

    # If net_pay is available, pick candidate closest in amount, or the highest credit in that window
    if slip.net_pay.is_found:
        try:
            net_val = float(slip.net_pay.value)
            candidates.sort(key=lambda c: abs(c.credit_amount - net_val))
        except ValueError:
            pass

    return candidates[0]

def check_salary_vs_bank_credits(packet: ApplicantPacketData) -> List[MismatchFlag]:
    """
    Deterministic check: compares net pay on each salary slip to the salary credit
    found in the bank statement. Flags if gap exceeds tolerance percentage and absolute INR.
    """
    flags: List[MismatchFlag] = []

    for idx, slip in enumerate(packet.salary_slips, start=1):
        if not slip.net_pay.is_found:
            continue

        try:
            net_pay = float(slip.net_pay.value)
        except (ValueError, TypeError):
            continue

        matching_tx = find_salary_credit_for_slip(slip, packet.bank_statement.transactions)
        if not matching_tx:
            # Handled by missing_credit_check
            continue

        credit_amount = matching_tx.credit_amount
        discrepancy = abs(net_pay - credit_amount)
        pct_diff = (discrepancy / net_pay) * 100.0 if net_pay > 0 else 0.0

        if (discrepancy > CONFIG.SALARY_TOLERANCE_ABSOLUTE_INR and
            pct_diff > CONFIG.SALARY_TOLERANCE_PERCENT):
            
            slip_loc = slip.net_pay.location
            tx_loc = matching_tx.location

            flags.append(MismatchFlag(
                flag_id=f"FLAG_SALARY_CREDIT_GAP_SLIP_{idx}",
                check_name="salary_vs_credit",
                severity=SeverityLevel.HIGH,
                short_title=f"Salary vs Bank Credit Gap: Slip #{idx} ({pct_diff:.1f}%)",
                llm_explanation=(
                    f"Salary slip #{idx} for period '{slip.pay_month_name.value}' reports Net Pay of "
                    f"₹{net_pay:,.2f} ({slip.document_name}, line {slip_loc.line if slip_loc else 'N/A'}), "
                    f"but bank statement records a salary credit of ₹{credit_amount:,.2f} on {matching_tx.date} "
                    f"({packet.bank_statement.document_name}, line {tx_loc.line if tx_loc else 'N/A'}). "
                    f"The gap of ₹{discrepancy:,.2f} ({pct_diff:.1f}%) exceeds the allowed {CONFIG.SALARY_TOLERANCE_PERCENT}% tolerance."
                ),
                evidence=[
                    EvidenceItem(
                        document=slip.document_name,
                        page=slip_loc.page if slip_loc else 1,
                        line=slip_loc.line if slip_loc else 1,
                        field_name="net_pay",
                        extracted_value=f"₹{net_pay:,.2f}",
                        raw_snippet=slip_loc.raw_text if slip_loc else ""
                    ),
                    EvidenceItem(
                        document=packet.bank_statement.document_name,
                        page=tx_loc.page if tx_loc else 1,
                        line=tx_loc.line if tx_loc else 1,
                        field_name="credit_amount",
                        extracted_value=f"₹{credit_amount:,.2f} ({matching_tx.description})",
                        raw_snippet=tx_loc.raw_text if tx_loc else ""
                    )
                ]
            ))

    return flags
