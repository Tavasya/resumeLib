"""
Review API routes
Handles resume submission for manual review
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from api.auth import get_user_id
from services.review_service import review_service
from models.review import (
    SubmitReviewResponse,
    ListReviewSubmissionsResponse,
    GetSubmissionResponse,
    DeleteSubmissionResponse,
    ReviewSubmissionSummary,
    SubmissionDetail,
    CompleteSubmissionResponse
)

router = APIRouter()


@router.post("/submit", response_model=SubmitReviewResponse)
async def submit_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Submit a resume for manual review

    Args:
        file: PDF file to submit
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        SubmitReviewResponse with submission ID and file URL
    """
    try:
        # Validate PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are supported")

        # Read file content
        file_content = await file.read()

        print(f"📄 Submitting resume for review:")
        print(f"   Filename: {file.filename}")
        print(f"   File size: {len(file_content)} bytes")
        print(f"   User ID: {user_id}")

        # Submit resume
        result = review_service.submit_resume(
            user_id=user_id,
            filename=file.filename,
            file_content=file_content
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


@router.post("/admin/complete/{submission_id}", response_model=CompleteSubmissionResponse)
async def complete_submission(
    submission_id: str,
    file: UploadFile = File(...),
    notes: str = None
):
    """
    Admin endpoint: Upload reviewed resume and mark submission as completed

    No authentication required - this is for internal admin use only.
    You can add auth later if needed.

    Args:
        submission_id: UUID of the submission to complete
        file: Reviewed PDF file (will be watermarked automatically)
        notes: Optional reviewer notes for the user

    Returns:
        CompleteSubmissionResponse with success status and reviewed file URL
    """
    try:
        # Validate PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are supported")

        # Read file content
        file_content = await file.read()

        print(f"📤 Completing submission:")
        print(f"   Submission ID: {submission_id}")
        print(f"   File size: {len(file_content)} bytes")
        print(f"   Notes: {notes or 'None'}")

        # Complete the submission
        result = review_service.complete_submission(
            submission_id=submission_id,
            reviewed_file_content=file_content,
            notes=notes
        )

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(404, "Submission not found")
            raise HTTPException(500, result.get("error", "Failed to complete submission"))

        print(f"✅ Submission completed successfully")

        return CompleteSubmissionResponse(
            success=True,
            reviewed_file_url=result["reviewed_file_url"],
            message="Submission completed and reviewed file uploaded successfully"
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
