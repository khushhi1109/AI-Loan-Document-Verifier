"""
Data models and schemas for AI Loan Document Verifier.
All documents, extracted fields, citations, and mismatch flags are strictly typed.
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class SourceLocation(BaseModel):
    document: str
    page: int = 1
    line: int = 1
    raw_text: str = ""

class ExtractedField(BaseModel):
    field_name: str
    value: Any  # "not_found" if unreadable/missing
    location: Optional[SourceLocation] = None
    confidence: float = 1.0

    @property
    def is_found(self) -> bool:
        return self.value is not None and str(self.value).strip().lower() != "not_found"

class IDDocumentData(BaseModel):
    document_name: str
    id_type: str  # "PAN" or "AADHAAR"
    id_number: ExtractedField
    applicant_name: ExtractedField
    date_of_birth: ExtractedField

class SalarySlipData(BaseModel):
    document_name: str
    slip_id: ExtractedField
    applicant_name: ExtractedField
    applicant_id_number: Optional[ExtractedField] = None
    employer_name: ExtractedField
    date_of_birth: Optional[ExtractedField] = None
    pay_period: ExtractedField  # YYYY-MM
    pay_month_name: ExtractedField  # e.g., "January 2024"
    gross_pay: ExtractedField
    deductions: ExtractedField
    net_pay: ExtractedField
    id_number: Optional[ExtractedField] = None

class BankTransaction(BaseModel):
    date: str  # YYYY-MM-DD
    description: str
    credit_amount: float = 0.0
    debit_amount: float = 0.0
    balance: float = 0.0
    is_salary: bool = False
    location: SourceLocation

class BankStatementData(BaseModel):
    document_name: str
    bank_name: ExtractedField
    account_holder: ExtractedField
    account_number: ExtractedField
    applicant_id_number: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    id_number: Optional[ExtractedField] = None
    transactions: List[BankTransaction] = Field(default_factory=list)

class ApplicantPacketData(BaseModel):
    applicant_id: str
    id_document: IDDocumentData
    salary_slips: List[SalarySlipData] = Field(default_factory=list)
    bank_statement: BankStatementData

class EvidenceItem(BaseModel):
    document: str
    page: int
    line: int
    field_name: str
    extracted_value: str
    raw_snippet: Optional[str] = None

class MismatchFlag(BaseModel):
    flag_id: str
    check_name: str
    severity: SeverityLevel
    short_title: str
    llm_explanation: str
    evidence: List[EvidenceItem]
    status: str = "PENDING"  # "PENDING", "ACCEPTED", "OVERRIDDEN"
    override_reason: Optional[str] = None
    underwriter_id: Optional[str] = None
    timestamp: Optional[str] = None

class GroundTruthMismatch(BaseModel):
    type: str  # e.g. "name_mismatch", "dob_mismatch", "salary_gap", "missing_month", "employer_mismatch", "edited_duplicate_slip"
    description: str
    target_document: Optional[str] = None
    planted_value: Optional[str] = None

class GroundTruthPacket(BaseModel):
    applicant_id: str
    is_clean: bool
    is_hard_negative: bool = False
    hard_negative_type: Optional[str] = None  # e.g., "initials_vs_fullname", "mohammed_spelling", "late_salary", "job_change", "swapped_name_order"
    planted_mismatches: List[GroundTruthMismatch] = Field(default_factory=list)
    expected_fields: Optional[Dict[str, Any]] = None
