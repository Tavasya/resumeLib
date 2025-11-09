"""
Resume Builder API routes
Handles resume builder creation, saving, PDF generation, and management
"""
from fastapi import APIRouter, HTTPException, Depends

from api.auth import get_user_id
from services.resume_builder_service import resume_builder_service
from models.resume_builder import (
    CreateBuilderResumeRequest,
    CreateBuilderResumeResponse,
    SaveBuilderContentRequest,
    SaveBuilderContentResponse,
    GeneratePDFRequest,
    GeneratePDFResponse,
    GetBuilderContentResponse,
    DeleteBuilderResumeResponse
)

router = APIRouter()


@router.post("/create", response_model=CreateBuilderResumeResponse)
async def create_builder_resume(
    request: CreateBuilderResumeRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Create a new builder resume

    Creates an empty resume entry that can be populated with Editor.js content

    Args:
        request: CreateBuilderResumeRequest with optional title
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        CreateBuilderResumeResponse with resume_id
    """
    try:
        result = resume_builder_service.create_builder_resume(
            user_id=user_id,
            title=request.title
        )

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to create resume"))

        return CreateBuilderResumeResponse(
            success=True,
            resume_id=result["resume_id"],
            title=result["title"],
            message="Resume created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating builder resume: {e}")
        return CreateBuilderResumeResponse(
            success=False,
            error=str(e)
        )


@router.put("/{resume_id}/save", response_model=SaveBuilderContentResponse)
async def save_builder_content(
    resume_id: str,
    request: SaveBuilderContentRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Save Editor.js content for a builder resume

    Saves the Editor.js output data to the database and storage

    Args:
        resume_id: UUID of the resume
        request: SaveBuilderContentRequest with editor_data and title
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        SaveBuilderContentResponse with success status
    """
    try:
        result = resume_builder_service.save_builder_content(
            resume_id=resume_id,
            user_id=user_id,
            editor_data=request.editor_data,
            title=request.title
        )

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to save content"))

        return SaveBuilderContentResponse(
            success=True,
            message=result["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving builder content: {e}")
        return SaveBuilderContentResponse(
            success=False,
            error=str(e)
        )


@router.post("/{resume_id}/generate-pdf", response_model=GeneratePDFResponse)
async def generate_pdf(
    resume_id: str,
    request: GeneratePDFRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Generate PDF from HTML provided by frontend

    Frontend renders Editor.js blocks to styled HTML.
    Backend just converts HTML to PDF using WeasyPrint.

    Args:
        resume_id: UUID of the resume
        request: GeneratePDFRequest with complete HTML
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GeneratePDFResponse with file_url
    """
    try:
        result = resume_builder_service.generate_pdf(
            resume_id=resume_id,
            user_id=user_id,
            html=request.html
        )

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Failed to generate PDF"))

        return GeneratePDFResponse(
            success=True,
            file_url=result["file_url"],
            message=result["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return GeneratePDFResponse(
            success=False,
            error=str(e)
        )


@router.get("/{resume_id}", response_model=GetBuilderContentResponse)
async def get_builder_content(
    resume_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get saved builder content for editing

    Retrieves the Editor.js content for a resume so it can be loaded in the editor

    Args:
        resume_id: UUID of the resume
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GetBuilderContentResponse with editor_data
    """
    try:
        result = resume_builder_service.get_builder_content(
            resume_id=resume_id,
            user_id=user_id
        )

        if not result["success"]:
            raise HTTPException(404, result.get("error", "Resume not found"))

        return GetBuilderContentResponse(
            success=True,
            resume_id=result["resume_id"],
            title=result["title"],
            editor_data=result["editor_data"],
            file_url=result.get("file_url")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting builder content: {e}")
        return GetBuilderContentResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{resume_id}", response_model=DeleteBuilderResumeResponse)
async def delete_builder_resume(
    resume_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Delete a builder resume

    Deletes the resume and all associated files from storage

    Args:
        resume_id: UUID of the resume
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        DeleteBuilderResumeResponse with success status
    """
    try:
        result = resume_builder_service.delete_builder_resume(
            resume_id=resume_id,
            user_id=user_id
        )

        if not result["success"]:
            raise HTTPException(404, result.get("error", "Resume not found"))

        return DeleteBuilderResumeResponse(
            success=True,
            message=result["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting builder resume: {e}")
        return DeleteBuilderResumeResponse(
            success=False,
            error=str(e)
        )
