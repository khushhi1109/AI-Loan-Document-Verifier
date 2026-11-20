"""
Configuration settings and deterministic thresholds for AI Loan Document Verifier.
All threshold tuning parameters are centralized here.
"""

import os
from pydantic import BaseModel

class VerifierConfig(BaseModel):
    # Name Matching Configuration
    # Name similarity bands (0 - 100)
    NAME_SIMILARITY_WARNING_THRESHOLD: float = 75.0
    NAME_SIMILARITY_VERY_HIGH_THRESHOLD: float = 92.0
    NAME_CORROBORATION_MINIMUM_SIMILARITY: float = 55.0
    NAME_PHONETIC_MINIMUM_BASE_SIMILARITY: float = 55.0
    NAME_PHONETIC_SIMILARITY_THRESHOLD: float = 85.0
    
    # Date of Birth matching
    DOB_MATCH_STRICT: bool = True
    
    # Salary vs Bank Credit Matching
    # Percentage tolerance (e.g. 2.0 = +/- 2.0%)
    SALARY_TOLERANCE_PERCENT: float = 2.0
    # Absolute tolerance in INR for small rounding differences
    SALARY_TOLERANCE_ABSOLUTE_INR: float = 250.0
    # Window in days after pay-period end (or month start) to find credit
    # Allows salary credited late (e.g., up to 18 days into next month or 5 days before)
    SALARY_DATE_WINDOW_PAST_DAYS: int = 5
    SALARY_DATE_WINDOW_FUTURE_DAYS: int = 20
    
    # Employer Matching
    EMPLOYER_SIMILARITY_THRESHOLD: float = 60.0
    
    # Payslip Arithmetic
    # Maximum acceptable discrepancy between (Gross - Deductions) and Net Pay
    ARITHMETIC_TOLERANCE_INR: float = 2.0
    
    # Paths & Database
    AUDIT_DB_PATH: str = os.getenv("AUDIT_DB_PATH", "audit_log.db")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    PACKETS_DIR: str = os.path.join(DATA_DIR, "packets")
    GROUND_TRUTH_PATH: str = os.path.join(DATA_DIR, "ground_truth.json")
    
    # LLM Settings
    LLM_MODE: str = os.getenv("LLM_MODE", "MOCK")  # 'MOCK' or 'GEMINI'
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Global singleton configuration
CONFIG = VerifierConfig()
