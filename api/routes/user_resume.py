"""
User Resume API routes
Handles user resume uploads and comparisons with database resumes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
import tempfile
import os
from pathlib import Path

from api.auth import get_current_user, get_user_id
from services.resume_service import resume_service
from services.comparison_service import comparison_service
from config import supabase

router = APIRouter()


class CompareRequest(BaseModel):
    """Request body for comparing resumes"""
    resume_id: str  # UUID of the database resume to compare with


class UploadResponse(BaseModel):
    """Response for resume upload"""
    success: bool
    message: str
    file_url: Optional[str] = None


class WhatToWriteInstead(BaseModel):
    """Pair of original text and improved version"""
    original: str
    improved: str


class CompareResponse(BaseModel):
    """Response for resume comparison"""
    success: bool
    overall_match_score: Optional[int] = None
    user_resume_ats_score: Optional[int] = None
    db_resume_ats_score: Optional[int] = None
    what_to_write_instead: Optional[List[WhatToWriteInstead]] = None
    whats_working: Optional[List[str]] = None
    what_needs_work: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    db_resume_name: Optional[str] = None
    error: Optional[str] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_user_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Upload and save user's resume to their profile

    Requires authentication via Clerk JWT token

    Args:
        file: Resume file (PDF, DOCX, DOC, or TXT)
        user_id: User ID from Clerk JWT (injected by dependency)

    Returns:
        UploadResponse with success status and file URL
    """
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_extension} not supported. Please upload PDF, DOCX, DOC, or TXT"
            )

        # Read file content
        file_content = await file.read()

        # Generate storage path: user_id/resume.ext
        storage_path = f"{user_id}/resume{file_extension}"

        # Determine content type
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
        }
        content_type = content_types.get(file_extension, "application/octet-stream")

        # Upload to Supabase Storage (user-resumes bucket)
        supabase.storage.from_("user-resumes").upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # Get the public URL
        file_url = supabase.storage.from_("user-resumes").get_public_url(storage_path)

        # Update user record with resume URL
        supabase.table("users").update({
            "user_resume_url": file_url
        }).eq("clerk_user_id", user_id).execute()

        return UploadResponse(
            success=True,
            message="Resume uploaded successfully",
            file_url=file_url
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume: {str(e)}"
        )


@router.post("/compare", response_model=CompareResponse)
async def compare_user_resume(
    request: CompareRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Compare user's saved resume with a database resume

    Requires authentication via Clerk JWT token
    User must have previously uploaded a resume

    Args:
        request: CompareRequest with resume_id to compare against
        user_id: User ID from Clerk JWT (injected by dependency)

    Returns:
        CompareResponse with AI analysis of the differences
    """
    try:
        # Get user's resume URL from database
        user_result = supabase.table("users").select("user_resume_url").eq("clerk_user_id", user_id).single().execute()

        if not user_result.data or not user_result.data.get("user_resume_url"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No resume found. Please upload your resume first using /upload endpoint"
            )

        user_resume_url = user_result.data["user_resume_url"]

        # Download user's resume from storage
        # Extract path from URL (format: .../user-resumes/user_id/resume.ext)
        storage_path = user_resume_url.split("/user-resumes/")[-1]
        user_resume_bytes = supabase.storage.from_("user-resumes").download(storage_path)

        # Save to temp file and extract text
        file_extension = Path(storage_path).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(user_resume_bytes)
            temp_file_path = temp_file.name

        try:
            # Extract text from user's resume
            user_resume_text = _extract_text_from_file(temp_file_path, file_extension.lstrip('.'))

            if not user_resume_text or len(user_resume_text.strip()) < 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not extract sufficient text from your resume"
                )
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        # Get the database resume
        db_resume = resume_service.get_resume_by_id(UUID(request.resume_id))

        if not db_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database resume not found: {request.resume_id}"
            )

        if not db_resume.raw_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database resume does not have text content available"
            )

        # Compare the resumes using OpenAI
        result = comparison_service.compare_resumes(
            user_resume_text=user_resume_text,
            db_resume_text=db_resume.raw_text,
            db_resume_name=db_resume.name or "Unknown"
        )

        if not result or not result.get("success"):
            return CompareResponse(
                success=False,
                error=result.get("error", "Failed to compare resumes")
            )

        analysis_data = result.get("analysis", {})

        # Convert what_to_write_instead to proper model objects
        what_to_write_instead = []
        for item in analysis_data.get("what_to_write_instead", []):
            what_to_write_instead.append(WhatToWriteInstead(
                original=item.get("original", ""),
                improved=item.get("improved", "")
            ))

        return CompareResponse(
            success=True,
            overall_match_score=analysis_data.get("overall_match_score"),
            user_resume_ats_score=analysis_data.get("user_resume_ats_score"),
            db_resume_ats_score=analysis_data.get("db_resume_ats_score"),
            what_to_write_instead=what_to_write_instead,
            whats_working=analysis_data.get("whats_working", []),
            what_needs_work=analysis_data.get("what_needs_work", []),
            next_steps=analysis_data.get("next_steps", []),
            db_resume_name=result.get("db_resume_name")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error comparing resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare resumes: {str(e)}"
        )


def _extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extract text from a file

    Args:
        file_path: Path to the file
        file_type: Type of file (pdf, docx, doc, txt)

    Returns:
        Extracted text
    """
    import PyPDF2
    import docx

    try:
        if file_type == 'pdf':
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()

        elif file_type in ['docx', 'doc']:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + "\n"
            return text.strip()

        elif file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        else:
            return ""

    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""
