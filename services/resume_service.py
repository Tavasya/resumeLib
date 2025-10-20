"""
Resume service for Supabase operations
Handles CRUD operations for resumes
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from config import supabase
from models import ResumeCreate, ResumeInDB, ResumeUpdate


class ResumeService:
    """Service class for resume database operations"""

    def __init__(self):
        self.table = "resumes"

    def create_resume(self, resume: ResumeCreate) -> Optional[ResumeInDB]:
        """
        Create a new resume in the database

        Args:
            resume: ResumeCreate object with resume data

        Returns:
            ResumeInDB object if successful, None otherwise
        """
        try:
            # Convert Pydantic model to dict
            resume_data = resume.model_dump(exclude_none=False)

            # Convert nested Pydantic models to dicts for JSONB fields
            if resume_data.get("experience"):
                resume_data["experience"] = [
                    exp.model_dump() if hasattr(exp, "model_dump") else exp
                    for exp in resume.experience
                ]

            if resume_data.get("education"):
                resume_data["education"] = [
                    edu.model_dump() if hasattr(edu, "model_dump") else edu
                    for edu in resume.education
                ]

            if resume_data.get("projects"):
                resume_data["projects"] = [
                    proj.model_dump() if hasattr(proj, "model_dump") else proj
                    for proj in resume.projects
                ]

            if resume_data.get("certifications"):
                resume_data["certifications"] = [
                    cert.model_dump() if hasattr(cert, "model_dump") else cert
                    for cert in resume.certifications
                ]

            # Insert into Supabase
            response = supabase.table(self.table).insert(resume_data).execute()

            if response.data and len(response.data) > 0:
                return ResumeInDB(**response.data[0])
            return None

        except Exception as e:
            print(f"Error creating resume: {e}")
            return None

    def get_resume_by_id(self, resume_id: UUID) -> Optional[ResumeInDB]:
        """
        Get a resume by ID

        Args:
            resume_id: UUID of the resume

        Returns:
            ResumeInDB object if found, None otherwise
        """
        try:
            response = supabase.table(self.table).select("*").eq("id", str(resume_id)).execute()

            if response.data and len(response.data) > 0:
                return ResumeInDB(**response.data[0])
            return None

        except Exception as e:
            print(f"Error getting resume: {e}")
            return None

    def get_resume_by_email(self, email: str) -> Optional[ResumeInDB]:
        """
        Get a resume by email (to avoid duplicates)

        Args:
            email: Email address

        Returns:
            ResumeInDB object if found, None otherwise
        """
        try:
            response = supabase.table(self.table).select("*").eq("email", email).execute()

            if response.data and len(response.data) > 0:
                return ResumeInDB(**response.data[0])
            return None

        except Exception as e:
            print(f"Error getting resume by email: {e}")
            return None

    def list_resumes(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ResumeInDB]:
        """
        List resumes with optional filters

        Args:
            limit: Maximum number of resumes to return
            offset: Number of resumes to skip
            filters: Dictionary of filters (e.g., {"title": "Software Engineer"})

        Returns:
            List of ResumeInDB objects
        """
        try:
            query = supabase.table(self.table).select("*")

            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply pagination
            response = query.range(offset, offset + limit - 1).execute()

            if response.data:
                return [ResumeInDB(**resume) for resume in response.data]
            return []

        except Exception as e:
            print(f"Error listing resumes: {e}")
            return []

    def update_resume(self, resume_id: UUID, resume_update: ResumeUpdate) -> Optional[ResumeInDB]:
        """
        Update a resume

        Args:
            resume_id: UUID of the resume to update
            resume_update: ResumeUpdate object with fields to update

        Returns:
            Updated ResumeInDB object if successful, None otherwise
        """
        try:
            # Only include fields that are set
            update_data = resume_update.model_dump(exclude_none=True)

            if not update_data:
                return self.get_resume_by_id(resume_id)

            response = (
                supabase.table(self.table)
                .update(update_data)
                .eq("id", str(resume_id))
                .execute()
            )

            if response.data and len(response.data) > 0:
                return ResumeInDB(**response.data[0])
            return None

        except Exception as e:
            print(f"Error updating resume: {e}")
            return None

    def delete_resume(self, resume_id: UUID) -> bool:
        """
        Delete a resume

        Args:
            resume_id: UUID of the resume to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            response = supabase.table(self.table).delete().eq("id", str(resume_id)).execute()
            return True

        except Exception as e:
            print(f"Error deleting resume: {e}")
            return False

    def search_resumes(self, search_query: str, limit: int = 50) -> List[ResumeInDB]:
        """
        Search resumes by text (searches name, title, skills, raw_text)

        Args:
            search_query: Text to search for
            limit: Maximum number of results

        Returns:
            List of matching ResumeInDB objects
        """
        try:
            # Supabase text search using ilike
            response = (
                supabase.table(self.table)
                .select("*")
                .or_(
                    f"name.ilike.%{search_query}%,"
                    f"title.ilike.%{search_query}%,"
                    f"company.ilike.%{search_query}%,"
                    f"raw_text.ilike.%{search_query}%"
                )
                .limit(limit)
                .execute()
            )

            if response.data:
                return [ResumeInDB(**resume) for resume in response.data]
            return []

        except Exception as e:
            print(f"Error searching resumes: {e}")
            return []


# Global service instance
resume_service = ResumeService()
