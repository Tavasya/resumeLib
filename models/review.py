"""
Pydantic models for Resume Review feature
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class SubmitReviewRequest(BaseModel):
    """Request to submit a resume for review

    Supports two submission methods:
    1. Upload a new file (provide filename/file)
    2. Submit existing resume from library (provide existing_resume_id)
    """
    filename: Optional[str] = Field(None, description="Original filename (for new file uploads)")
    existing_resume_id: Optional[str] = Field(None, description="ID of existing resume from user_resumes table")
    review_context: Optional[str] = Field(None, description="Context for review: target roles, concerns, areas to focus on")
    reviewer_type: Literal["team", "big_tech", "startup", "technical"] = Field("team", description="Type of reviewer")
    delivery_speed: Literal["standard", "express"] = Field("standard", description="Delivery speed")
    base_price: Optional[float] = Field(0.00, description="Base price for reviewer type")
    delivery_fee: Optional[float] = Field(0.00, description="Additional fee for express delivery")
    total_price: Optional[float] = Field(0.00, description="Total cost")


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
    user_id: Optional[str] = Field(None, description="User's Clerk ID (only included in admin endpoints)")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Status: 'pending' or 'completed'")
    file_url: str = Field(..., description="URL to submitted file")
    reviewed_file_url: Optional[str] = Field(None, description="URL to reviewed file (if completed)")
    submitted_at: str = Field(..., description="ISO timestamp of submission")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")
    paid: bool = Field(False, description="Whether user has paid to view the review")
    review_context: Optional[str] = Field(None, description="Context for review: target roles, concerns")
    reviewer_type: Optional[str] = Field(None, description="Type of reviewer: team, big_tech, startup, technical")
    delivery_speed: Optional[str] = Field(None, description="Delivery speed: standard, express")
    base_price: Optional[float] = Field(None, description="Base price for reviewer type")
    delivery_fee: Optional[float] = Field(None, description="Additional fee for express delivery")
    total_price: Optional[float] = Field(None, description="Total cost")


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
    paid: bool = Field(False, description="Whether user has paid to view the review")
    stripe_session_id: Optional[str] = Field(None, description="Stripe checkout session ID")
    stripe_payment_intent_id: Optional[str] = Field(None, description="Stripe payment intent ID")
    review_context: Optional[str] = Field(None, description="Context for review: target roles, concerns")
    reviewer_type: Optional[str] = Field(None, description="Type of reviewer: team, big_tech, startup, technical")
    delivery_speed: Optional[str] = Field(None, description="Delivery speed: standard, express")
    base_price: Optional[float] = Field(None, description="Base price for reviewer type")
    delivery_fee: Optional[float] = Field(None, description="Additional fee for express delivery")
    total_price: Optional[float] = Field(None, description="Total cost")


class GetSubmissionResponse(BaseModel):
    """Response from get submission detail endpoint"""
    success: bool
    submission: Optional[SubmissionDetail] = None
    error: Optional[str] = None


class UpdateReviewedFileRequest(BaseModel):
    """Request to upload reviewed file (admin only)"""
    notes: Optional[str] = Field(None, description="Reviewer notes/feedback")


class CompleteReviewRequest(BaseModel):
    """Request to complete a review (admin only)"""
    notes: Optional[str] = Field("", description="Reviewer notes/feedback")


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


# Annotation Models
class AnnotationPosition(BaseModel):
    """Position data for an annotation"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    width: float = Field(..., description="Width of annotation")
    height: float = Field(..., description="Height of annotation")


class AnnotationContent(BaseModel):
    """Content data for an annotation"""
    selectedText: Optional[str] = Field(None, description="Text that was selected (for highlights)")
    comment: Optional[str] = Field(None, description="Reviewer's note/comment")


class CreateAnnotationRequest(BaseModel):
    """Request to create an annotation"""
    submission_id: str = Field(..., description="UUID of the submission")
    annotation_type: str = Field(..., description="Type: 'highlight', 'area', or 'drawing'")
    page_number: int = Field(..., description="Page number (0-indexed)")
    position: AnnotationPosition = Field(..., description="Position data")
    content: AnnotationContent = Field(..., description="Content data")


class AnnotationDetail(BaseModel):
    """Details of a single annotation"""
    id: str = Field(..., description="Annotation UUID")
    submission_id: str = Field(..., description="Submission UUID")
    annotation_type: str = Field(..., description="Type: 'highlight', 'area', or 'drawing'")
    page_number: int = Field(..., description="Page number (0-indexed)")
    position: dict = Field(..., description="Position data")
    content: dict = Field(..., description="Content data")
    created_at: str = Field(..., description="ISO timestamp of creation")


class CreateAnnotationResponse(BaseModel):
    """Response from create annotation endpoint"""
    success: bool
    annotation: Optional[AnnotationDetail] = None
    error: Optional[str] = None


class GetAnnotationsResponse(BaseModel):
    """Response from get annotations endpoint"""
    success: bool
    annotations: List[AnnotationDetail] = Field(default_factory=list)
    error: Optional[str] = None


class DeleteAnnotationResponse(BaseModel):
    """Response from delete annotation endpoint"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class CreateReviewCheckoutResponse(BaseModel):
    """Response from create review checkout endpoint"""
    success: bool
    checkout_url: Optional[str] = Field(None, description="Stripe checkout URL")
    session_id: Optional[str] = Field(None, description="Stripe session ID")
    error: Optional[str] = None
