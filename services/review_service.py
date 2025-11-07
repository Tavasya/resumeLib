"""
Service for managing resume review submissions
"""
import uuid
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from config import supabase
from services.pdf_service import pdf_service
from services.storage_service import storage_service


class ReviewService:
    """Service for managing resume review submissions"""

    def __init__(self):
        self.bucket_name = "user-resumes"

    def submit_resume(
        self,
        user_id: str,
        filename: str,
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Submit a resume for review

        Args:
            user_id: Clerk user ID
            filename: Original filename
            file_content: PDF file content as bytes

        Returns:
            Dictionary with success status, submission_id, and file_url
        """
        try:
            # Generate unique submission ID
            submission_id = str(uuid.uuid4())

            # Create storage path: {user_id}/{submission_id}.pdf
            storage_path = f"{user_id}/{submission_id}.pdf"

            # Upload to user-resumes bucket using storage service
            file_url = storage_service.upload_file(
                bucket_name=self.bucket_name,
                storage_path=storage_path,
                file_content=file_content,
                content_type="application/pdf"
            )

            # Create database record
            submission_data = {
                "id": submission_id,
                "user_id": user_id,
                "filename": filename,
                "file_url": file_url,
                "storage_path": storage_path,
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("review_submissions").insert(submission_data).execute()

            return {
                "success": True,
                "submission_id": submission_id,
                "file_url": file_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def submit_resume_by_id(
        self,
        user_id: str,
        user_resume_id: str
    ) -> Dict[str, Any]:
        """
        Submit a resume for review using existing user_resume_id

        Args:
            user_id: Clerk user ID
            user_resume_id: ID of resume in user_resumes table

        Returns:
            Dictionary with success status, submission_id, and file_url
        """
        try:
            # Get the user resume from database
            resume_result = supabase.table("user_resumes")\
                .select("id, filename, file_url, storage_path")\
                .eq("id", user_resume_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not resume_result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            resume = resume_result.data

            # Generate unique submission ID
            submission_id = str(uuid.uuid4())

            # Create database record linking to user_resume
            submission_data = {
                "id": submission_id,
                "user_id": user_id,
                "user_resume_id": user_resume_id,
                "filename": resume["filename"],
                "file_url": resume["file_url"],  # Reference original
                "storage_path": resume["storage_path"],  # Reference original
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("review_submissions").insert(submission_data).execute()

            return {
                "success": True,
                "submission_id": submission_id,
                "file_url": resume["file_url"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_submissions(self, user_id: str) -> Dict[str, Any]:
        """
        List all review submissions for a user

        Args:
            user_id: Clerk user ID

        Returns:
            Dictionary with success status and list of submissions
        """
        try:
            result = supabase.table("review_submissions")\
                .select("id, filename, status, file_url, reviewed_file_url, submitted_at, completed_at, paid")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .execute()

            submissions = result.data or []

            return {
                "success": True,
                "submissions": submissions
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "submissions": []
            }

    def list_all_submissions(self) -> Dict[str, Any]:
        """
        List all review submissions from all users (Admin only)

        Returns:
            Dictionary with success status and list of all submissions
        """
        try:
            result = supabase.table("review_submissions")\
                .select("id, user_id, filename, status, file_url, reviewed_file_url, submitted_at, completed_at, paid")\
                .order("created_at", desc=True)\
                .execute()

            submissions = result.data or []

            return {
                "success": True,
                "submissions": submissions
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "submissions": []
            }

    def get_submission(self, submission_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get details of a single submission

        Args:
            submission_id: UUID of submission
            user_id: Clerk user ID (for authorization)

        Returns:
            Dictionary with success status and submission details
        """
        try:
            result = supabase.table("review_submissions")\
                .select("id, user_id, filename, file_url, storage_path, status, reviewed_file_url, notes, created_at, updated_at, submitted_at, completed_at, paid, stripe_session_id, stripe_payment_intent_id")\
                .eq("id", submission_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            return {
                "success": True,
                "submission": result.data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_submission_admin(self, submission_id: str) -> Dict[str, Any]:
        """
        Get details of a single submission (Admin only - no ownership check)

        Args:
            submission_id: UUID of submission

        Returns:
            Dictionary with success status and submission details
        """
        try:
            result = supabase.table("review_submissions")\
                .select("id, user_id, filename, file_url, storage_path, status, reviewed_file_url, notes, created_at, updated_at, submitted_at, completed_at, paid, stripe_session_id, stripe_payment_intent_id")\
                .eq("id", submission_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            return {
                "success": True,
                "submission": result.data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def complete_submission(
        self,
        submission_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete a submission by generating PDF from annotations (Admin only)

        Args:
            submission_id: UUID of submission
            notes: Optional reviewer notes/feedback for the user

        Returns:
            Dictionary with success status and reviewed_file_url
        """
        try:
            # 1. Get submission details
            result = supabase.table("review_submissions")\
                .select("user_id, storage_path, file_url")\
                .eq("id", submission_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            user_id = result.data["user_id"]
            original_file_url = result.data["file_url"]

            # 2. Get all annotations for this submission
            annotations_result = supabase.table("review_annotations")\
                .select("page_number, position, content, annotation_type")\
                .eq("submission_id", submission_id)\
                .order("created_at", desc=False)\
                .execute()

            annotations = annotations_result.data or []

            # 3. Download original PDF
            response = requests.get(original_file_url)
            response.raise_for_status()
            original_pdf_bytes = response.content

            # 4. Generate PDF with annotations burned in
            pdf_result = pdf_service.generate_annotated_pdf(
                pdf_bytes=original_pdf_bytes,
                annotations=annotations,
                watermark_text="Reviewed by cookedcareer.com"
            )

            if not pdf_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to generate annotated PDF: {pdf_result.get('error')}"
                }

            reviewed_pdf_bytes = pdf_result["pdf_bytes"]

            # 5. Upload the generated PDF to storage
            # Get user_resume_id from submission to organize under that resume's folder
            submission_result = supabase.table("review_submissions")\
                .select("user_resume_id")\
                .eq("id", submission_id)\
                .single()\
                .execute()

            user_resume_id = submission_result.data.get("user_resume_id") if submission_result.data else None

            if user_resume_id:
                reviewed_storage_path = f"{user_id}/{user_resume_id}/reviewed/{submission_id}_reviewed.pdf"
            else:
                # Fallback for old data without FK
                reviewed_storage_path = f"{user_id}/review/{submission_id}_reviewed.pdf"

            reviewed_file_url = storage_service.upload_file(
                bucket_name=self.bucket_name,
                storage_path=reviewed_storage_path,
                file_content=reviewed_pdf_bytes,
                content_type="application/pdf"
            )

            # 6. Update submission record
            update_data = {
                "status": "completed",
                "reviewed_file_url": reviewed_file_url,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if notes:
                update_data["notes"] = notes

            supabase.table("review_submissions")\
                .update(update_data)\
                .eq("id", submission_id)\
                .execute()

            return {
                "success": True,
                "reviewed_file_url": reviewed_file_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_submission(self, submission_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a submission and its files

        Args:
            submission_id: UUID of submission
            user_id: Clerk user ID (for authorization)

        Returns:
            Dictionary with success status
        """
        try:
            # Get submission to find storage paths
            result = supabase.table("review_submissions")\
                .select("user_id, reviewed_file_url")\
                .eq("id", submission_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            # NOTE: We do NOT delete the original file - it belongs to user_resumes table
            # Only delete the reviewed file if it exists
            if result.data.get("reviewed_file_url"):
                # Get submission to find correct path
                submission_result = supabase.table("review_submissions")\
                    .select("user_resume_id")\
                    .eq("id", submission_id)\
                    .single()\
                    .execute()

                user_resume_id = submission_result.data.get("user_resume_id") if submission_result.data else None

                if user_resume_id:
                    reviewed_path = f"{user_id}/{user_resume_id}/reviewed/{submission_id}_reviewed.pdf"
                else:
                    reviewed_path = f"{user_id}/review/{submission_id}_reviewed.pdf"

                try:
                    supabase.storage.from_(self.bucket_name).remove([reviewed_path])
                except:
                    pass  # File might not exist

            # Delete database record
            supabase.table("review_submissions")\
                .delete()\
                .eq("id", submission_id)\
                .eq("user_id", user_id)\
                .execute()

            return {
                "success": True,
                "message": "Submission deleted successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_annotation(
        self,
        submission_id: str,
        annotation_type: str,
        page_number: int,
        position: Dict[str, Any],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an annotation for a submission (Admin only)

        Args:
            submission_id: UUID of submission
            annotation_type: Type of annotation ('highlight', 'area', or 'drawing')
            page_number: Page number (0-indexed)
            position: Position data as dict
            content: Content data as dict

        Returns:
            Dictionary with success status and annotation details
        """
        try:
            # Validate annotation type
            if annotation_type not in ['highlight', 'area', 'drawing']:
                return {
                    "success": False,
                    "error": "Invalid annotation type. Must be 'highlight', 'area', or 'drawing'"
                }

            # Verify submission exists
            result = supabase.table("review_submissions")\
                .select("id")\
                .eq("id", submission_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            # Generate unique annotation ID
            annotation_id = str(uuid.uuid4())

            # Create annotation record
            annotation_data = {
                "id": annotation_id,
                "submission_id": submission_id,
                "annotation_type": annotation_type,
                "page_number": page_number,
                "position": position,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("review_annotations")\
                .insert(annotation_data)\
                .execute()

            return {
                "success": True,
                "annotation": annotation_data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_annotations(self, submission_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all annotations for a submission

        Args:
            submission_id: UUID of submission
            user_id: Optional user_id for authorization check (if provided, verifies ownership)

        Returns:
            Dictionary with success status and list of annotations
        """
        try:
            # If user_id provided, verify they own this submission
            if user_id:
                result = supabase.table("review_submissions")\
                    .select("id")\
                    .eq("id", submission_id)\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()

                if not result.data:
                    return {
                        "success": False,
                        "error": "Submission not found or access denied"
                    }

            # Get all annotations for this submission
            result = supabase.table("review_annotations")\
                .select("id, submission_id, annotation_type, page_number, position, content, created_at")\
                .eq("submission_id", submission_id)\
                .order("created_at", desc=False)\
                .execute()

            annotations = result.data or []

            return {
                "success": True,
                "annotations": annotations
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "annotations": []
            }

    def delete_annotation(self, annotation_id: str) -> Dict[str, Any]:
        """
        Delete an annotation (Admin only)

        Args:
            annotation_id: UUID of annotation to delete

        Returns:
            Dictionary with success status
        """
        try:
            # Delete annotation
            result = supabase.table("review_annotations")\
                .delete()\
                .eq("id", annotation_id)\
                .execute()

            return {
                "success": True,
                "message": "Annotation deleted successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global review service instance
review_service = ReviewService()
