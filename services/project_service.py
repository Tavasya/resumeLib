"""
Project service for Supabase operations
Handles operations for extracting projects from resumes
"""
from typing import List, Dict, Any
from config import supabase


class ProjectService:
    """Service class for project-related operations"""

    def __init__(self):
        self.table = "resumes"

    def get_projects_with_links(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Get all projects that have links/URLs with pagination

        Args:
            page: Page number (starts at 1)
            limit: Number of projects per page

        Returns:
            Dictionary with projects and pagination info
        """
        print(f"DEBUG SERVICE: get_projects_with_links called with page={page}, limit={limit}")
        try:
            # Get all resumes
            print(f"DEBUG SERVICE: Fetching resumes from table '{self.table}'")
            response = supabase.table(self.table).select("*").execute()
            print(f"DEBUG SERVICE: Got response with {len(response.data) if response.data else 0} resumes")

            if not response.data:
                return {
                    "projects": [],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": 0,
                        "total_pages": 0
                    }
                }

            all_projects = []

            for resume in response.data:
                projects = resume.get("projects", [])

                if not projects:
                    continue

                # Filter projects that have a non-empty URL
                for project in projects:
                    if isinstance(project, dict) and project.get("url"):
                        url = project.get("url", "").strip()
                        if url:  # Only include if URL is not empty after stripping
                            all_projects.append({
                                "project_name": project.get("name"),
                                "project_url": url,
                                "project_description": project.get("description"),
                                "project_technologies": project.get("technologies", []),
                                "owner_id": resume.get("id"),
                                "owner_name": resume.get("name"),
                                "owner_email": resume.get("email"),
                                "owner_title": resume.get("title")
                            })

            # Apply pagination
            total = len(all_projects)
            offset = (page - 1) * limit
            paginated_projects = all_projects[offset:offset + limit]

            print(f"DEBUG SERVICE: Total projects with links: {total}")
            print(f"DEBUG SERVICE: Returning {len(paginated_projects)} projects for page {page}")

            result = {
                "projects": paginated_projects,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit if total > 0 else 0
                }
            }
            print(f"DEBUG SERVICE: Result structure: {result.keys()}")
            return result

        except Exception as e:
            print(f"ERROR in get_projects_with_links: {e}")
            import traceback
            traceback.print_exc()
            return {
                "projects": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0
                },
                "error": str(e)
            }


# Global service instance
project_service = ProjectService()
