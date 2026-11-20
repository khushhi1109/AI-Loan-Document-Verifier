"""
Tests for src/report_generator.py
Covers CSV and PDF generation for clean and mismatch packets.
"""
import io
import csv
import json
import os
import pytest

from src.report_generator import generate_csv_report, generate_pdf_report
from src.pipeline import verify_applicant_packet
from src.database import AuditLogDatabase

PACKETS_DIR = "data/packets"
CLEAN_ID = "APP_001"
MISMATCH_ID = "APP_031"

@pytest.fixture(scope="module")
def db():
    return AuditLogDatabase(":memory:")

@pytest.fixture(scope="module")
def clean_packet_and_flags(db):
    pkt, flags, _ = verify_applicant_packet(os.path.join(PACKETS_DIR, CLEAN_ID), db=db, log_to_audit=False)
    return pkt, flags

@pytest.fixture(scope="module")
def mismatch_packet_and_flags(db):
    pkt, flags, _ = verify_applicant_packet(os.path.join(PACKETS_DIR, MISMATCH_ID), db=db, log_to_audit=False)
    return pkt, flags


class TestGenerateCsvReport:
    def test_csv_clean_packet_has_header_and_one_row(self, clean_packet_and_flags):
        pkt, flags = clean_packet_and_flags
        csv_str = generate_csv_report(pkt, flags, [])
        reader = list(csv.reader(io.StringIO(csv_str)))
        assert len(reader) >= 2, "CSV must have header + at least one data row"
        # Check key column headers present
        header = reader[0]
        for col in ("Applicant ID", "Flag ID", "Severity", "Underwriter Decision"):
            assert col in header, f"Missing column: {col}"

    def test_csv_mismatch_packet_has_flag_rows(self, mismatch_packet_and_flags):
        pkt, flags = mismatch_packet_and_flags
        csv_str = generate_csv_report(pkt, flags, [])
        reader = list(csv.reader(io.StringIO(csv_str)))
        # Header + at least as many rows as there are evidence items
        assert len(reader) > 1
        # Applicant ID present in data rows
        for row in reader[1:]:
            assert row[0] == pkt.applicant_id

    def test_csv_contains_underwriter_action_when_provided(self, mismatch_packet_and_flags):
        pkt, flags = mismatch_packet_and_flags
        fake_action = {
            "flag_id": flags[0].flag_id if flags else "FLAG_X",
            "action": "ACCEPT",
            "underwriter_id": "UW_TEST",
            "rationale": "",
            "timestamp": "2024-01-01T00:00:00"
        }
        csv_str = generate_csv_report(pkt, flags, [fake_action])
        assert "ACCEPT" in csv_str
        assert "UW_TEST" in csv_str

    def test_csv_returns_string(self, clean_packet_and_flags):
        pkt, flags = clean_packet_and_flags
        result = generate_csv_report(pkt, flags, [])
        assert isinstance(result, str)


class TestGeneratePdfReport:
    def test_pdf_returns_bytes(self, clean_packet_and_flags):
        pkt, flags = clean_packet_and_flags
        result = generate_pdf_report(pkt, flags, [])
        assert isinstance(result, (bytes, bytearray))

    def test_pdf_non_empty(self, clean_packet_and_flags):
        pkt, flags = clean_packet_and_flags
        result = generate_pdf_report(pkt, flags, [])
        assert len(result) > 1024, "PDF should be more than 1 KB"

    def test_pdf_starts_with_pdf_header(self, clean_packet_and_flags):
        pkt, flags = clean_packet_and_flags
        result = generate_pdf_report(pkt, flags, [])
        assert bytes(result)[:4] == b"%PDF", "File must start with PDF magic bytes"

    def test_pdf_mismatch_packet_non_empty(self, mismatch_packet_and_flags):
        pkt, flags = mismatch_packet_and_flags
        result = generate_pdf_report(pkt, flags, [])
        assert len(result) > 1024
