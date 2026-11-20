"""
Unit tests for LLM Explanation Layer and fallback mode.
"""

from src.models import MismatchFlag, EvidenceItem, SeverityLevel
from src.llm.explainer import explain_flag, generate_templated_explanation

def test_templated_explanation_citations():
    flag = MismatchFlag(
        flag_id="FLAG_SALARY_GAP_01",
        check_name="salary_vs_credit",
        severity=SeverityLevel.HIGH,
        short_title="Salary vs Credit Gap",
        llm_explanation="",
        evidence=[
            EvidenceItem(
                document="SALARY_SLIP_1.pdf",
                page=1,
                line=10,
                field_name="net_pay",
                extracted_value="₹75,000.00"
            ),
            EvidenceItem(
                document="BANK_STATEMENT.pdf",
                page=1,
                line=22,
                field_name="credit_amount",
                extracted_value="₹52,000.00"
            )
        ]
    )

    explanation = explain_flag(flag)
    assert "SALARY_SLIP_1.pdf" in explanation
    assert "BANK_STATEMENT.pdf" in explanation
    assert "₹75,000.00" in explanation
    assert "₹52,000.00" in explanation
    assert "Page 1, line 10" in explanation
    assert "Page 1, line 22" in explanation

def test_all_rule_types_templated_fallbacks():
    rules = [
        "name_consistency",
        "dob_consistency",
        "salary_vs_credit",
        "missing_month_credit",
        "employer_consistency",
        "slip_arithmetic_duplicate"
    ]
    for r in rules:
        flag = MismatchFlag(
            flag_id=f"FLAG_{r}",
            check_name=r,
            severity=SeverityLevel.HIGH,
            short_title=f"Test {r}",
            llm_explanation="",
            evidence=[EvidenceItem(document="doc.pdf", page=1, line=5, field_name="f", extracted_value="v")]
        )
        exp = generate_templated_explanation(flag)
        assert len(exp) > 20
        assert "doc.pdf" in exp
