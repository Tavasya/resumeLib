"""
Anonymizer API routes
Handles PDF upload, PII detection, and anonymization preferences
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import uuid

from api.auth import get_user_id
from services.anonymizer_service import anonymizer_service
from services.storage_service import storage_service
from models.anonymizer import (
    DetectPIIRequest,
    DetectPIIResponse,
    PIIDetection,
    GenerateAnonymizedPDFRequest,
    GenerateAnonymizedPDFResponse,
    SaveSessionRequest,
    SaveSessionResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    SessionSummary,
    SessionDetail,
    CreateShareLinkRequest,
    CreateShareLinkResponse,
    SharedSessionResponse
)
from config import supabase, settings

router = APIRouter()


@router.post("/detect-pii", response_model=DetectPIIResponse)
async def detect_pii(
    request: DetectPIIRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Detect PII in user's resume

    Returns coordinates of all detected personal information

    Args:
        request: DetectPIIRequest with user_resume_id
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        DetectPIIResponse with detected PII and coordinates
    """
    try:
        print(f"📄 Processing PDF for PII detection:")
        print(f"   User Resume ID: {request.user_resume_id}")
        print(f"   User ID: {user_id}")

        # Get the user resume from database
        resume_result = supabase.table("user_resumes")\
            .select("id, filename, file_url, storage_path")\
            .eq("id", request.user_resume_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not resume_result.data:
            raise HTTPException(404, "Resume not found or access denied")

        resume = resume_result.data

        # Validate PDF
        if not resume["filename"].lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are supported for anonymization")

        # Download the original file from storage
        file_content = supabase.storage.from_("user-resumes").download(resume["storage_path"])

        print(f"   File size: {len(file_content)} bytes")

        # Process PDF from memory (no temp file needed)
        result = anonymizer_service.detect_pii_with_coordinates(file_content)

        if not result["success"]:
            print(f"❌ PII detection failed: {result.get('error')}")
            raise HTTPException(500, result.get("error", "PII detection failed"))

        print(f"✅ PII detection successful: {len(result['detections'])} detections found")

        # Return using the existing user_resume_id (no new upload needed)
        return DetectPIIResponse(
            success=True,
            file_id=request.user_resume_id,  # Use resume ID as file_id for consistency
            original_url=resume["file_url"],
            detections=result["detections"],
            total_pages=result["total_pages"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in detect_pii: {e}")
        return DetectPIIResponse(
            success=False,
            file_id="",
            original_url="",
            detections=[],
            total_pages=0,
            error=str(e)
        )


@router.post("/generate-anonymized-pdf", response_model=GenerateAnonymizedPDFResponse)
async def generate_anonymized_pdf(
    request: GenerateAnonymizedPDFRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Generate a new PDF with text replacements applied

    Takes the original PDF and applies user-specified text replacements
    to create an anonymized version

    Args:
        request: GenerateAnonymizedPDFRequest with file_id and replacements
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        GenerateAnonymizedPDFResponse with download URLs
    """
    try:
        # Get the user resume from database (file_id is actually user_resume_id)
        resume_result = supabase.table("user_resumes")\
            .select("id, file_url, storage_path")\
            .eq("id", request.file_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not resume_result.data:
            raise HTTPException(404, "Resume not found or access denied")

        resume = resume_result.data

        # Download original PDF from user-resumes bucket
        try:
            pdf_bytes = supabase.storage.from_("user-resumes").download(resume["storage_path"])
        except Exception as e:
            raise HTTPException(404, f"Original PDF not found: {str(e)}")

        # Generate anonymized PDF
        replacements = [r.model_dump() for r in request.replacements]
        result = anonymizer_service.generate_anonymized_pdf(pdf_bytes, replacements)

        if not result["success"]:
            raise HTTPException(500, f"PDF generation failed: {result.get('error')}")

        # Generate unique session ID for this anonymization
        session_id = str(uuid.uuid4())

        # Upload anonymized PDF to Supabase under the resume's folder
        anonymized_path = f"{user_id}/{request.file_id}/anonymized/{session_id}_anonymized.pdf"

        anonymized_url = storage_service.upload_file(
            bucket_name="user-resumes",
            storage_path=anonymized_path,
            file_content=result["pdf_bytes"],
            content_type="application/pdf"
        )

        return GenerateAnonymizedPDFResponse(
            success=True,
            anonymized_url=anonymized_url,
            original_url=resume["file_url"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating anonymized PDF: {e}")
        return GenerateAnonymizedPDFResponse(
            success=False,
            error=str(e)
        )


@router.post("/save-session", response_model=SaveSessionResponse)
async def save_session(
    request: SaveSessionRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Save or update an anonymizer session

    Stores all detection data, blur states, replacement text, and manual blurs
    for a specific file. If a session already exists for this user+file_id,
    it will be updated (upsert behavior).

    Args:
        request: SaveSessionRequest with file_id, filename, detections, manual_blurs, num_pages
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        SaveSessionResponse with session_id
    """
    try:
        # Get the user resume from database (file_id is actually user_resume_id)
        resume_result = supabase.table("user_resumes")\
            .select("id, filename, file_url")\
            .eq("id", request.file_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not resume_result.data:
            raise HTTPException(404, "Resume not found or access denied")

        resume = resume_result.data

        # Convert detections and manual_blurs to JSON
        detections_json = [d.model_dump() for d in request.detections]
        manual_blurs_json = [mb.model_dump() for mb in request.manual_blurs]

        # Check if session already exists for this user+file_id
        existing = supabase.table("anonymizer_sessions").select("id").eq(
            "user_id", user_id
        ).eq("file_id", request.file_id).execute()

        if existing.data and len(existing.data) > 0:
            # Update existing session
            session_id = existing.data[0]["id"]
            result = supabase.table("anonymizer_sessions").update({
                "filename": resume["filename"],
                "detections": detections_json,
                "manual_blurs": manual_blurs_json,
                "num_pages": request.num_pages,
                "updated_at": "NOW()"
            }).eq("id", session_id).execute()

            message = "Session updated successfully"
        else:
            # Create new session with FK link
            result = supabase.table("anonymizer_sessions").insert({
                "user_id": user_id,
                "file_id": request.file_id,
                "user_resume_id": request.file_id,  # Set FK
                "filename": resume["filename"],
                "original_url": resume["file_url"],
                "detections": detections_json,
                "manual_blurs": manual_blurs_json,
                "num_pages": request.num_pages
            }).execute()

            session_id = result.data[0]["id"]
            message = "Session saved successfully"

        return SaveSessionResponse(
            success=True,
            session_id=str(session_id),
            message=message
        )

    except Exception as e:
        print(f"Error saving session: {e}")
        return SaveSessionResponse(
            success=False,
            error=str(e)
        )


@router.get("/sessions", response_model=ListSessionsResponse)
async def list_sessions(
    user_id: str = Depends(get_user_id)
):
    """
    List all anonymizer sessions for the current user

    Returns summary information for each session (no full detection data)

    Args:
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        ListSessionsResponse with array of session summaries
    """
    try:
        # Get all sessions for this user, ordered by updated_at descending
        result = supabase.table("anonymizer_sessions").select(
            "id, file_id, filename, original_url, num_pages, created_at, updated_at"
        ).eq("user_id", user_id).order("updated_at", desc=True).execute()

        sessions = []
        for row in result.data:
            sessions.append(SessionSummary(
                session_id=str(row["id"]),
                file_id=row["file_id"],
                filename=row["filename"],
                original_url=row["original_url"],
                num_pages=row["num_pages"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))

        return ListSessionsResponse(
            success=True,
            sessions=sessions
        )

    except Exception as e:
        print(f"Error listing sessions: {e}")
        return ListSessionsResponse(
            success=False,
            error=str(e)
        )


@router.get("/sessions/{session_id}", response_model=LoadSessionResponse)
async def load_session(
    session_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Load a specific anonymizer session with full data

    Returns all detection data, blur states, replacement text, and manual blurs

    Args:
        session_id: UUID of the session to load
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        LoadSessionResponse with full session details
    """
    try:
        # Get session by ID and verify it belongs to this user
        result = supabase.table("anonymizer_sessions").select("*").eq(
            "id", session_id
        ).eq("user_id", user_id).single().execute()

        if not result.data:
            raise HTTPException(404, "Session not found or access denied")

        row = result.data

        session = SessionDetail(
            session_id=str(row["id"]),
            file_id=row["file_id"],
            filename=row["filename"],
            original_url=row["original_url"],
            detections=row["detections"],
            manual_blurs=row["manual_blurs"],
            num_pages=row["num_pages"]
        )

        return LoadSessionResponse(
            success=True,
            session=session
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading session: {e}")
        return LoadSessionResponse(
            success=False,
            error=str(e)
        )


@router.post("/create-share-link", response_model=CreateShareLinkResponse)
async def create_share_link(
    request: CreateShareLinkRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Create a shareable link for an anonymizer session using readable slug

    Generates a human-readable slug from the filename (e.g., "johns-resume-x7k9")
    that can be shared publicly.

    Args:
        request: CreateShareLinkRequest with session_id
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        CreateShareLinkResponse with share_token (slug) and share_url
    """
    try:
        # Verify the session exists and belongs to this user
        result = supabase.table("anonymizer_sessions").select("id, filename").eq(
            "id", request.session_id
        ).eq("user_id", user_id).single().execute()

        if not result.data:
            raise HTTPException(404, "Session not found or access denied")

        filename = result.data["filename"]

        # Generate slug from filename
        import re
        import secrets

        # Remove file extension and sanitize
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # Replace spaces and special chars with hyphens, lowercase
        slug_base = re.sub(r'[^a-zA-Z0-9]+', '-', base_name).lower().strip('-')
        # Limit length
        slug_base = slug_base[:50]

        # Add random suffix for uniqueness
        random_suffix = secrets.token_urlsafe(4)[:6].lower().replace('_', '').replace('-', '')
        share_slug = f"{slug_base}-{random_suffix}"

        # Update the session with the share_slug
        supabase.table("anonymizer_sessions").update({
            "share_slug": share_slug
        }).eq("id", request.session_id).execute()

        # Build the share URL
        share_url = f"{settings.FRONTEND_URL}/share/{share_slug}"

        return CreateShareLinkResponse(
            success=True,
            share_token=share_slug,
            share_url=share_url
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating share link: {e}")
        return CreateShareLinkResponse(
            success=False,
            error=str(e)
        )


@router.get("/share/{slug}", response_model=SharedSessionResponse)
async def get_shared_session(slug: str):
    """
    Get session data from a share slug (PUBLIC - no auth required)

    Looks up the session by readable slug and returns the session data
    in read-only mode for viewing.

    Args:
        slug: Human-readable slug (e.g., "johns-resume-x7k9")

    Returns:
        SharedSessionResponse with session data
    """
    try:
        # Get session data from database by share_slug
        result = supabase.table("anonymizer_sessions").select("*").eq(
            "share_slug", slug
        ).single().execute()

        if not result.data:
            raise HTTPException(404, "Shared session not found")

        row = result.data

        # Build session detail
        session = SessionDetail(
            session_id=str(row["id"]),
            file_id=row["file_id"],
            filename=row["filename"],
            original_url=row["original_url"],
            detections=row["detections"],
            manual_blurs=row["manual_blurs"],
            num_pages=row["num_pages"]
        )

        return SharedSessionResponse(
            success=True,
            session=session
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading shared session: {e}")
        return SharedSessionResponse(
            success=False,
            error=str(e)
        )
