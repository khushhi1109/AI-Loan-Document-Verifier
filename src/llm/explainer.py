"""
LLM Explanation Layer for Underwriter Discrepancy Flags.
Uses Google Gemini when configured, or a structured, deterministic templated fallback
(MOCK mode) ensuring complete offline usability and zero external API dependencies.
"""

import json
from urllib import request
from typing import Optional
from src.config import CONFIG
from src.models import MismatchFlag

SYSTEM_INSTRUCTION = """You are an Underwriting Risk Assistant. Your role is to explain document discrepancies to a human loan underwriter in crisp, objective, factual language.
Guidelines:
1. NEVER decide whether to approve or reject the loan application.
2. Specifically cite each document, page, and line number where the conflicting data appears.
3. Highlight the exact numerical or textual discrepancy.
4. Keep the explanation under 3-4 sentences.
"""

def generate_templated_explanation(flag: MismatchFlag) -> str:
    """
    Deterministic fallback explanation citing documents, lines, and values.
    Used in MOCK mode or whenever the Gemini API is unreachable.
    """
    evidence_cites = []
    for ev in flag.evidence:
        line_info = f"line {ev.line}" if ev.line and ev.line > 0 else "line N/A"
        evidence_cites.append(
            f"'{ev.document}' (Page {ev.page}, {line_info}): {ev.field_name} = '{ev.extracted_value}'"
        )
    citations_str = " vs ".join(evidence_cites)

    if flag.check_name == "name_consistency":
        return (
            f"A name discrepancy was detected across application documents. "
            f"Citations: {citations_str}. "
            f"Please verify government ID records against payroll details."
        )
    elif flag.check_name == "dob_consistency":
        return (
            f"A Date of Birth mismatch was identified between submitted records. "
            f"Citations: {citations_str}. "
            f"Please ensure identity proof matches payroll onboarding records."
        )
    elif flag.check_name == "salary_vs_credit":
        return (
            f"Net salary stated on payslip does not reconcile with bank salary credit. "
            f"Citations: {citations_str}. "
            f"Review bank narration and net pay breakdown for undisclosed deductions or tampering."
        )
    elif flag.check_name == "missing_month_credit":
        return (
            f"No corresponding salary credit transaction was found in the bank statement for the stated pay cycle. "
            f"Citations: {citations_str}. "
            f"Inquire whether salary was deposited into an alternate bank account."
        )
    elif flag.check_name == "employer_consistency":
        return (
            f"Salary slip employer does not match the company narration in the bank salary deposit. "
            f"Citations: {citations_str}. "
            f"Check if employer processes payroll through a parent group entity or third-party agency."
        )
    elif flag.check_name == "slip_arithmetic_duplicate":
        return (
            f"Payslip authenticity alert: mathematical discrepancy or re-used identifier detected. "
            f"Citations: {citations_str}. "
            f"Verify payslip PDF metadata and calculation integrity."
        )
    else:
        return f"Discrepancy identified under rule '{flag.check_name}'. Citations: {citations_str}."

def call_gemini_api(flag: MismatchFlag, api_key: str) -> Optional[str]:
    """Calls Gemini REST API directly without heavy external client dependencies."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{CONFIG.GEMINI_MODEL}:generateContent?key={api_key}"
        
        evidence_text = "\n".join([
            f"- Document: {e.document}, Page: {e.page}, Line: {e.line}, Field: {e.field_name}, Value: {e.extracted_value}"
            for e in flag.evidence
        ])
        
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"Rule: {flag.check_name} ({flag.severity.value})\n"
            f"Title: {flag.short_title}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Explain this discrepancy concisely with exact citations for the underwriter:"
        )

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 200
            }
        }

        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
    except Exception:
        # Graceful fallback on any network/API error
        pass
    return None

def explain_flag(flag: MismatchFlag) -> str:
    """
    Generates a natural language explanation for a flag.
    Uses Gemini API if configured and LLM_MODE is 'GEMINI', otherwise uses templated fallback.
    """
    mode = CONFIG.LLM_MODE.upper()
    api_key = CONFIG.GEMINI_API_KEY

    if mode == "GEMINI" and api_key and api_key.strip():
        llm_result = call_gemini_api(flag, api_key)
        if llm_result:
            return llm_result

    # Fallback / MOCK mode
    return generate_templated_explanation(flag)
