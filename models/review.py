"""
Pydantic models for Resume Review feature
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SubmitReviewRequest(BaseModel):
    """Request to submit a resume for review"""
    filename: str = Field(..., description="Original filename")


class SubmitReviewResponse(BaseModel):
    """Response from submit review endpoint"""
    success: bool
    submission_id: Optional[str] = Field(None, description="UUID of created submission")
    file_url: Optional[str] = Field(None, description="URL to submitted file")
    message: Optional[str] = None
    error: Optional[str] = None


class ReviewSubmissionSummary(BaseModel):
    """Summary of a review submission for list view"""
    id: str = Field(..., description="Submission UUID")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Status: 'pending' or 'completed'")
    file_url: str = Field(..., description="URL to submitted file")
    reviewed_file_url: Optional[str] = Field(None, description="URL to reviewed file (if completed)")
    submitted_at: str = Field(..., description="ISO timestamp of submission")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")


class ListReviewSubmissionsResponse(BaseModel):
    """Response from list submissions endpoint"""
    success: bool
    submissions: List[ReviewSubmissionSummary] = Field(default_factory=list)
    error: Optional[str] = None


class SubmissionDetail(BaseModel):
    """Full details of a single submission"""
    id: str = Field(..., description="Submission UUID")
    user_id: str = Field(..., description="User's Clerk ID")
    filename: str = Field(..., description="Original filename")
    file_url: str = Field(..., description="URL to submitted file")
    storage_path: str = Field(..., description="Storage path in bucket")
    status: str = Field(..., description="Status: 'pending' or 'completed'")
    reviewed_file_url: Optional[str] = Field(None, description="URL to reviewed file")
    notes: Optional[str] = Field(None, description="Reviewer notes")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    submitted_at: str = Field(..., description="ISO timestamp of submission")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")


class GetSubmissionResponse(BaseModel):
    """Response from get submission detail endpoint"""
    success: bool
    submission: Optional[SubmissionDetail] = None
    error: Optional[str] = None


class UpdateReviewedFileRequest(BaseModel):
    """Request to upload reviewed file (admin only)"""
    notes: Optional[str] = Field(None, description="Reviewer notes/feedback")


class UpdateReviewedFileResponse(BaseModel):
    """Response from update reviewed file endpoint"""
    success: bool
    reviewed_file_url: Optional[str] = Field(None, description="URL to uploaded reviewed file")
    message: Optional[str] = None
    error: Optional[str] = None


class CompleteSubmissionResponse(BaseModel):
    """Response from admin complete submission endpoint"""
    success: bool
    reviewed_file_url: Optional[str] = Field(None, description="URL to uploaded reviewed file")
    message: Optional[str] = None
    error: Optional[str] = None


class DeleteSubmissionResponse(BaseModel):
    """Response from delete submission endpoint"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
