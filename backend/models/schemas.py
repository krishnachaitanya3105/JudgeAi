"""
JudgeAI Pydantic Schemas
──────────────────────────────────────────────────
Request/response models for API validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────

class ExtractRequest(BaseModel):
    """Request body for POST /extract-actions."""
    pdf_url: str = Field(..., description="Public URL of the uploaded PDF")


class UploadResponse(BaseModel):
    """Response from POST /upload-pdf."""
    message: str
    case_number: str
    pdf_url: str
    metadata: dict


# ── Data Schemas ─────────────────────────────────

class CaseMetadata(BaseModel):
    """Schema for the `cases` table."""
    case_number: str
    pdf_url: str
    uploaded_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractedAction(BaseModel):
    """Schema for the `extracted_actions` table."""
    case_number: Optional[str] = None
    judgment_date: Optional[str] = None
    department: Optional[str] = None
    deadline: Optional[str] = None
    directive: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_sentence: Optional[str] = None
    pdf_url: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LLMExtractionResult(BaseModel):
    """Schema for the LLM extraction output."""
    case_number: Optional[str] = None
    judgment_date: Optional[str] = None
    department: Optional[str] = None
    deadline: Optional[str] = None
    directive: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_sentence: Optional[str] = None
