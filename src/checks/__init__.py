"""
Deterministic check functions for AI Loan Document Verifier.
"""
from src.checks.name_check import check_name_consistency
from src.checks.dob_check import check_dob_consistency
from src.checks.salary_vs_credit_check import check_salary_vs_bank_credits
from src.checks.missing_credit_check import check_missing_month_credits
from src.checks.employer_check import check_employer_consistency
from src.checks.slip_arithmetic_check import check_slip_arithmetic_and_authenticity

__all__ = [
    "check_name_consistency",
    "check_dob_consistency",
    "check_salary_vs_bank_credits",
    "check_missing_month_credits",
    "check_employer_consistency",
    "check_slip_arithmetic_and_authenticity"
]
