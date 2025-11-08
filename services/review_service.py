"""
Service for managing resume review submissions
"""
import uuid
import requests
import os
from typing import Dict, Any, Optional
from datetime import datetime
from config import supabase
from services.pdf_service import pdf_service
from services.storage_service import storage_service
from services.email_service import email_service


class ReviewService:
    """Service for managing resume review submissions"""

    def __init__(self):
        self.bucket_name = "user-resumes"

    def submit_resume(
        self,
        user_id: str,
        filename: str,
        file_content: bytes,
        review_context: Optional[str] = None,
        reviewer_type: str = "team",
        delivery_speed: str = "standard",
        base_price: float = 0.00,
        delivery_fee: float = 0.00,
        total_price: float = 0.00
    ) -> Dict[str, Any]:
        """
        Submit a resume for review

        This also adds the resume to the user's library for future reference.

        Args:
            user_id: Clerk user ID
            filename: Original filename
            file_content: PDF file content as bytes
            review_context: Context for review
            reviewer_type: Type of reviewer (team, big_tech, startup, technical)
            delivery_speed: Delivery speed (standard, express)
            base_price: Base price for reviewer type
            delivery_fee: Additional fee for express delivery
            total_price: Total cost

        Returns:
            Dictionary with success status, submission_id, and file_url
        """
        try:
            # Generate unique IDs
            resume_id = str(uuid.uuid4())  # For user_resumes table
            submission_id = str(uuid.uuid4())  # For review_submissions table

            # Create storage path using library structure: {user_id}/{resume_id}/original.pdf
            storage_path = f"{user_id}/{resume_id}/original.pdf"

            # Upload to user-resumes bucket using storage service
            file_url = storage_service.upload_file(
                bucket_name=self.bucket_name,
                storage_path=storage_path,
                file_content=file_content,
                content_type="application/pdf"
            )

            # 1. First, add to user's resume library
            resume_data = {
                "id": resume_id,
                "user_id": user_id,
                "filename": filename,
                "file_url": file_url,
                "storage_path": storage_path,
                "file_type": "pdf"
            }
            supabase.table("user_resumes").insert(resume_data).execute()

            # 2. Then, create review submission linked to the library resume
            # Auto-mark as paid if free (no payment required)
            is_paid = total_price == 0.0

            submission_data = {
                "id": submission_id,
                "user_id": user_id,
                "user_resume_id": resume_id,  # Link to user_resumes table
                "filename": filename,
                "file_url": file_url,
                "storage_path": storage_path,
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat(),
                "review_context": review_context,
                "reviewer_type": reviewer_type,
                "delivery_speed": delivery_speed,
                "base_price": base_price,
                "delivery_fee": delivery_fee,
                "total_price": total_price,
                "paid": is_paid
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
        user_resume_id: str,
        review_context: Optional[str] = None,
        reviewer_type: str = "team",
        delivery_speed: str = "standard",
        base_price: float = 0.00,
        delivery_fee: float = 0.00,
        total_price: float = 0.00
    ) -> Dict[str, Any]:
        """
        Submit a resume for review using existing user_resume_id

        Args:
            user_id: Clerk user ID
            user_resume_id: ID of resume in user_resumes table
            review_context: Context for review
            reviewer_type: Type of reviewer (team, big_tech, startup, technical)
            delivery_speed: Delivery speed (standard, express)
            base_price: Base price for reviewer type
            delivery_fee: Additional fee for express delivery
            total_price: Total cost

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

            # Auto-mark as paid if free (no payment required)
            is_paid = total_price == 0.0

            # Create database record linking to user_resume
            submission_data = {
                "id": submission_id,
                "user_id": user_id,
                "user_resume_id": user_resume_id,
                "filename": resume["filename"],
                "file_url": resume["file_url"],  # Reference original
                "storage_path": resume["storage_path"],  # Reference original
                "status": "pending",
                "submitted_at": datetime.utcnow().isoformat(),
                "review_context": review_context,
                "reviewer_type": reviewer_type,
                "delivery_speed": delivery_speed,
                "base_price": base_price,
                "delivery_fee": delivery_fee,
                "total_price": total_price,
                "paid": is_paid
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
                .select("id, filename, status, file_url, reviewed_file_url, submitted_at, completed_at, paid, review_context, reviewer_type, delivery_speed, base_price, delivery_fee, total_price")\
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
                .select("id, user_id, filename, status, file_url, reviewed_file_url, submitted_at, completed_at, paid, review_context, reviewer_type, delivery_speed, base_price, delivery_fee, total_price")\
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
                .select("id, user_id, filename, file_url, storage_path, status, reviewed_file_url, notes, created_at, updated_at, submitted_at, completed_at, paid, stripe_session_id, stripe_payment_intent_id, review_context, reviewer_type, delivery_speed, base_price, delivery_fee, total_price")\
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
                .select("id, user_id, filename, file_url, storage_path, status, reviewed_file_url, notes, created_at, updated_at, submitted_at, completed_at, paid, stripe_session_id, stripe_payment_intent_id, review_context, reviewer_type, delivery_speed, base_price, delivery_fee, total_price")\
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

            # 7. Send email notification to user
            self._send_review_ready_email(user_id, submission_id)

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

    def _send_review_ready_email(self, user_id: str, submission_id: str) -> None:
        """
        Send email notification when review is ready

        Args:
            user_id: Clerk user ID
            submission_id: Review submission ID
        """
        try:
            # Get user info from Clerk
            clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
            if not clerk_secret_key:
                print("⚠️  CLERK_SECRET_KEY not configured, skipping email")
                return

            # Fetch user data from Clerk API
            clerk_api_url = f"https://api.clerk.com/v1/users/{user_id}"
            headers = {
                "Authorization": f"Bearer {clerk_secret_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(clerk_api_url, headers=headers)

            if response.status_code != 200:
                print(f"⚠️  Failed to fetch user from Clerk: {response.status_code}")
                return

            user_data = response.json()

            # Extract user info
            first_name = user_data.get("first_name", "there")
            email_addresses = user_data.get("email_addresses", [])

            if not email_addresses:
                print(f"⚠️  No email address found for user {user_id}")
                return

            # Get primary email
            primary_email = None
            for email_obj in email_addresses:
                if email_obj.get("id") == user_data.get("primary_email_address_id"):
                    primary_email = email_obj.get("email_address")
                    break

            if not primary_email and email_addresses:
                primary_email = email_addresses[0].get("email_address")

            if not primary_email:
                print(f"⚠️  No valid email address found for user {user_id}")
                return

            # Construct review URL
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            review_url = f"{frontend_url}/resume-review"

            # Send email
            print(f"📧 Sending review ready email to {primary_email}")
            result = email_service.send_review_ready_email(
                to_email=primary_email,
                first_name=first_name,
                review_url=review_url
            )

            if result["success"]:
                print(f"✅ Email sent successfully")
            else:
                print(f"⚠️  Failed to send email: {result.get('error')}")

        except Exception as e:
            # Don't fail the entire operation if email fails
            print(f"⚠️  Error sending review ready email: {str(e)}")


# Global review service instance
review_service = ReviewService()
