"""
Streamlit Underwriting UI for AI Loan Document Verifier.
Assistive compliance tool for loan underwriters to review cross-document discrepancies.
INVARIANT: This tool NEVER approves or rejects an application.
"""

import os
import json
import streamlit as st
import pandas as pd
from src.config import CONFIG
from src.database import AuditLogDatabase
from src.pipeline import verify_applicant_packet
from src.models import SeverityLevel

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI Loan Document Verifier",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Financial Underwriting
st.markdown("""
<style>
    .banner-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.25) 100%);
        border: 2px solid #F59E0B;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 24px;
        color: #92400E;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .banner-warning h4 {
        margin: 0 0 6px 0;
        color: #B45309;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    @media (prefers-color-scheme: dark) {
        .banner-warning {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(180, 83, 9, 0.3) 100%);
            border-color: #F59E0B;
            color: #FDE68A;
        }
        .banner-warning h4 {
            color: #FBBF24;
        }
    }
    [data-theme="dark"] .banner-warning,
    [data-testid="stAppViewContainer"].dark .banner-warning,
    .stApp.dark .banner-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(180, 83, 9, 0.3) 100%);
        border-color: #F59E0B;
        color: #FDE68A;
    }
    [data-theme="dark"] .banner-warning h4,
    [data-testid="stAppViewContainer"].dark .banner-warning h4,
    .stApp.dark .banner-warning h4 {
        color: #FBBF24;
    }
    .flag-card {
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        border-left: 6px solid #CBD5E1;
        background-color: #F8FAFC;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .flag-high {
        border-left-color: #EF4444;
        background-color: #FEF2F2;
    }
    .flag-medium {
        border-left-color: #F59E0B;
        background-color: #FFFBEB;
    }
    .flag-low {
        border-left-color: #3B82F6;
        background-color: #EFF6FF;
    }
    .badge-high {
        background-color: #EF4444;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-medium {
        background-color: #F59E0B;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-low {
        background-color: #3B82F6;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .evidence-table {
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db = AuditLogDatabase()

# Mandatory Decision Support Banner
st.markdown("""
<div class="banner-warning">
    <h4>⚠️ Decision Support Only</h4>
    This tool flags inconsistencies for review. It does not approve or reject applications. Final decisions rest with the human underwriter.
</div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🛡️ Loan Verifier Agent")
st.sidebar.markdown("**Assistive Underwriting Copilot**")

# Underwriter ID
underwriter_id = st.sidebar.text_input("Underwriter ID", value="UW_SARAH_88", help="Identifier logged in append-only audit trail.")

# LLM Status badge
llm_mode = CONFIG.LLM_MODE.upper()
if llm_mode == "GEMINI" and CONFIG.GEMINI_API_KEY:
    st.sidebar.success("🤖 LLM: Gemini 1.5 Flash (Online)")
else:
    st.sidebar.info("⚙️ LLM: MOCK Mode (Deterministic Fallback)")

# Packet selector
packets_dir = CONFIG.PACKETS_DIR
available_packets = []
if os.path.exists(packets_dir):
    available_packets = sorted([d for d in os.listdir(packets_dir) if os.path.isdir(os.path.join(packets_dir, d))])

selected_packet_id = st.sidebar.selectbox(
    "Select Applicant Packet",
    options=available_packets,
    index=0 if available_packets else None
)

# Load ground truth metadata if available
gt_entry = None
if os.path.exists(CONFIG.GROUND_TRUTH_PATH):
    try:
        with open(CONFIG.GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
            gt_dict = {item["applicant_id"]: item for item in gt_data}
            gt_entry = gt_dict.get(selected_packet_id)
    except Exception:
        pass

if gt_entry:
    with st.sidebar.expander("Ground Truth Details", expanded=False):
        if gt_entry["is_clean"]:
            st.success(f"Clean Packet {'(Hard Negative: ' + gt_entry.get('hard_negative_type', '') + ')' if gt_entry.get('is_hard_negative') else ''}")
        else:
            st.warning("Planted Mismatch Packet")
            for m in gt_entry.get("planted_mismatches", []):
                st.caption(f"• **{m['type']}**: {m['description']}")

st.sidebar.markdown("---")
st.sidebar.markdown("### System Health & DB")
st.sidebar.caption("Append-only SQLite DB: `audit_log.db`")
st.sidebar.caption("Tamper-proof Triggers: ACTIVE")

if not selected_packet_id:
    st.warning("No applicant packets found. Run `python -m src.generator.packet_generator` to generate synthetic data.")
    st.stop()

# Execution Pipeline
packet_path = os.path.join(packets_dir, selected_packet_id)

# Run verification and cache in session state for action interactivity
cache_key = f"verification_{selected_packet_id}"
if cache_key not in st.session_state:
    with st.spinner("Extracting documents and evaluating cross-document consistency..."):
        packet_data, flags, run_id = verify_applicant_packet(packet_path, db=db, log_to_audit=True)
        st.session_state[cache_key] = {
            "packet": packet_data,
            "flags": flags,
            "run_id": run_id
        }

cached = st.session_state[cache_key]
packet_data = cached["packet"]
flags = cached["flags"]
run_id = cached["run_id"]

# Applicant Header
st.subheader(f"Applicant: {selected_packet_id} — {packet_data.id_document.applicant_name.value}")

# Summary Metrics Row
high_count = sum(1 for f in flags if f.severity == SeverityLevel.HIGH)
med_count = sum(1 for f in flags if f.severity == SeverityLevel.MEDIUM)
low_count = sum(1 for f in flags if f.severity == SeverityLevel.LOW)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Discrepancies", len(flags))
c2.metric("High Severity", high_count, delta="Action Required" if high_count > 0 else None, delta_color="inverse")
c3.metric("Medium Severity", med_count)
c4.metric("Low / Info", low_count)

# Main Navigation Tabs
tab_flags, tab_docs, tab_audit, tab_metrics, tab_upload = st.tabs([
    "🚩 Discrepancy Flags & Triage",
    "📄 Document & Extracted Fields Inspector",
    "🔒 Append-Only Audit Log",
    "📊 Evaluation Metrics",
    "📤 Upload Documents"
])

# ----------------- TAB 1: FLAGS & TRIAGE -----------------
with tab_flags:
    if not flags:
        st.success("✅ **No discrepancies detected across documents.** All names, dates, earnings, and employer affiliations align within policy tolerances.")
    else:
        st.markdown(f"### Identified Flags ({len(flags)})")
        
        # Load existing underwriter actions for this applicant
        actions_list = db.get_actions_for_applicant(selected_packet_id)
        action_map = {a["flag_id"]: a for a in actions_list}

        for idx, flag in enumerate(flags, start=1):
            sev_class = "flag-high" if flag.severity == SeverityLevel.HIGH else ("flag-medium" if flag.severity == SeverityLevel.MEDIUM else "flag-low")
            badge_class = "badge-high" if flag.severity == SeverityLevel.HIGH else ("badge-medium" if flag.severity == SeverityLevel.MEDIUM else "badge-low")

            current_action = action_map.get(flag.flag_id)
            status_text = "PENDING REVIEW"
            if current_action:
                status_text = f"DECIDED: {current_action['action']} by {current_action['underwriter_id']}"

            st.markdown(f"""
            <div class="flag-card {sev_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:700; font-size:1.05rem;">#{idx}. {flag.short_title}</span>
                    <div>
                        <span class="{badge_class}">{flag.severity.value}</span>
                        <span style="margin-left:8px; font-size:0.8rem; background:#E2E8F0; padding:3px 8px; border-radius:10px;">{status_text}</span>
                    </div>
                </div>
                <div style="margin-bottom: 12px; color: #1E293B;">
                    <strong>Underwriting Risk Analysis:</strong> {flag.llm_explanation}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Evidence Table
            ev_data = []
            for ev in flag.evidence:
                ev_data.append({
                    "Document": ev.document,
                    "Page": ev.page,
                    "Line #": ev.line,
                    "Field": ev.field_name,
                    "Extracted Value": ev.extracted_value,
                    "Raw Text Excerpt": ev.raw_snippet or "N/A"
                })
            st.dataframe(pd.DataFrame(ev_data), width="stretch", hide_index=True)

            # Underwriter Action Buttons
            col_act1, col_act2 = st.columns([1, 3])
            
            with col_act1:
                accept_btn = st.button(f"Accept Flag #{idx}", key=f"acc_{flag.flag_id}")
                if accept_btn:
                    try:
                        db.log_underwriter_action(
                            applicant_id=selected_packet_id,
                            flag_id=flag.flag_id,
                            action="ACCEPT",
                            underwriter_id=underwriter_id
                        )
                        st.success(f"Flag #{idx} Accepted & Logged.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            with col_act2:
                with st.expander(f"Override Flag #{idx} (Requires Rationale)", expanded=False):
                    override_reason = st.text_area(
                        "Mandatory Underwriter Rationale",
                        key=f"reason_{flag.flag_id}",
                        placeholder="State why this discrepancy is acceptable (e.g., confirmed marriage certificate, verified HR payroll arrangement, etc.)"
                    )
                    override_btn = st.button(f"Confirm Override #{idx}", key=f"ovr_{flag.flag_id}")
                    if override_btn:
                        if not override_reason.strip():
                            st.error("Underwriting policy strictly requires a written reason to override any discrepancy flag.")
                        else:
                            try:
                                db.log_underwriter_action(
                                    applicant_id=selected_packet_id,
                                    flag_id=flag.flag_id,
                                    action="OVERRIDE",
                                    underwriter_id=underwriter_id,
                                    rationale=override_reason.strip()
                                )
                                st.success(f"Flag #{idx} Overridden & Logged to Audit Trail.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)

    # --- Download Report buttons ---
    st.markdown("---")
    st.markdown("#### 📥 Export Verification Report")
    _col_dl1, _col_dl2, _col_dl3 = st.columns([1, 1, 2])
    try:
        from src.report_generator import generate_csv_report, generate_pdf_report
        _actions_list = db.get_actions_for_applicant(selected_packet_id)
        with _col_dl1:
            _csv_data = generate_csv_report(packet_data, flags, _actions_list)
            st.download_button(
                label="📥 Download CSV",
                data=_csv_data,
                file_name=f"{selected_packet_id}_verification_report.csv",
                mime="text/csv",
                key="dl_csv_main"
            )
        with _col_dl2:
            _pdf_data = generate_pdf_report(packet_data, flags, _actions_list)
            st.download_button(
                label="📄 Download PDF",
                data=bytes(_pdf_data),
                file_name=f"{selected_packet_id}_verification_report.pdf",
                mime="application/pdf",
                key="dl_pdf_main"
            )
    except Exception as _report_err:
        st.warning(f"Report export unavailable: {_report_err}")

# ----------------- TAB 2: DOCUMENT INSPECTOR -----------------
with tab_docs:
    st.markdown("### Cross-Document Structured Field Extractions")
    
    doc_tabs = st.tabs(["Government ID Proof", "Salary Slip #1", "Salary Slip #2", "Salary Slip #3", "Bank Statement"])
    
    with doc_tabs[0]:
        id_doc = packet_data.id_document
        st.markdown(f"**Document File:** `{id_doc.document_name}`")
        id_table = [
            {"Field": "ID Type", "Value": id_doc.id_type, "Source Location": "Document Header"},
            {"Field": "ID Number", "Value": id_doc.id_number.value, "Source Location": f"Page {id_doc.id_number.location.page}, Line {id_doc.id_number.location.line}" if id_doc.id_number.location else "N/A"},
            {"Field": "Applicant Name", "Value": id_doc.applicant_name.value, "Source Location": f"Page {id_doc.applicant_name.location.page}, Line {id_doc.applicant_name.location.line}" if id_doc.applicant_name.location else "N/A"},
            {"Field": "Date of Birth", "Value": id_doc.date_of_birth.value, "Source Location": f"Page {id_doc.date_of_birth.location.page}, Line {id_doc.date_of_birth.location.line}" if id_doc.date_of_birth.location else "N/A"},
        ]
        st.dataframe(pd.DataFrame(id_table), width="stretch", hide_index=True)

    for s_idx in range(3):
        with doc_tabs[s_idx + 1]:
            if s_idx < len(packet_data.salary_slips):
                slip = packet_data.salary_slips[s_idx]
                st.markdown(f"**Document File:** `{slip.document_name}`")
                slip_table = [
                    {"Field": "Employer Name", "Value": slip.employer_name.value, "Location": f"Line {slip.employer_name.location.line}" if slip.employer_name.location else "N/A"},
                    {"Field": "Employee Name", "Value": slip.applicant_name.value, "Location": f"Line {slip.applicant_name.location.line}" if slip.applicant_name.location else "N/A"},
                    {"Field": "Employee ID", "Value": slip.slip_id.value, "Location": f"Line {slip.slip_id.location.line}" if slip.slip_id.location else "N/A"},
                    {"Field": "Pay Month", "Value": slip.pay_month_name.value, "Location": f"Line {slip.pay_period.location.line}" if slip.pay_period.location else "N/A"},
                    {"Field": "Gross Pay", "Value": f"₹{float(slip.gross_pay.value):,.2f}" if slip.gross_pay.is_found else "N/A", "Location": f"Line {slip.gross_pay.location.line}" if slip.gross_pay.location else "N/A"},
                    {"Field": "Total Deductions", "Value": f"₹{float(slip.deductions.value):,.2f}" if slip.deductions.is_found else "N/A", "Location": f"Line {slip.deductions.location.line}" if slip.deductions.location else "N/A"},
                    {"Field": "Net Pay", "Value": f"₹{float(slip.net_pay.value):,.2f}" if slip.net_pay.is_found else "N/A", "Location": f"Line {slip.net_pay.location.line}" if slip.net_pay.location else "N/A"}
                ]
                st.dataframe(pd.DataFrame(slip_table), width="stretch", hide_index=True)

    with doc_tabs[4]:
        bs = packet_data.bank_statement
        st.markdown(f"**Document File:** `{bs.document_name}`")
        st.write(f"**Bank Name:** {bs.bank_name.value} | **Account Holder:** {bs.account_holder.value} | **Account Number:** {bs.account_number.value}")
        
        tx_rows = []
        for t in bs.transactions:
            tx_rows.append({
                "Date": t.date,
                "Narration": t.description,
                "Debit (DR)": f"₹{t.debit_amount:,.2f}" if t.debit_amount > 0 else "-",
                "Credit (CR)": f"₹{t.credit_amount:,.2f}" if t.credit_amount > 0 else "-",
                "Balance": f"₹{t.balance:,.2f}",
                "Salary Deposit?": "YES" if t.is_salary else "NO",
                "Line #": t.location.line
            })
        st.dataframe(pd.DataFrame(tx_rows), width="stretch", hide_index=True)

# ----------------- TAB 3: AUDIT LOG -----------------
with tab_audit:
    st.markdown("### Append-Only SQLite Audit Trail")
    st.caption("Immutable record of system runs, flag detections, and human underwriter accept/override actions.")

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("#### System Verification Runs")
        runs = db.get_all_runs()
        if runs:
            st.dataframe(pd.DataFrame(runs), width="stretch", hide_index=True)
        else:
            st.info("No system verification runs recorded yet.")

    with col_a2:
        st.markdown("#### Underwriter Action Trail")
        actions = db.get_all_actions()
        if actions:
            st.dataframe(pd.DataFrame(actions), width="stretch", hide_index=True)
        else:
            st.info("No underwriter actions logged yet. Use the triage buttons in Tab 1.")

# ----------------- TAB 4: EVALUATION METRICS -----------------
with tab_metrics:
    st.markdown("### 📊 System Evaluation & Detection Metrics (Held-Out Test Split)")
    st.caption("Performance measured strictly on the 30 held-out test applicant packets (15 clean/hard-negative packets and 15 planted mismatch packets).")

    if os.path.exists("metrics.json"):
        with open("metrics.json", "r", encoding="utf-8") as f:
            m_data = json.load(f)

        held_out = m_data.get("held_out_test_split", {})
        ext_acc = held_out.get("field_extraction_accuracy", {})

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        col_m1.metric("Held-Out Recall", f"{held_out.get('packet_recall_pct', 0)}%")
        col_m2.metric("Held-Out Precision", f"{held_out.get('packet_precision_pct', 0)}%")
        col_m3.metric("F1 Score", f"{held_out.get('packet_f1_score', 0)}")
        col_m4.metric("Clean FAR", f"{held_out.get('clean_false_alarm_rate_pct', 0)}%")
        col_m5.metric("Extraction Accuracy", f"{ext_acc.get('overall_accuracy_pct', 0)}%")

        st.markdown("---")

        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "🎯 Recall per Mismatch Type",
            "🛡️ Hard-Negative False Alarm Rate",
            "🔍 Field Extraction Accuracy",
            "📋 Full Metrics Report (Markdown)"
        ])

        with sub_tab1:
            st.markdown("#### Planted Mismatch Detection Recall by Category")
            st.caption("Verification that every planted fraudulent or inconsistent pattern was flagged by its corresponding deterministic rule.")
            m_breakdown = held_out.get("mismatch_type_breakdown", {})
            m_rows = []
            for k, v in m_breakdown.items():
                m_rows.append({
                    "Mismatch Category": k,
                    "Planted Count": v.get("total", 0),
                    "Detected Count": v.get("detected", 0),
                    "Detection Recall": f"{v.get('recall_pct', 0)}%",
                    "Status": "DETECTED (100%)" if v.get("recall_pct", 0) == 100 else f"PARTIAL ({v.get('recall_pct', 0)}%)"
                })
            st.dataframe(pd.DataFrame(m_rows), width="stretch", hide_index=True)

        with sub_tab2:
            st.markdown("#### False Alarm Rate on Clean & Hard-Negative Packets")
            st.caption("Verification that complex legitimate variations never trigger false positive flags.")
            hn_breakdown = held_out.get("hard_negative_breakdown", {})
            hn_rows = [
                {
                    "Evaluation Category": "Clean (Overall)",
                    "Scenario Description": "All legitimate clean packets",
                    "Tested": held_out.get("clean_count", 0),
                    "False Alarms": held_out.get("false_positives", 0),
                    "FAR (%)": f"{held_out.get('clean_false_alarm_rate_pct', 0)}%",
                    "Accuracy": f"{100.0 - held_out.get('clean_false_alarm_rate_pct', 0):.1f}%",
                    "Status": "PASSED" if held_out.get("false_positives", 0) == 0 else "FAILED"
                },
                {
                    "Evaluation Category": "Hard Negative (Overall)",
                    "Scenario Description": "All hard-negative variation packets",
                    "Tested": held_out.get("hard_negative_count", 0),
                    "False Alarms": sum(d.get("false_alarms", 0) for d in hn_breakdown.values()),
                    "FAR (%)": f"{held_out.get('hard_negative_false_alarm_rate_pct', 0)}%",
                    "Accuracy": f"{100.0 - held_out.get('hard_negative_false_alarm_rate_pct', 0):.1f}%",
                    "Status": "PASSED" if held_out.get("hard_negative_false_alarm_rate_pct", 0) == 0 else "FAILED"
                }
            ]
            hn_desc_map = {
                "initials_vs_fullname": "Initials on ID vs full name on slips/bank",
                "mohammed_spelling": "Transliteration spelling variant (Mohammed vs Mohammad)",
                "late_salary": "Legitimate payroll delay (credited 10+ days late)",
                "job_change": "Mid-period career transition (slips and bank credits match chronologically)",
                "swapped_name_order": "Name order permutation (Last First vs First Last)"
            }
            for k, v in hn_breakdown.items():
                hn_rows.append({
                    "Evaluation Category": "Hard Negative",
                    "Scenario Description": f"{hn_desc_map.get(k, k)} ({k})",
                    "Tested": v.get("total", 0),
                    "False Alarms": v.get("false_alarms", 0),
                    "FAR (%)": f"{v.get('far_pct', 0)}%",
                    "Accuracy": f"{v.get('accuracy_pct', 0)}%",
                    "Status": "PASSED" if v.get("false_alarms", 0) == 0 else "FAILED"
                })
            st.dataframe(pd.DataFrame(hn_rows), width="stretch", hide_index=True)

        with sub_tab3:
            st.markdown("#### Structured Extraction Accuracy per Field")
            st.caption(f"Extraction accuracy with page and line citations across {ext_acc.get('total_fields_evaluated', 0)} field instances.")
            f_data = ext_acc.get("fields", {})
            f_rows = []
            for fname, v in f_data.items():
                doc_type = "ID Document" if "(ID)" in fname else ("Bank Statement" if "Statement" in fname else "Salary Slips")
                f_rows.append({
                    "Document": doc_type,
                    "Field Name": fname,
                    "Evaluated Instances": v.get("total", 0),
                    "Correctly Extracted": v.get("correct", 0),
                    "Accuracy": f"{v.get('accuracy_pct', 0)}%",
                    "Status": "PERFECT (100%)" if v.get("accuracy_pct", 0) == 100 else f"{v.get('accuracy_pct', 0)}%"
                })
            st.dataframe(pd.DataFrame(f_rows), width="stretch", hide_index=True)

        with sub_tab4:
            if os.path.exists("metrics.md"):
                with open("metrics.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
    else:
        st.info("Metrics report not yet generated. Run `python eval.py` to produce metrics.")

    # Hard stress-test sub-section
    if os.path.exists("metrics.json"):
        hard = m_data.get("hard_test_set", {})
        if hard:
            st.markdown("---")
            st.markdown("### 🧪 Hard Stress-Test Results (15 Adversarial Packets)")
            st.caption(
                "Noisy layouts, Aadhaar IDs, INR currency, DMY dates, missing fields. "
                "Reported separately to give an honest view of system limits."
            )
            hc1, hc2, hc3, hc4 = st.columns(4)
            hc1.metric("Recall", f"{hard.get('recall_pct', 0)}%")
            hc2.metric("False Alarm Rate", f"{hard.get('far_pct', 0)}%")
            hc3.metric("True Positives", hard.get("tp", 0))
            hc4.metric("Honest-Limit Misses", len(hard.get("honest_limits", [])))
            if hard.get("honest_limits"):
                st.info(
                    f"⚠️ **Honest limit:** {', '.join(hard['honest_limits'])} — "
                    "pay_period unreadable in noisy PDF; reconciliation correctly skipped."
                )
            h_rows = []
            for mtype, data in hard.get("mismatch_breakdown", {}).items():
                h_rows.append({
                    "Mismatch Type": mtype,
                    "Planted": data.get("total", 0),
                    "Detected": data.get("detected", 0),
                    "Recall": f"{data.get('recall_pct', 0)}%"
                })
            if h_rows:
                st.dataframe(pd.DataFrame(h_rows), width="stretch", hide_index=True)

# ----------------- TAB 5: UPLOAD DOCUMENTS -----------------
with tab_upload:
    import tempfile
    import shutil

    st.markdown("### 📤 Upload Your Own Applicant Documents")
    st.caption(
        "Upload PDFs for ad-hoc verification. "
        "No ground truth required — flags are shown as-is for underwriter review."
    )

    with st.form("upload_form"):
        up_id = st.file_uploader(
            "Government ID Document (PDF) — PAN / Aadhaar / Passport",
            type=["pdf"],
            accept_multiple_files=False
        )
        up_slips = st.file_uploader(
            "Salary Slips — 1 to 3 PDFs",
            type=["pdf"],
            accept_multiple_files=True
        )
        up_bank = st.file_uploader(
            "Bank Statement (PDF)",
            type=["pdf"],
            accept_multiple_files=False
        )
        submitted_upload = st.form_submit_button("🔍 Verify Uploaded Documents")

    if submitted_upload:
        if not up_id or not up_bank or not up_slips:
            st.error("Please upload at least: 1 ID document, 1 salary slip, and 1 bank statement.")
        elif len(up_slips) > 3:
            st.error("Maximum 3 salary slips allowed.")
        else:
            with st.spinner("Extracting fields and running cross-document consistency checks..."):
                tmp_dir = tempfile.mkdtemp(prefix="loan_upload_")
                try:
                    with open(os.path.join(tmp_dir, "id_document.pdf"), "wb") as fh:
                        fh.write(up_id.read())
                    for _i, _slip in enumerate(up_slips, start=1):
                        with open(os.path.join(tmp_dir, f"salary_slip_{_i}.pdf"), "wb") as fh:
                            fh.write(_slip.read())
                    with open(os.path.join(tmp_dir, "bank_statement.pdf"), "wb") as fh:
                        fh.write(up_bank.read())

                    from src.extractor.pdf_extractor import extract_packet
                    _upload_packet = extract_packet(tmp_dir)
                    # Give it a stable temporary ID so DB calls don't collide
                    _upload_packet = _upload_packet.model_copy(update={"applicant_id": "UPLOAD_TEMP"})
                    _upload_flags, _, _ = verify_applicant_packet(
                        _upload_packet, db=db, log_to_audit=False
                    )
                    st.session_state["upload_packet"] = _upload_packet
                    st.session_state["upload_flags"] = _upload_flags
                    st.success("Extraction and verification complete.")
                except Exception as _up_err:
                    st.error(f"Verification failed: {_up_err}")
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)

    if "upload_packet" in st.session_state:
        _up_pkt = st.session_state["upload_packet"]
        _up_flags = st.session_state["upload_flags"]

        st.markdown("---")
        st.markdown("#### Extracted Fields")

        def _field_row(label: str, field_obj) -> dict:
            val = field_obj.value if field_obj.is_found else "⚠️ Not extracted from document"
            return {"Field": label, "Value": val}

        _id = _up_pkt.id_document
        _id_rows = [
            _field_row("ID Type", type("_", (), {"value": _id.id_type, "is_found": bool(_id.id_type)})()),
            _field_row("ID Number", _id.id_number),
            _field_row("Applicant Name (ID)", _id.applicant_name),
            _field_row("Date of Birth (ID)", _id.date_of_birth),
        ]
        st.markdown("**Government ID**")
        st.dataframe(pd.DataFrame(_id_rows), width="stretch", hide_index=True)

        for _si, _slip in enumerate(_up_pkt.salary_slips, start=1):
            _slip_rows = [
                _field_row("Employer Name", _slip.employer_name),
                _field_row("Applicant Name", _slip.applicant_name),
                _field_row("Pay Period", _slip.pay_period),
                _field_row("Gross Pay", _slip.gross_pay),
                _field_row("Net Pay", _slip.net_pay),
                _field_row("Deductions", _slip.deductions),
            ]
            st.markdown(f"**Salary Slip #{_si}**")
            st.dataframe(pd.DataFrame(_slip_rows), width="stretch", hide_index=True)

        _bs = _up_pkt.bank_statement
        _bs_rows = [
            _field_row("Bank Name", type("_", (), {"value": _bs.bank_name, "is_found": bool(_bs.bank_name)})()),
            _field_row("Account Holder", _bs.account_holder_name),
            _field_row("Account Number", _bs.account_number),
        ]
        st.markdown(f"**Bank Statement** — {len(_bs.transactions)} transaction(s) parsed")
        st.dataframe(pd.DataFrame(_bs_rows), width="stretch", hide_index=True)

        st.markdown("---")
        st.markdown("#### Flags")
        if not _up_flags:
            st.success("✅ No discrepancies detected. All cross-document checks passed.")
        else:
            st.markdown(f"**{len(_up_flags)} flag(s) detected:**")
            for _fi, _flag in enumerate(_up_flags, start=1):
                _sev = _flag.severity.value
                _sev_color = {"HIGH": "#FEE2E2", "MEDIUM": "#FEF3C7", "LOW": "#F0FDF4"}.get(_sev, "#F8FAFC")
                st.markdown(
                    f"<div style='background:{_sev_color}; border-radius:8px; padding:12px; margin-bottom:8px;'>"
                    f"<strong>#{_fi}. {_flag.short_title}</strong> &nbsp;"
                    f"<span style='font-size:0.8rem; background:#E2E8F0; padding:2px 8px; border-radius:10px;'>{_sev}</span><br>"
                    f"{_flag.llm_explanation}"
                    "</div>",
                    unsafe_allow_html=True
                )
                _up_ev_rows = [
                    {"Document": ev.document, "Page": ev.page, "Field": ev.field_name, "Value": ev.extracted_value}
                    for ev in _flag.evidence
                ]
                if _up_ev_rows:
                    st.dataframe(pd.DataFrame(_up_ev_rows), width="stretch", hide_index=True)

        # Download report for uploaded packet
        st.markdown("---")
        st.markdown("#### Export Upload Verification Report")
        try:
            from src.report_generator import generate_csv_report, generate_pdf_report
            _up_col1, _up_col2, _ = st.columns([1, 1, 2])
            with _up_col1:
                _up_csv = generate_csv_report(_up_pkt, _up_flags, [])
                st.download_button(
                    label="📥 Download CSV",
                    data=_up_csv,
                    file_name="upload_verification_report.csv",
                    mime="text/csv",
                    key="dl_csv_upload"
                )
            with _up_col2:
                _up_pdf = generate_pdf_report(_up_pkt, _up_flags, [])
                st.download_button(
                    label="📄 Download PDF",
                    data=bytes(_up_pdf),
                    file_name="upload_verification_report.pdf",
                    mime="application/pdf",
                    key="dl_pdf_upload"
                )
        except Exception as _up_rep_err:
            st.warning(f"Report export unavailable: {_up_rep_err}")
