"""
Pydantic models for Resume Builder
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CreateBuilderResumeRequest(BaseModel):
    """Request to create new builder resume"""
    title: Optional[str] = "Untitled Resume"


class CreateBuilderResumeResponse(BaseModel):
    """Response for creating builder resume"""
    success: bool
    resume_id: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SaveBuilderContentRequest(BaseModel):
    """Request to save builder content"""
    editor_data: Dict[str, Any] = Field(..., description="Editor.js output data with blocks")
    title: Optional[str] = "Untitled Resume"


class SaveBuilderContentResponse(BaseModel):
    """Response for saving builder content"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class GeneratePDFRequest(BaseModel):
    """Request to generate PDF from HTML"""
    html: str = Field(..., description="Complete HTML document with styling")


class GeneratePDFResponse(BaseModel):
    """Response for PDF generation"""
    success: bool
    file_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class GetBuilderContentResponse(BaseModel):
    """Response for getting builder content"""
    success: bool
    resume_id: Optional[str] = None
    title: Optional[str] = None
    editor_data: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    error: Optional[str] = None


class DeleteBuilderResumeResponse(BaseModel):
    """Response for deleting builder resume"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
