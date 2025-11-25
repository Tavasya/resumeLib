"""
Pydantic models for ATS Checker feature
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ATSSuggestion(BaseModel):
    """Single ATS suggestion"""
    category: Literal["critical", "warning", "success", "info"] = Field(..., description="Suggestion severity")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Suggestion details")


class ATSAnalyzeRequest(BaseModel):
    """Request to analyze resume for ATS compatibility"""
    existing_submission_id: Optional[str] = Field(None, description="ID of existing resume submission (from review_submissions)")
    existing_resume_id: Optional[str] = Field(None, description="ID of existing resume (from user_resumes - supports builder resumes)")
    job_description: Optional[str] = Field(None, description="Job description to compare against")


class ATSAnalyzeResponse(BaseModel):
    """Response from ATS analysis"""
    success: bool
    score: Optional[int] = Field(None, description="ATS compatibility score (0-100)")
    suggestions: List[ATSSuggestion] = Field(default_factory=list)
    error: Optional[str] = None
