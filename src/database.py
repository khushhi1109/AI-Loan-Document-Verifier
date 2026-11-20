"""
Append-only SQLite audit log repository for AI Loan Document Verifier.
Logs all verification runs and underwriter accept/override decisions with triggers preventing UPDATE or DELETE.
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from src.config import CONFIG
from src.models import MismatchFlag

class AuditLogDatabase:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CONFIG.AUDIT_DB_PATH
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables and append-only triggers."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # System verification run logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                applicant_id TEXT NOT NULL,
                status TEXT NOT NULL,
                total_flags INTEGER NOT NULL,
                high_count INTEGER NOT NULL,
                medium_count INTEGER NOT NULL,
                low_count INTEGER NOT NULL,
                summary TEXT
            );
            """)

            # Detailed flags generated in runs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS flag_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                flag_id TEXT NOT NULL,
                applicant_id TEXT NOT NULL,
                check_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                short_title TEXT NOT NULL,
                explanation TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            """)

            # Human underwriter decisions (Accept / Override)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS underwriter_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                applicant_id TEXT NOT NULL,
                flag_id TEXT NOT NULL,
                action TEXT NOT NULL,
                underwriter_id TEXT NOT NULL,
                rationale TEXT,
                metadata_json TEXT
            );
            """)

            # Append-only triggers to reject any UPDATE or DELETE operations
            for table in ["system_runs", "flag_records", "underwriter_actions"]:
                cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS prevent_update_{table}
                BEFORE UPDATE ON {table}
                BEGIN
                    SELECT RAISE(FAIL, 'Updates forbidden on append-only audit log: table {table}');
                END;
                """)
                cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS prevent_delete_{table}
                BEFORE DELETE ON {table}
                BEGIN
                    SELECT RAISE(FAIL, 'Deletions forbidden on append-only audit log: table {table}');
                END;
                """)
            
            conn.commit()

    def log_system_run(self, applicant_id: str, flags: List[MismatchFlag], status: str = "COMPLETED", summary: str = "") -> int:
        """Appends a system verification run and all flags to the audit log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        high_c = sum(1 for f in flags if f.severity.value == "HIGH")
        med_c = sum(1 for f in flags if f.severity.value == "MEDIUM")
        low_c = sum(1 for f in flags if f.severity.value == "LOW")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO system_runs (timestamp, applicant_id, status, total_flags, high_count, medium_count, low_count, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, applicant_id, status, len(flags), high_c, med_c, low_c, summary))
            run_id = cursor.lastrowid

            for flag in flags:
                evidence_data = [e.model_dump() for e in flag.evidence]
                cursor.execute("""
                INSERT INTO flag_records (run_id, flag_id, applicant_id, check_name, severity, short_title, explanation, evidence_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    flag.flag_id,
                    applicant_id,
                    flag.check_name,
                    flag.severity.value,
                    flag.short_title,
                    flag.llm_explanation,
                    json.dumps(evidence_data),
                    timestamp
                ))
            conn.commit()
            return run_id

    def log_underwriter_action(
        self,
        applicant_id: str,
        flag_id: str,
        action: str,  # "ACCEPT" or "OVERRIDE"
        underwriter_id: str,
        rationale: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Logs an underwriter decision. If action is OVERRIDE, rationale is required."""
        action = action.upper()
        if action == "OVERRIDE" and (not rationale or not rationale.strip()):
            raise ValueError("Override action requires a written rationale explaining the decision.")

        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_str = json.dumps(metadata or {})

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO underwriter_actions (timestamp, applicant_id, flag_id, action, underwriter_id, rationale, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, applicant_id, flag_id, action, underwriter_id, rationale or "", metadata_str))
            action_id = cursor.lastrowid
            conn.commit()
            return action_id

    def get_actions_for_applicant(self, applicant_id: str) -> List[Dict[str, Any]]:
        """Retrieves underwriter actions for a specific applicant."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM underwriter_actions WHERE applicant_id = ? ORDER BY id ASC
            """, (applicant_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Retrieves all verification runs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_runs ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_actions(self) -> List[Dict[str, Any]]:
        """Retrieves all underwriter actions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM underwriter_actions ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
