# Two-minute demo script

Keep the walkthrough focused on how the tool presents evidence for human review. All packets and the override rationale below are synthetic demo material.

## Walkthrough

1. **Open a clean packet.** In the sidebar, select `APP_001`. Point out that the packet has no discrepancy flags; the tool reports its checks rather than making an underwriting decision.
2. **Show a mismatch and its evidence.** Select `APP_031` and open **Discrepancy Flags & Triage**. Show the name-mismatch flag and its evidence table, including the cited document, page, line, and extracted value. Explain that the flag identifies a discrepancy for review; it is not a fraud conclusion.
3. **Demonstrate an override.** Expand **Override Flag** for a flag, enter a written rationale, and confirm the override. For example, use: “Synthetic demo rationale: supporting payroll evidence reviewed for this walkthrough.” Note that an override records the underwriter's action; it does not change the verifier's automated result.
4. **Inspect the audit trail.** Open **Append-Only Audit Log**. Show the verification run and the underwriter action with its rationale.
5. **Show evaluation results.** Open **Evaluation Metrics**. Point to the held-out split and the separately reported hard stress-test results in `metrics.md`.
6. **Show document upload.** Open **Upload Documents** and point out the ID, salary-slip, and bank-statement PDF inputs. If using real documents in a live environment, stop here: this demo is for synthetic data, and the upload path does not write a system run to the audit log.

## Close

Reinforce that deterministic checks surface inconsistencies with evidence, the explanation layer only helps describe flags, and a human underwriter remains responsible for review and decisions.
