"""
Review API routes
Handles resume submission for manual review
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Form

from api.auth import get_user_id, verify_clerk_token
from services.review_service import review_service
from services.stripe_service import stripe_service
from models.review import (
    SubmitReviewResponse,
    ListReviewSubmissionsResponse,
    GetSubmissionResponse,
    DeleteSubmissionResponse,
    ReviewSubmissionSummary,
    SubmissionDetail,
    CompleteSubmissionResponse,
    CompleteReviewRequest,
    CreateAnnotationRequest,
    CreateAnnotationResponse,
    GetAnnotationsResponse,
    DeleteAnnotationResponse,
    AnnotationDetail,
    CreateReviewCheckoutResponse
)

router = APIRouter()


@router.post("/submit", response_model=SubmitReviewResponse)
async def submit_resume(
    file: UploadFile = File(...),
    review_context: Optional[str] = Form(None),
    reviewer_type: str = Form("team"),
    delivery_speed: str = Form("standard"),
    base_price: float = Form(0.00),
    delivery_fee: float = Form(0.00),
    total_price: float = Form(0.00),
    user_id: str = Depends(get_user_id)
):
    """
    Submit a resume for manual review

    Args:
        file: PDF file to submit
        review_context: Context for review (target roles, concerns, areas to focus)
        reviewer_type: Type of reviewer (team, big_tech, startup, technical)
        delivery_speed: Delivery speed (standard, express)
        base_price: Base price for reviewer type
        delivery_fee: Additional fee for express delivery
        total_price: Total cost
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        SubmitReviewResponse with submission ID and file URL
    """
    try:
        # Validate PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are supported")

        # Validate reviewer_type
        if reviewer_type not in ["team", "big_tech", "startup", "technical"]:
            raise HTTPException(400, "Invalid reviewer_type")

        # Validate delivery_speed
        if delivery_speed not in ["standard", "express"]:
            raise HTTPException(400, "Invalid delivery_speed")

        # Read file content
        file_content = await file.read()

        print(f"📄 Submitting resume for review:")
        print(f"   Filename: {file.filename}")
        print(f"   File size: {len(file_content)} bytes")
        print(f"   User ID: {user_id}")
        print(f"   Reviewer Type: {reviewer_type}")
        print(f"   Delivery Speed: {delivery_speed}")
        print(f"   Total Price: ${total_price}")

        # Submit resume
        result = review_service.submit_resume(
            user_id=user_id,
            filename=file.filename,
            file_content=file_content,
            review_context=review_context,
            reviewer_type=reviewer_type,
            delivery_speed=delivery_speed,
            base_price=base_price,
            delivery_fee=delivery_fee,
            total_price=total_price
        )

        if not result["success"]:
            print(f"❌ Submission failed: {result.get('error')}")
            raise HTTPException(500, result.get("error", "Submission failed"))

        print(f"✅ Submission successful: {result['submission_id']}")

        return SubmitReviewResponse(
            success=True,
            submission_id=result["submission_id"],
            file_url=result["file_url"],
            message="Resume submitted successfully for review"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(500, f"Failed to submit resume: {str(e)}")


@router.get("/submissions", response_model=ListReviewSubmissionsResponse)
async def list_submissions(
    user_id: str = Depends(get_user_id)
):
    """
    List all review submissions for the authenticated user

    Args:
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        ListReviewSubmissionsResponse with list of submissions
    """
    try:
        result = review_service.list_submissions(user_id)

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to list submissions"))

        # Convert to Pydantic models
        submissions = [
            ReviewSubmissionSummary(**submission)
            for submission in result["submissions"]
        ]

        return ListReviewSubmissionsResponse(
            success=True,
            submissions=submissions
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error listing submissions: {e}")
        raise HTTPException(500, f"Failed to list submissions: {str(e)}")


@router.get("/admin/submissions", response_model=ListReviewSubmissionsResponse)
async def list_all_submissions(
    user_id: str = Depends(get_user_id)
):
    """
    Admin endpoint: List all review submissions from all users

    Only accessible by admin user: 2bcabe8f-73c9-4f14-8fd0-a0d2310443a0

    Args:
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        ListReviewSubmissionsResponse with list of all submissions
    """
    # Check if user is admin
    ADMIN_USER_IDS = [
        "user_34xiVcXmTBuDQJIJtqOpl5i2K9W",
        "user_34N6arMDMuOBtMo1OivYVsc1VuP"
    ]
    print(f"🔐 Admin endpoint accessed by user_id: {user_id}")
    print(f"🔑 Expected admin user_ids: {ADMIN_USER_IDS}")
    print(f"✅ Match: {user_id in ADMIN_USER_IDS}")

    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(403, "Access denied. Admin privileges required.")

    try:
        result = review_service.list_all_submissions()

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to list submissions"))

        # Convert to Pydantic models
        submissions = [
            ReviewSubmissionSummary(**submission)
            for submission in result["submissions"]
        ]

        return ListReviewSubmissionsResponse(
            success=True,
            submissions=submissions
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error listing submissions: {e}")
        raise HTTPException(500, f"Failed to list submissions: {str(e)}")


@router.get("/submissions/{submission_id}", response_model=GetSubmissionResponse)
async def get_submission(
    submission_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get details of a single submission

    Args:
        submission_id: UUID of the submission
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GetSubmissionResponse with submission details
    """
    try:
        result = review_service.get_submission(submission_id, user_id)

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, "Submission not found")
            raise HTTPException(500, result.get("error", "Failed to get submission"))

        submission = SubmissionDetail(**result["submission"])

        return GetSubmissionResponse(
            success=True,
            submission=submission
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting submission: {e}")
        raise HTTPException(500, f"Failed to get submission: {str(e)}")


@router.get("/admin/submissions/{submission_id}", response_model=GetSubmissionResponse)
async def get_submission_admin(
    submission_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Admin endpoint: Get details of any submission without ownership check

    Only accessible by admin users

    Args:
        submission_id: UUID of the submission
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GetSubmissionResponse with submission details
    """
    # Check if user is admin
    ADMIN_USER_IDS = [
        "user_34xiVcXmTBuDQJIJtqOpl5i2K9W",
        "user_34N6arMDMuOBtMo1OivYVsc1VuP"
    ]

    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(403, "Access denied. Admin privileges required.")

    try:
        result = review_service.get_submission_admin(submission_id)

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, "Submission not found")
            raise HTTPException(500, result.get("error", "Failed to get submission"))

        submission = SubmissionDetail(**result["submission"])

        return GetSubmissionResponse(
            success=True,
            submission=submission
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting submission: {e}")
        raise HTTPException(500, f"Failed to get submission: {str(e)}")


@router.post("/admin/complete/{submission_id}", response_model=CompleteSubmissionResponse)
async def complete_submission(
    submission_id: str,
    request: CompleteReviewRequest
):
    """
    Admin endpoint: Generate reviewed PDF from annotations and mark submission as completed

    This endpoint generates the reviewed PDF by:
    1. Fetching all annotations for the submission
    2. Downloading the original PDF
    3. Burning annotations (highlights + comments) into the PDF
    4. Uploading the generated PDF with watermark

    No authentication required - this is for internal admin use only.
    You can add auth later if needed.

    Args:
        submission_id: UUID of the submission to complete
        request: CompleteReviewRequest with optional notes

    Returns:
        CompleteSubmissionResponse with success status and reviewed file URL
    """
    try:
        print(f"📤 Completing submission:")
        print(f"   Submission ID: {submission_id}")
        print(f"   Notes: {request.notes or 'None'}")

        # Complete the submission (generates PDF from annotations)
        result = review_service.complete_submission(
            submission_id=submission_id,
            notes=request.notes
        )

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, "Submission not found")
            raise HTTPException(500, result.get("error", "Failed to complete submission"))

        print(f"✅ Submission completed successfully")

        return CompleteSubmissionResponse(
            success=True,
            reviewed_file_url=result["reviewed_file_url"],
            message="Submission completed and reviewed file generated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error completing submission: {e}")
        raise HTTPException(500, f"Failed to complete submission: {str(e)}")


@router.delete("/submissions/{submission_id}", response_model=DeleteSubmissionResponse)
async def delete_submission(
    submission_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Delete a submission and its files

    Args:
        submission_id: UUID of the submission
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        DeleteSubmissionResponse with success status
    """
    try:
        result = review_service.delete_submission(submission_id, user_id)

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, "Submission not found")
            raise HTTPException(500, result.get("error", "Failed to delete submission"))

        return DeleteSubmissionResponse(
            success=True,
            message="Submission deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting submission: {e}")
        raise HTTPException(500, f"Failed to delete submission: {str(e)}")


# Annotation Endpoints

@router.post("/admin/annotations", response_model=CreateAnnotationResponse)
async def create_annotation(
    request: CreateAnnotationRequest
):
    """
    Admin endpoint: Create an annotation for a submission

    No authentication required - this is for internal admin use only.
    You can add auth later if needed.

    Args:
        request: CreateAnnotationRequest with annotation details

    Returns:
        CreateAnnotationResponse with created annotation
    """
    try:
        print(f"📝 Creating annotation:")
        print(f"   Submission ID: {request.submission_id}")
        print(f"   Type: {request.annotation_type}")
        print(f"   Page: {request.page_number}")

        # Create the annotation
        result = review_service.create_annotation(
            submission_id=request.submission_id,
            annotation_type=request.annotation_type,
            page_number=request.page_number,
            position=request.position.model_dump(),
            content=request.content.model_dump()
        )

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, result.get("error", "Submission not found"))
            raise HTTPException(400, result.get("error", "Failed to create annotation"))

        print(f"✅ Annotation created successfully: {result['annotation']['id']}")

        annotation = AnnotationDetail(**result["annotation"])

        return CreateAnnotationResponse(
            success=True,
            annotation=annotation
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating annotation: {e}")
        raise HTTPException(500, f"Failed to create annotation: {str(e)}")


@router.get("/submissions/{submission_id}/annotations", response_model=GetAnnotationsResponse)
async def get_annotations(
    submission_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get all annotations for a submission

    Args:
        submission_id: UUID of the submission
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GetAnnotationsResponse with list of annotations
    """
    try:
        # Get annotations (with user ownership check)
        result = review_service.get_annotations(submission_id, user_id)

        if not result["success"]:
            if "not found" in result.get("error", "").lower() or "access denied" in result.get("error", "").lower():
                raise HTTPException(404, result.get("error", "Submission not found"))
            raise HTTPException(500, result.get("error", "Failed to get annotations"))

        # Convert to Pydantic models
        annotations = [
            AnnotationDetail(**annotation)
            for annotation in result["annotations"]
        ]

        return GetAnnotationsResponse(
            success=True,
            annotations=annotations
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting annotations: {e}")
        raise HTTPException(500, f"Failed to get annotations: {str(e)}")


@router.get("/admin/submissions/{submission_id}/annotations", response_model=GetAnnotationsResponse)
async def get_annotations_admin(
    submission_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Admin endpoint: Get all annotations for any submission without ownership check

    Only accessible by admin users

    Args:
        submission_id: UUID of the submission
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GetAnnotationsResponse with list of annotations
    """
    # Check if user is admin
    ADMIN_USER_IDS = [
        "user_34xiVcXmTBuDQJIJtqOpl5i2K9W",
        "user_34N6arMDMuOBtMo1OivYVsc1VuP"
    ]

    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(403, "Access denied. Admin privileges required.")

    try:
        # Get annotations (without ownership check)
        result = review_service.get_annotations(submission_id, user_id=None)

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to get annotations"))

        # Convert to Pydantic models
        annotations = [
            AnnotationDetail(**annotation)
            for annotation in result["annotations"]
        ]

        return GetAnnotationsResponse(
            success=True,
            annotations=annotations
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting annotations: {e}")
        raise HTTPException(500, f"Failed to get annotations: {str(e)}")


@router.delete("/admin/annotations/{annotation_id}", response_model=DeleteAnnotationResponse)
async def delete_annotation(
    annotation_id: str
):
    """
    Admin endpoint: Delete an annotation

    No authentication required - this is for internal admin use only.
    You can add auth later if needed.

    Args:
        annotation_id: UUID of the annotation to delete

    Returns:
        DeleteAnnotationResponse with success status
    """
    try:
        print(f"🗑️  Deleting annotation: {annotation_id}")

        result = review_service.delete_annotation(annotation_id)

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to delete annotation"))

        print(f"✅ Annotation deleted successfully")

        return DeleteAnnotationResponse(
            success=True,
            message="Annotation deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting annotation: {e}")
        raise HTTPException(500, f"Failed to delete annotation: {str(e)}")


# Payment Endpoints

@router.post("/create-checkout/{submission_id}", response_model=CreateReviewCheckoutResponse)
async def create_review_checkout(
    submission_id: str,
    request: Request
):
    """
    Create a Stripe checkout session for a resume review payment

    Supports two payment flows:
    1. Upfront payment: User pays before review is completed (status = pending)
    2. Post-review payment: User pays after review is completed (status = completed)

    Requires authentication. User must own the submission.

    Args:
        submission_id: UUID of the submission to pay for
        request: FastAPI Request object for authentication

    Returns:
        CreateReviewCheckoutResponse with checkout URL and session ID
    """
    try:
        # Verify user authentication
        user = await verify_clerk_token(request)
        user_id = user.get("id")
        email = user.get("email_addresses", [{}])[0].get("email_address")

        # Verify user owns this submission
        submission = review_service.get_submission(submission_id, user_id)

        if not submission["success"]:
            raise HTTPException(404, "Submission not found or access denied")

        submission_data = submission["submission"]

        # Allow payment for both pending (upfront) and completed (post-review) submissions
        # Just verify not already paid
        if submission_data.get("paid", False):
            raise HTTPException(400, "Review has already been paid for")

        # Create Stripe checkout session
        result = stripe_service.create_review_checkout_session(
            submission_id=submission_id,
            clerk_user_id=user_id,
            email=email
        )

        return CreateReviewCheckoutResponse(
            success=True,
            checkout_url=result["checkout_url"],
            session_id=result["session_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create checkout session: {str(e)}")
