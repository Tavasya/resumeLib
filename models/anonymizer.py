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


class SaveAnonymizedRequest(BaseModel):
    """Request to save anonymization preferences"""
    file_id: str
    detections: List[PIIDetection] = Field(..., description="List of PII detections with blur state")


class SaveAnonymizedResponse(BaseModel):
    """Response from save anonymized endpoint"""
    success: bool
    message: Optional[str] = None
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
