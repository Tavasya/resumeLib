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

    def generate_pdf(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        """
        Generate PDF from saved Editor.js content

        Args:
            resume_id: UUID of resume
            user_id: Clerk user ID

        Returns:
            Dictionary with success status and file_url
        """
        try:
            # Get resume with builder content
            result = supabase.table("user_resumes")\
                .select("id, builder_content, filename")\
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

            resume = result.data
            editor_data = resume.get("builder_content")

            if not editor_data:
                return {
                    "success": False,
                    "error": "No content to generate PDF from. Please save content first."
                }

            # Parse Editor.js blocks to HTML
            html_content = self._convert_blocks_to_html(editor_data.get("blocks", []))

            # Generate PDF using WeasyPrint
            pdf_bytes = self._generate_pdf_from_html(html_content)

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
            Dictionary with success status and editor_data
        """
        try:
            result = supabase.table("user_resumes")\
                .select("id, filename, builder_content, file_url")\
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

            resume = result.data

            return {
                "success": True,
                "resume_id": resume_id,
                "title": resume.get("filename"),
                "editor_data": resume.get("builder_content"),
                "file_url": resume.get("file_url")
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

    def _convert_blocks_to_html(self, blocks: list) -> str:
        """
        Convert Editor.js blocks to HTML

        Args:
            blocks: List of Editor.js blocks

        Returns:
            HTML string
        """
        html_parts = []

        for block in blocks:
            block_type = block.get("type")
            data = block.get("data", {})

            if block_type == "header":
                level = data.get("level", 2)
                text = data.get("text", "")
                html_parts.append(f'<h{level}>{text}</h{level}>')

            elif block_type == "paragraph":
                text = data.get("text", "")
                # Replace &nbsp; with spaces for cleaner PDF
                text = text.replace("&nbsp;", " ")
                html_parts.append(f'<p>{text}</p>')

            elif block_type == "list":
                style = data.get("style", "unordered")
                items = data.get("items", [])
                tag = "ul" if style == "unordered" else "ol"

                list_html = f'<{tag}>'
                for item in items:
                    content = item.get("content", "") if isinstance(item, dict) else item
                    list_html += f'<li>{content}</li>'
                list_html += f'</{tag}>'

                html_parts.append(list_html)

            elif block_type == "delimiter":
                # Horizontal line separator
                html_parts.append('<hr>')

        return "\n".join(html_parts)

    def _generate_pdf_from_html(self, html_content: str) -> bytes:
        """
        Generate PDF from HTML using WeasyPrint

        Args:
            html_content: HTML string

        Returns:
            PDF bytes
        """
        # Create a styled HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: Letter;
                    margin: 1in;
                }}

                body {{
                    font-family: 'Helvetica', 'Arial', sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #000;
                }}

                h1 {{
                    font-size: 24pt;
                    font-weight: bold;
                    margin: 0 0 8pt 0;
                    text-align: center;
                }}

                h2 {{
                    font-size: 14pt;
                    font-weight: bold;
                    margin: 16pt 0 8pt 0;
                    border-bottom: 1px solid #000;
                    padding-bottom: 4pt;
                }}

                h3 {{
                    font-size: 12pt;
                    font-weight: bold;
                    margin: 12pt 0 6pt 0;
                }}

                p {{
                    margin: 4pt 0;
                }}

                ul, ol {{
                    margin: 4pt 0;
                    padding-left: 20pt;
                }}

                li {{
                    margin: 2pt 0;
                }}

                b, strong {{
                    font-weight: bold;
                }}

                i, em {{
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        pdf_file = BytesIO()
        HTML(string=full_html).write_pdf(pdf_file)
        return pdf_file.getvalue()


# Global service instance
resume_builder_service = ResumeBuilderService()
