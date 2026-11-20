"""
Unit tests for evaluation metrics computation, split stratification, and metrics reporting.
"""

import os
import json
from eval import compute_split_metrics, is_field_match

def test_is_field_match():
    # Numeric matching within tolerance
    assert is_field_match(100000.0, 100000.0)
    assert is_field_match(100000.0, 100000.005)
    assert not is_field_match(100000.0, 100050.0)

    # String matching case-insensitive and stripped
    assert is_field_match("Infosys Limited", "INFOSYS LIMITED")
    assert is_field_match("PAN", "pan")
    assert not is_field_match("Infosys", "Wipro")

    # Missing / not_found values
    assert not is_field_match("Anything", "not_found")
    assert not is_field_match("Anything", None)

def test_compute_split_metrics_synthetic():
    sample_results = [
        # Clean packet
        {
            "applicant_id": "APP_001",
            "is_clean": True,
            "is_hard_negative": False,
            "hard_negative_type": None,
            "planted_mismatches": [],
            "planted_results": [],
            "planted_detected": 0,
            "has_flags": False,
            "field_matches": {"id_number": True, "slip_1_net_pay": True}
        },
        # Hard negative packet (clean with legitimate variation)
        {
            "applicant_id": "APP_002",
            "is_clean": True,
            "is_hard_negative": True,
            "hard_negative_type": "initials_vs_fullname",
            "planted_mismatches": [],
            "planted_results": [],
            "planted_detected": 0,
            "has_flags": False,
            "field_matches": {"id_number": True, "slip_1_net_pay": True}
        },
        # Mismatch packet (properly detected)
        {
            "applicant_id": "APP_003",
            "is_clean": False,
            "is_hard_negative": False,
            "hard_negative_type": None,
            "planted_mismatches": [{"type": "salary_gap"}],
            "planted_results": [{"type": "salary_gap", "detected": True}],
            "planted_detected": 1,
            "has_flags": True,
            "field_matches": {"id_number": True, "slip_1_net_pay": True}
        }
    ]

    metrics = compute_split_metrics(sample_results, "Test Split")
    assert metrics["total_packets"] == 3
    assert metrics["clean_count"] == 2
    assert metrics["mismatch_count"] == 1
    assert metrics["hard_negative_count"] == 1
    assert metrics["packet_recall_pct"] == 100.0
    assert metrics["packet_precision_pct"] == 100.0
    assert metrics["clean_false_alarm_rate_pct"] == 0.0
    assert metrics["hard_negative_false_alarm_rate_pct"] == 0.0
    assert metrics["planted_item_recall_pct"] == 100.0
    assert metrics["mismatch_type_breakdown"]["salary_gap"]["recall_pct"] == 100.0
    assert metrics["field_extraction_accuracy"]["overall_accuracy_pct"] == 100.0

def test_metrics_json_and_md_exist_and_valid():
    assert os.path.exists("metrics.json"), "metrics.json must exist"
    assert os.path.exists("metrics.md"), "metrics.md must exist"

    with open("metrics.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "held_out_test_split" in data
    held_out = data["held_out_test_split"]
    assert held_out["total_packets"] == 30
    assert held_out["packet_recall_pct"] == 100.0
    assert held_out["packet_precision_pct"] == 100.0
    assert held_out["clean_false_alarm_rate_pct"] == 0.0
    assert held_out["hard_negative_false_alarm_rate_pct"] == 0.0
    assert held_out["field_extraction_accuracy"]["overall_accuracy_pct"] == 100.0

    # Verify all 6 mismatch types in breakdown
    m_types = set(held_out["mismatch_type_breakdown"].keys())
    expected_m_types = {"name_mismatch", "dob_mismatch", "salary_gap", "missing_month", "employer_mismatch", "edited_duplicate_slip"}
    assert expected_m_types == m_types

    # Verify all 5 hard-negative types in breakdown
    hn_types = set(held_out["hard_negative_breakdown"].keys())
    expected_hn_types = {"initials_vs_fullname", "mohammed_spelling", "late_salary", "job_change", "swapped_name_order"}
    assert expected_hn_types == hn_types

    with open("metrics.md", "r", encoding="utf-8") as f:
        md = f.read()
    assert "Held-Out Test Split" in md
    assert "Planted Mismatch Detection Recall by Category" in md
    assert "False Alarm Rates on Clean and Hard-Negative Packets" in md
    assert "Extraction Accuracy per Field" in md
    assert "Confusion Matrix" in md
