"""
End-to-end verification pipeline coordinating PDF extraction, deterministic checks,
LLM explanation enrichment, and append-only SQLite audit logging.
"""

from typing import List, Tuple, Union
from src.models import ApplicantPacketData, MismatchFlag, SeverityLevel
from src.extractor.pdf_extractor import extract_packet
from src.checks import (
    check_name_consistency,
    check_dob_consistency,
    check_salary_vs_bank_credits,
    check_missing_month_credits,
    check_employer_consistency,
    check_slip_arithmetic_and_authenticity
)
from src.llm.explainer import explain_flag
from src.database import AuditLogDatabase

SEVERITY_ORDER = {
    SeverityLevel.HIGH: 0,
    SeverityLevel.MEDIUM: 1,
    SeverityLevel.LOW: 2
}

def verify_applicant_packet(
    packet_source: Union[str, ApplicantPacketData],
    db: AuditLogDatabase = None,
    log_to_audit: bool = True
) -> Tuple[ApplicantPacketData, List[MismatchFlag], int]:
    """
    Executes end-to-end loan document verification:
    1. Extracts structured fields with line citations.
    2. Runs all 6 deterministic check functions.
    3. Enriches flags with LLM plain-language explanations.
    4. Sorts flags by severity (HIGH -> MEDIUM -> LOW).
    5. Commits verification run and citations to SQLite append-only audit log.
    """
    if isinstance(packet_source, str):
        packet = extract_packet(packet_source)
    else:
        packet = packet_source

    flags: List[MismatchFlag] = []

    # Run all 6 deterministic checks
    flags.extend(check_name_consistency(packet))
    flags.extend(check_dob_consistency(packet))
    flags.extend(check_salary_vs_bank_credits(packet))
    flags.extend(check_missing_month_credits(packet))
    flags.extend(check_employer_consistency(packet))
    flags.extend(check_slip_arithmetic_and_authenticity(packet))

    # Enrich flags with LLM plain language explanations citing documents & lines
    for f in flags:
        f.llm_explanation = explain_flag(f)

    # Sort flags by severity (HIGH first)
    flags.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

    # Log to append-only audit database
    run_id = -1
    if log_to_audit:
        if db is None:
            db = AuditLogDatabase()
        run_id = db.log_system_run(
            applicant_id=packet.applicant_id,
            flags=flags,
            status="COMPLETED",
            summary=f"Automated verification produced {len(flags)} flag(s)."
        )

    return packet, flags, run_id
