"""Shared public Case value sets.

These aliases mirror existing database and API values only.  They do not add
new lifecycle values or change the stored schema.
"""

from typing import Literal, TypeAlias


CaseRisk: TypeAlias = Literal["NORMAL", "LOW", "HIGH"]
CaseMode: TypeAlias = Literal["PREVENT", "RECOVERY", "CLOSED"]
CaseStatus: TypeAlias = Literal["NEW", "TRIAGE", "VERIFYING", "IN_PROGRESS", "CLOSED"]
InitialCaseMode: TypeAlias = Literal["PREVENT"]
InitialCaseStatus: TypeAlias = Literal["TRIAGE"]
AnalyzeDisposition: TypeAlias = Literal["CASE_CREATED", "NO_CASE", "FAILED"]
PublicAnalyzeErrorCode: TypeAlias = Literal[
    "INVALID_INPUT", "AI_ANALYSIS_FAILED", "CASE_SAVE_FAILED",
    "OPENAI_QUOTA_EXHAUSTED", "OPENAI_AUTHENTICATION_FAILED",
]
