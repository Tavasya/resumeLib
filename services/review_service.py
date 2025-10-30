"""
Service for managing resume review submissions
"""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from config import supabase
from services.anonymizer_service import anonymizer_service


class ReviewService:
    """Service for managing resume review submissions"""

    def __init__(self):
        self.bucket_name = "review-submissions"

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

            # Upload to review-submissions bucket
            response = supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

            # Get public URL
            file_url = supabase.storage.from_(self.bucket_name).get_public_url(storage_path)

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
                .select("id, filename, status, file_url, reviewed_file_url, submitted_at, completed_at")\
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
                .select("*")\
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

    def update_reviewed_file(
        self,
        submission_id: str,
        reviewed_file_content: bytes,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload reviewed file and mark submission as completed
        (This is for manual review - you upload the edited file)

        Args:
            submission_id: UUID of submission
            reviewed_file_content: Reviewed PDF file content as bytes
            notes: Optional reviewer notes

        Returns:
            Dictionary with success status and reviewed_file_url
        """
        try:
            # Get submission to find user_id
            result = supabase.table("review_submissions")\
                .select("user_id, storage_path")\
                .eq("id", submission_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            user_id = result.data["user_id"]

            # Add watermark to reviewed file
            watermark_result = anonymizer_service.add_watermark_to_pdf(
                reviewed_file_content,
                watermark_text="Reviewed by cookedcareer.com"
            )

            if not watermark_result["success"]:
                print(f"⚠️ Warning: Failed to add watermark: {watermark_result.get('error')}")
                # Continue with original file if watermark fails
                watermarked_content = reviewed_file_content
            else:
                watermarked_content = watermark_result["pdf_bytes"]

            # Create storage path for reviewed file
            reviewed_storage_path = f"{user_id}/{submission_id}_reviewed.pdf"

            # Upload reviewed file with watermark
            response = supabase.storage.from_(self.bucket_name).upload(
                path=reviewed_storage_path,
                file=watermarked_content,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

            # Get public URL
            reviewed_file_url = supabase.storage.from_(self.bucket_name).get_public_url(reviewed_storage_path)

            # Update submission record
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
                .select("storage_path, reviewed_file_url")\
                .eq("id", submission_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Submission not found"
                }

            storage_path = result.data["storage_path"]

            # Delete original file from storage
            try:
                supabase.storage.from_(self.bucket_name).remove([storage_path])
            except:
                pass  # File might not exist

            # Delete reviewed file if exists
            if result.data.get("reviewed_file_url"):
                reviewed_path = f"{storage_path.rsplit('.', 1)[0]}_reviewed.pdf"
                try:
                    supabase.storage.from_(self.bucket_name).remove([reviewed_path])
                except:
                    pass

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


# Global review service instance
review_service = ReviewService()
