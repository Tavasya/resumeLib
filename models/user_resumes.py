"""
Pydantic models for User Resumes
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response for resume upload"""
    success: bool
    message: str
    resume_id: Optional[str] = None
    file_url: Optional[str] = None


class UserResumeItem(BaseModel):
    """Single user resume item"""
    id: str
    filename: str
    file_url: str
    file_type: str
    created_at: datetime
    updated_at: datetime


class ListResumesResponse(BaseModel):
    """Response for listing user resumes"""
    success: bool
    resumes: List[UserResumeItem]
