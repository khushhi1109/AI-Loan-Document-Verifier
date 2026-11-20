"""
Unit tests for append-only SQLite audit log and tamper resistance.
"""

import pytest
import sqlite3
from src.database import AuditLogDatabase
from src.models import MismatchFlag, EvidenceItem, SeverityLevel

@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_audit.db")
    return AuditLogDatabase(db_path=db_file)

def test_audit_log_system_run(test_db):
    flag = MismatchFlag(
        flag_id="FLAG_TEST_01",
        check_name="name_consistency",
        severity=SeverityLevel.HIGH,
        short_title="Test Name Mismatch",
        llm_explanation="Primary name differs from payroll record.",
        evidence=[EvidenceItem(
            document="pan.pdf",
            page=1,
            line=4,
            field_name="applicant_name",
            extracted_value="John Doe"
        )]
    )
    run_id = test_db.log_system_run("APP_001", [flag], summary="Test run")
    assert run_id > 0

    runs = test_db.get_all_runs()
    assert len(runs) == 1
    assert runs[0]["applicant_id"] == "APP_001"
    assert runs[0]["high_count"] == 1

def test_underwriter_action_logging(test_db):
    # Logging accept action
    act_id = test_db.log_underwriter_action(
        applicant_id="APP_001",
        flag_id="FLAG_TEST_01",
        action="ACCEPT",
        underwriter_id="UW_42"
    )
    assert act_id > 0

    # Logging override action with required rationale
    ovr_id = test_db.log_underwriter_action(
        applicant_id="APP_001",
        flag_id="FLAG_TEST_01",
        action="OVERRIDE",
        underwriter_id="UW_42",
        rationale="Applicant provided marriage certificate validating surname change."
    )
    assert ovr_id > 0

    actions = test_db.get_actions_for_applicant("APP_001")
    assert len(actions) == 2
    assert actions[1]["action"] == "OVERRIDE"
    assert "marriage certificate" in actions[1]["rationale"]

def test_override_requires_rationale(test_db):
    with pytest.raises(ValueError, match="Override action requires a written rationale"):
        test_db.log_underwriter_action(
            applicant_id="APP_001",
            flag_id="FLAG_TEST_01",
            action="OVERRIDE",
            underwriter_id="UW_42",
            rationale=""
        )

def test_append_only_tamper_prevention(test_db):
    test_db.log_underwriter_action(
        applicant_id="APP_001",
        flag_id="FLAG_TEST_01",
        action="ACCEPT",
        underwriter_id="UW_42"
    )

    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        # Attempting UPDATE must fail due to trigger
        with pytest.raises(sqlite3.DatabaseError, match="Updates forbidden"):
            cursor.execute("UPDATE underwriter_actions SET action = 'OVERRIDE' WHERE id = 1")

        # Attempting DELETE must fail due to trigger
        with pytest.raises(sqlite3.DatabaseError, match="Deletions forbidden"):
            cursor.execute("DELETE FROM underwriter_actions WHERE id = 1")
