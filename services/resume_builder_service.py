"""
Service for managing resume builder functionality
"""
import uuid
import json
from typing import Dict, Any
from datetime import datetime
from weasyprint import HTML
from io import BytesIO

from config import supabase
from services.storage_service import storage_service


class ResumeBuilderService:
    """Service for managing resume builder"""

    def __init__(self):
        self.bucket_name = "user-resumes"

    def create_builder_resume(self, user_id: str, title: str = "Untitled Resume") -> Dict[str, Any]:
        """
        Create a new builder resume

        Args:
            user_id: Clerk user ID
            title: Resume title/filename

        Returns:
            Dictionary with success status and resume_id
        """
        try:
            # Generate unique resume ID
            resume_id = str(uuid.uuid4())

            # Create database record
            resume_data = {
                "id": resume_id,
                "user_id": user_id,
                "filename": title,
                "file_type": "pdf",
                "resume_source": "builder",
                "builder_content": None,  # Will be saved when user saves content
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("user_resumes").insert(resume_data).execute()

            return {
                "success": True,
                "resume_id": resume_id,
                "title": title
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def save_builder_content(
        self,
        resume_id: str,
        user_id: str,
        editor_data: Dict[str, Any],
        title: str = "Untitled Resume"
    ) -> Dict[str, Any]:
        """
        Save Editor.js content to database

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID
            editor_data: Editor.js output data
            title: Resume title/filename

        Returns:
            Dictionary with success status
        """
        try:
            # Verify resume belongs to user
            result = supabase.table("user_resumes")\
                .select("id")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .eq("resume_source", "builder")\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            # Update database with Editor.js content
            update_data = {
                "builder_content": editor_data,
                "filename": title,
                "updated_at": datetime.utcnow().isoformat()
            }

            supabase.table("user_resumes")\
                .update(update_data)\
                .eq("id", resume_id)\
                .execute()

            # Also save JSON file to storage for backup
            storage_path = f"{user_id}/{resume_id}/builder_content.json"
            json_bytes = json.dumps(editor_data, indent=2).encode('utf-8')

            storage_service.upload_file(
                bucket_name=self.bucket_name,
                storage_path=storage_path,
                file_content=json_bytes,
                content_type="application/json"
            )

            return {
                "success": True,
                "message": "Content saved successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_pdf(self, resume_id: str, user_id: str, html: str) -> Dict[str, Any]:
        """
        Generate PDF from HTML provided by frontend

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID
            html: Complete HTML document with styling (from frontend)

        Returns:
            Dictionary with success status and file_url
        """
        try:
            # Verify resume belongs to user
            result = supabase.table("user_resumes")\
                .select("id, filename")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .eq("resume_source", "builder")\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            # Generate PDF from HTML (frontend controls all styling)
            pdf_bytes = self._generate_pdf_from_html(html)

            # Upload to storage
            storage_path = f"{user_id}/{resume_id}/original.pdf"
            file_url = storage_service.upload_file(
                bucket_name=self.bucket_name,
                storage_path=storage_path,
                file_content=pdf_bytes,
                content_type="application/pdf"
            )

            # Update database with file_url and storage_path
            supabase.table("user_resumes")\
                .update({
                    "file_url": file_url,
                    "storage_path": storage_path,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", resume_id)\
                .execute()

            return {
                "success": True,
                "file_url": file_url,
                "message": "PDF generated successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_builder_content(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get saved builder content for editing

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID

        Returns:
            Dictionary with success status and builder_content
        """
        try:
            result = supabase.table("user_resumes")\
                .select("id, user_id, filename, builder_content, file_url, created_at, updated_at")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .eq("resume_source", "builder")\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            resume_data = result.data

            return {
                "success": True,
                "resume": {
                    "id": resume_data.get("id"),
                    "user_id": resume_data.get("user_id"),
                    "title": resume_data.get("filename"),
                    "builder_content": resume_data.get("builder_content"),
                    "created_at": resume_data.get("created_at"),
                    "updated_at": resume_data.get("updated_at")
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_builder_resume(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a builder resume and all associated files

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID

        Returns:
            Dictionary with success status
        """
        try:
            # Verify resume belongs to user
            result = supabase.table("user_resumes")\
                .select("id")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .eq("resume_source", "builder")\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            # Delete files from storage (folder deletion)
            try:
                # List all files in the resume folder
                files_to_delete = [
                    f"{user_id}/{resume_id}/original.pdf",
                    f"{user_id}/{resume_id}/builder_content.json"
                ]
                supabase.storage.from_(self.bucket_name).remove(files_to_delete)
            except:
                pass  # Files might not exist

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

    def _generate_pdf_from_html(self, html: str) -> bytes:
        """
        Generate PDF from complete HTML document using WeasyPrint

        Frontend provides complete HTML with all styling.
        Backend just does the conversion.

        Args:
            html: Complete HTML document with styling

        Returns:
            PDF bytes
        """
        # Generate PDF from complete HTML (no styling needed - frontend handles it)
        pdf_file = BytesIO()
        HTML(string=html).write_pdf(pdf_file)
        return pdf_file.getvalue()


# Global service instance
resume_builder_service = ResumeBuilderService()
