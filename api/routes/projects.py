"""
Projects API routes
Handles all project-related endpoints including search
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from services.project_service import project_service

router = APIRouter()


@router.get("/search")
async def search_projects(
    q: Optional[str] = Query(None, description="Search query (searches project name and description)"),
    technologies: Optional[str] = Query(None, description="Comma-separated list of technologies (e.g., 'python,react,docker')"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Search projects with filters

    Public endpoint - no authentication required
    """
    # Parse technologies from comma-separated string
    technologies_list = None
    if technologies:
        technologies_list = [t.strip() for t in technologies.split(",") if t.strip()]

    # Call the search service
    result = project_service.search_projects(
        query=q,
        technologies=technologies_list,
        page=page,
        limit=limit
    )

    return result


@router.get("/")
async def get_projects_with_links(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(20, ge=1, le=100, description="Projects per page (max 100)")
):
    """
    Get all projects that have links (GitHub, websites, etc.) with pagination

    Public endpoint - no authentication required
    """
    result = project_service.get_projects_with_links(page=page, limit=limit)
    return result
