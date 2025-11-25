"""
Service for managing user resume operations (delete, rename, etc.)
"""
from typing import Dict, Any
from datetime import datetime

from config import supabase
from services.storage_service import storage_service


class UserResumeService:
    """Service for managing user resumes"""

    def __init__(self):
        self.bucket_name = "user-resumes"

    def delete_resume(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a user resume (works for both upload and builder resumes)

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID

        Returns:
            Dictionary with success status
        """
        try:
            # Verify resume belongs to user and get resume details
            result = supabase.table("user_resumes")\
                .select("id, storage_path, resume_source")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            resume_data = result.data
            resume_source = resume_data.get("resume_source")

            # Delete files from storage
            try:
                files_to_delete = []

                # For builder resumes, delete both PDF and JSON
                if resume_source == "builder":
                    files_to_delete = [
                        f"{user_id}/{resume_id}/original.pdf",
                        f"{user_id}/{resume_id}/builder_content.json"
                    ]
                # For uploaded resumes, delete the original file
                else:
                    storage_path = resume_data.get("storage_path")
                    if storage_path:
                        files_to_delete = [storage_path]

                # Delete files (ignore errors if files don't exist)
                if files_to_delete:
                    supabase.storage.from_(self.bucket_name).remove(files_to_delete)
            except Exception as e:
                print(f"Warning: Error deleting files from storage: {e}")
                # Continue with database deletion even if storage deletion fails

            # Delete database record
            supabase.table("user_resumes")\
                .delete()\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .execute()

            return {
                "success": True,
                "message": "Resume deleted successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def rename_resume(self, resume_id: str, user_id: str, new_filename: str) -> Dict[str, Any]:
        """
        Rename a user resume (update filename field)

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID
            new_filename: New filename for the resume

        Returns:
            Dictionary with success status
        """
        try:
            # Verify resume belongs to user
            result = supabase.table("user_resumes")\
                .select("id")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            # Update filename in database
            update_result = supabase.table("user_resumes")\
                .update({
                    "filename": new_filename,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .execute()

            return {
                "success": True,
                "message": "Resume renamed successfully",
                "resume_id": resume_id,
                "filename": new_filename
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global service instance
user_resume_service = UserResumeService()
