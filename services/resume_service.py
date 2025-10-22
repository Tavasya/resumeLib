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
        Simple search resumes by text (searches name, title, skills, raw_text)

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

    def advanced_search(
        self,
        query: Optional[str] = None,
        seniority: Optional[str] = None,
        skills: Optional[List[str]] = None,
        school: Optional[str] = None,
        min_experience: Optional[int] = None,
        max_experience: Optional[int] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Advanced search for resumes with filters
        """
        # Pinned/featured resume IDs (always appear first)
        PINNED_RESUME_IDS = [
            "eacb4ca1-9092-407c-a0e2-dcc625df062b",
            "33fab7b2-f58e-46a7-bfd7-dee9ecdd9a6f",
            "ab47820b-8036-4942-b90d-a09fd20acdd4",
            "9d79b9db-4112-4a05-bfcc-70be1acf79e4",
            "99b5ed0a-fb33-4a67-9e8a-fb8a0e85ae6a",
            "decdf60f-badf-4f2c-88b8-ed4eb478325f"
            
        ]

        try:
            # Start with all resumes
            db_query = supabase.table(self.table).select("*")

            # Full-text search using ilike on raw_text
            if query:
                db_query = db_query.ilike("raw_text", f"%{query}%")

            # Filter by seniority
            if seniority:
                db_query = db_query.eq("seniority", seniority.lower())

            # Filter by experience range
            if min_experience is not None:
                db_query = db_query.gte("years_of_experience", min_experience)
            if max_experience is not None:
                db_query = db_query.lte("years_of_experience", max_experience)

            # Order by newest first
            db_query = db_query.order("created_at", desc=True)

            # Execute query
            response = db_query.execute()
            all_results = response.data if response.data else []

            # Filter by skills in Python (case-insensitive matching)
            if skills:
                filtered_results = []
                for resume in all_results:
                    resume_skills = resume.get("skills", [])
                    # Convert both search skills and resume skills to lowercase for comparison
                    resume_skills_lower = [s.lower() for s in resume_skills] if resume_skills else []
                    search_skills_lower = [s.lower() for s in skills]
                    # Check if any of the search skills match
                    if any(skill in resume_skills_lower for skill in search_skills_lower):
                        filtered_results.append(resume)
                all_results = filtered_results

            # Filter by school (search in education.institution field)
            if school:
                filtered_results = []
                school_lower = school.lower()
                for resume in all_results:
                    education = resume.get("education", [])
                    # Check if any institution matches the school search
                    if education and any(
                        school_lower in edu.get("institution", "").lower()
                        for edu in education if isinstance(edu, dict)
                    ):
                        filtered_results.append(resume)
                all_results = filtered_results

            # Separate pinned resumes from regular results
            pinned_resumes = []
            regular_resumes = []

            for resume in all_results:
                if resume.get("id") in PINNED_RESUME_IDS:
                    pinned_resumes.append(resume)
                else:
                    regular_resumes.append(resume)

            # Sort pinned resumes in the order they appear in PINNED_RESUME_IDS
            pinned_resumes.sort(key=lambda r: PINNED_RESUME_IDS.index(r.get("id")))

            # Combine: pinned first, then regular
            all_results = pinned_resumes + regular_resumes

            # Pagination in Python
            total = len(all_results)
            offset = (page - 1) * limit
            paginated_results = all_results[offset:offset + limit]

            # Convert to ResumeInDB objects
            results = [ResumeInDB(**resume) for resume in paginated_results]

            return {
                "results": results,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit if total > 0 else 0
                },
                "filters_applied": {
                    "query": query,
                    "seniority": seniority,
                    "skills": skills,
                    "school": school,
                    "min_experience": min_experience,
                    "max_experience": max_experience
                }
            }

        except Exception as e:
            print(f"Error in advanced search: {e}")
            return {
                "results": [],
                "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0},
                "filters_applied": {"query": query, "seniority": seniority, "skills": skills, "school": school, "min_experience": min_experience, "max_experience": max_experience},
                "error": str(e)
            }


# Global service instance
resume_service = ResumeService()
