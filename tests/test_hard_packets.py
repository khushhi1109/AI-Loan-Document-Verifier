"""
Tests for the 15 hard stress-test packets (APP_061-075).
Verifies that:
  - All 15 packet directories and their PDFs exist on disk.
  - data/hard_ground_truth.json has exactly 15 entries.
  - The pipeline runs without crashing on every hard packet.
  - Clean / hard-negative packets produce 0 flags (no false alarms).
  - Mismatch packets (except the declared honest-limit APP_075) produce >= 1 flag.
  - APP_075 is correctly identified as an honest limit in ground truth.
"""
import json
import os
import pytest

from src.pipeline import verify_applicant_packet
from src.database import AuditLogDatabase

HARD_GT_PATH = "data/hard_ground_truth.json"
PACKETS_DIR = "data/packets"
HARD_IDS = [f"APP_0{i}" for i in range(61, 76)]


@pytest.fixture(scope="module")
def hard_gt():
    with open(HARD_GT_PATH, encoding="utf-8") as fh:
        return {g["applicant_id"]: g for g in json.load(fh)}


@pytest.fixture(scope="module")
def db():
    return AuditLogDatabase(":memory:")


class TestHardPacketFiles:
    def test_ground_truth_has_15_entries(self):
        with open(HARD_GT_PATH, encoding="utf-8") as fh:
            gt = json.load(fh)
        assert len(gt) == 15, f"Expected 15 entries in hard GT, got {len(gt)}"

    @pytest.mark.parametrize("app_id", HARD_IDS)
    def test_packet_directory_exists(self, app_id):
        pkt_dir = os.path.join(PACKETS_DIR, app_id)
        assert os.path.isdir(pkt_dir), f"Packet directory missing: {pkt_dir}"

    @pytest.mark.parametrize("app_id", HARD_IDS)
    def test_id_pdf_exists(self, app_id):
        pdf = os.path.join(PACKETS_DIR, app_id, "id_document.pdf")
        assert os.path.isfile(pdf), f"id_document.pdf missing for {app_id}"

    @pytest.mark.parametrize("app_id", HARD_IDS)
    def test_bank_pdf_exists(self, app_id):
        pdf = os.path.join(PACKETS_DIR, app_id, "bank_statement.pdf")
        assert os.path.isfile(pdf), f"bank_statement.pdf missing for {app_id}"

    @pytest.mark.parametrize("app_id", HARD_IDS)
    def test_at_least_one_salary_slip(self, app_id):
        slip1 = os.path.join(PACKETS_DIR, app_id, "salary_slip_1.pdf")
        assert os.path.isfile(slip1), f"salary_slip_1.pdf missing for {app_id}"


class TestHardPacketPipeline:
    @pytest.mark.parametrize("app_id", HARD_IDS)
    def test_pipeline_runs_without_crash(self, app_id, db):
        pkt_dir = os.path.join(PACKETS_DIR, app_id)
        # Must not raise
        pkt, flags, run_id = verify_applicant_packet(pkt_dir, db=db, log_to_audit=False)
        assert pkt is not None
        assert isinstance(flags, list)
        assert run_id is not None


class TestHardPacketDetection:
    # Clean / hard-negative packets: APP_061-067
    CLEAN_IDS = [f"APP_0{i}" for i in range(61, 68)]
    # Mismatch packets: APP_068-074 (APP_075 is excluded as honest limit)
    MISMATCH_IDS = [f"APP_0{i}" for i in range(68, 75)]

    @pytest.mark.parametrize("app_id", CLEAN_IDS)
    def test_clean_hard_packet_produces_no_flags(self, app_id, db):
        pkt_dir = os.path.join(PACKETS_DIR, app_id)
        _, flags, _ = verify_applicant_packet(pkt_dir, db=db, log_to_audit=False)
        assert len(flags) == 0, (
            f"{app_id} is a clean/hard-negative packet but got flags: "
            + str([f.check_name for f in flags])
        )

    @pytest.mark.parametrize("app_id", MISMATCH_IDS)
    def test_mismatch_hard_packet_produces_at_least_one_flag(self, app_id, db):
        pkt_dir = os.path.join(PACKETS_DIR, app_id)
        _, flags, _ = verify_applicant_packet(pkt_dir, db=db, log_to_audit=False)
        assert len(flags) >= 1, (
            f"{app_id} is a mismatch packet but no flags were produced. "
            "Check the relevant check rule."
        )

    def test_app075_is_declared_honest_limit(self, hard_gt):
        entry = hard_gt["APP_075"]
        assert entry.get("honest_limit") is True, (
            "APP_075 must be tagged honest_limit=True in hard_ground_truth.json"
        )
        assert entry["is_clean"] is False, "APP_075 is a mismatch packet"

    def test_app075_produces_no_flags(self, db):
        """APP_075 is an honest limit: unreadable pay_period → 0 flags (expected)."""
        pkt_dir = os.path.join(PACKETS_DIR, "APP_075")
        _, flags, _ = verify_applicant_packet(pkt_dir, db=db, log_to_audit=False)
        assert len(flags) == 0, (
            "APP_075 should produce 0 flags (honest limit). "
            "If this passes unexpectedly, update the honest_limit annotation."
        )
