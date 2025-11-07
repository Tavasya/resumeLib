"""
Pydantic models for User Resumes
"""
from typing import Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response for resume upload"""
    success: bool
    message: str
    resume_id: Optional[str] = None
    file_url: Optional[str] = None
