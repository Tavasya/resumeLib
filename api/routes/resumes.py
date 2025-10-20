"""
Resume API routes
Handles all resume-related endpoints including search
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from uuid import UUID

from services.resume_service import resume_service
from services.project_service import project_service
from models.resume import ResumeInDB

router = APIRouter()


@router.get("/search")
async def search_resumes(
    q: Optional[str] = Query(None, description="Search query (searches across all resume text)"),
    seniority: Optional[str] = Query(None, description="Filter by seniority level (intern, junior, mid-level, senior, staff, principal, etc.)"),
    skills: Optional[str] = Query(None, description="Comma-separated list of skills (e.g., 'python,react,aws')"),
    school: Optional[str] = Query(None, description="Filter by school/university (e.g., 'MIT', 'Stanford', 'Berkeley')"),
    min_experience: Optional[int] = Query(None, ge=0, description="Minimum years of experience"),
    max_experience: Optional[int] = Query(None, ge=0, description="Maximum years of experience"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Advanced search for resumes with multiple filters

    Example queries:
    - /api/resumes/search?q=google+intern
    - /api/resumes/search?q=software+engineer&seniority=senior&skills=python,react
    - /api/resumes/search?seniority=intern&min_experience=0&max_experience=2
    - /api/resumes/search?q=machine+learning&skills=tensorflow,pytorch&page=2
    - /api/resumes/search?school=stanford&seniority=intern
    - /api/resumes/search?school=MIT&skills=python

    The search uses full-text search on the raw resume text, so it will find:
    - Company names mentioned anywhere (current or past positions)
    - Keywords in job descriptions
    - Project descriptions and technologies
    - Any text content in the resume
    """
    # Parse skills from comma-separated string
    skills_list = None
    if skills:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]

    # Call the advanced search service
    result = resume_service.advanced_search(
        query=q,
        seniority=seniority,
        skills=skills_list,
        school=school,
        min_experience=min_experience,
        max_experience=max_experience,
        page=page,
        limit=limit
    )

    # Convert ResumeInDB objects to dicts for JSON serialization
    result["results"] = [resume.model_dump() for resume in result["results"]]

    return result


@router.get("/projects")
async def get_projects_with_links(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(20, ge=1, le=100, description="Projects per page (max 100)")
):
    """
    Get all projects that have links (GitHub, websites, etc.) with pagination

    Only returns projects with a non-empty URL field.
    Each project includes the resume owner's information for context.

    Example queries:
    - /api/resumes/projects?page=1&limit=20
    - /api/resumes/projects?page=2&limit=50

    Returns:
        Paginated list of projects with links, including owner information
    """
    print(f"DEBUG: Received request with page={page}, limit={limit}")
    result = project_service.get_projects_with_links(page=page, limit=limit)
    print(f"DEBUG: Service returned: {type(result)}")
    print(f"DEBUG: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    print(f"DEBUG: Number of projects: {len(result.get('projects', [])) if isinstance(result, dict) else 'N/A'}")
    return result


@router.get("/{resume_id}", response_model=ResumeInDB)
async def get_resume(resume_id: UUID):
    """
    Get a single resume by ID

    Args:
        resume_id: UUID of the resume

    Returns:
        Resume object with all fields
    """
    resume = resume_service.get_resume_by_id(resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume with ID {resume_id} not found")

    return resume


@router.get("/")
async def list_resumes(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of resumes to return"),
    offset: int = Query(0, ge=0, description="Number of resumes to skip"),
):
    """
    List all resumes with pagination

    For searching with filters, use /search endpoint instead
    """
    resumes = resume_service.list_resumes(limit=limit, offset=offset)

    return {
        "results": [resume.model_dump() for resume in resumes],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": len(resumes)
        }
    }
