"""
Pydantic models for Anonymizer data
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for PII detection"""
    x: float = Field(..., description="X coordinate (left)")
    y: float = Field(..., description="Y coordinate (top)")
    width: float = Field(..., description="Width of bounding box")
    height: float = Field(..., description="Height of bounding box")


class TextStyle(BaseModel):
    """Font and styling information for detected text"""
    font_name: str = Field(..., description="Font family name (e.g., 'Helvetica', 'Calibri')")
    font_size: float = Field(..., description="Font size in points")
    color: int = Field(..., description="Text color as integer (RGB encoded)")
    flags: int = Field(..., description="Font flags (bold, italic, etc.)")


class PIIDetection(BaseModel):
    """Single PII detection with location"""
    id: str = Field(..., description="Unique identifier for this detection (UUID)")
    type: str = Field(..., description="Type: email, phone, name, company, school, linkedin, website, github, address")
    text: str = Field(..., description="The actual text detected")
    page: int = Field(..., description="PDF page number (0-indexed)")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 - 1.0)")
    style: TextStyle = Field(..., description="Original text styling information")


class DetectPIIResponse(BaseModel):
    """Response from PII detection endpoint"""
    success: bool
    file_id: str = Field(..., description="UUID for tracking this file")
    original_url: str = Field(..., description="Supabase storage URL for original PDF")
    detections: List[PIIDetection] = Field(default_factory=list)
    total_pages: int
    error: Optional[str] = None


class ReplacementItem(BaseModel):
    """Single text replacement with location"""
    page: int = Field(..., description="PDF page number (0-indexed)")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    original_text: str = Field(..., description="Original text to replace")
    replacement_text: str = Field(..., description="New text to insert")
    type: str = Field(..., description="Type of PII: email, phone, name, company, school, etc.")
    style: TextStyle = Field(..., description="Original text styling to preserve")


class GenerateAnonymizedPDFRequest(BaseModel):
    """Request to generate anonymized PDF with text replacements"""
    file_id: str = Field(..., description="UUID of the original file")
    replacements: List[ReplacementItem] = Field(..., description="List of text replacements to apply")


class GenerateAnonymizedPDFResponse(BaseModel):
    """Response from generate anonymized PDF endpoint"""
    success: bool
    anonymized_url: Optional[str] = Field(None, description="Download URL for anonymized PDF")
    original_url: Optional[str] = Field(None, description="Original PDF URL")
    error: Optional[str] = None


# Session Management Models

class ManualBlur(BaseModel):
    """Manual blur region added by user"""
    page: int = Field(..., description="PDF page number (0-indexed)")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    id: str = Field(..., description="Unique identifier for this manual blur")


class SessionPIIDetection(BaseModel):
    """PII detection with blur and replacement state"""
    id: str = Field(..., description="Unique identifier for this detection (UUID)")
    type: str = Field(..., description="Type: email, phone, name, company, school, linkedin, website, github, address")
    text: str = Field(..., description="The actual text detected")
    page: int = Field(..., description="PDF page number (0-indexed)")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    blurred: bool = Field(default=False, description="Whether this detection should be blurred")
    replacement_text: Optional[str] = Field(None, description="Replacement text if user wants to replace instead of blur")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 - 1.0)")
    style: TextStyle = Field(..., description="Original text styling information")


class SaveSessionRequest(BaseModel):
    """Request to save/update anonymizer session"""
    file_id: str = Field(..., description="UUID of the uploaded file")
    filename: str = Field(..., description="Original filename for display")
    detections: List[SessionPIIDetection] = Field(..., description="All PII detections with their blur/replacement state")
    manual_blurs: List[ManualBlur] = Field(default_factory=list, description="User-added manual blur regions")
    num_pages: int = Field(..., description="Total number of pages in PDF")


class SaveSessionResponse(BaseModel):
    """Response from save session endpoint"""
    success: bool
    session_id: Optional[str] = Field(None, description="Database session ID (UUID)")
    message: Optional[str] = None
    error: Optional[str] = None


class SessionSummary(BaseModel):
    """Summary of an anonymizer session for list view"""
    session_id: str = Field(..., description="Database session ID (UUID)")
    file_id: str = Field(..., description="File UUID")
    filename: str = Field(..., description="Original filename")
    original_url: str = Field(..., description="URL to original PDF")
    num_pages: int = Field(..., description="Number of pages in PDF")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")


class ListSessionsResponse(BaseModel):
    """Response from list sessions endpoint"""
    success: bool
    sessions: List[SessionSummary] = Field(default_factory=list)
    error: Optional[str] = None


class SessionDetail(BaseModel):
    """Full session data including all detections"""
    session_id: str = Field(..., description="Database session ID (UUID)")
    file_id: str = Field(..., description="File UUID")
    filename: str = Field(..., description="Original filename")
    original_url: str = Field(..., description="URL to original PDF")
    detections: List[SessionPIIDetection] = Field(..., description="All PII detections with states")
    manual_blurs: List[ManualBlur] = Field(..., description="Manual blur regions")
    num_pages: int = Field(..., description="Number of pages in PDF")


class LoadSessionResponse(BaseModel):
    """Response from load session endpoint"""
    success: bool
    session: Optional[SessionDetail] = None
    error: Optional[str] = None


# Share Link Models

class CreateShareLinkRequest(BaseModel):
    """Request to create a shareable link"""
    session_id: str = Field(..., description="UUID of the session to share")
    expires_in_days: Optional[int] = Field(None, description="Number of days until link expires (optional)")
    password: Optional[str] = Field(None, description="Optional password to protect the link")


class CreateShareLinkResponse(BaseModel):
    """Response from create share link endpoint"""
    success: bool
    share_token: Optional[str] = Field(None, description="UUID token for sharing")
    share_url: Optional[str] = Field(None, description="Full URL to share")
    expires_at: Optional[str] = Field(None, description="ISO timestamp when link expires")
    error: Optional[str] = None


class SharedSessionResponse(BaseModel):
    """Response from public share endpoint"""
    success: bool
    session: Optional[SessionDetail] = Field(None, description="Session data in read-only mode")
    error: Optional[str] = None
