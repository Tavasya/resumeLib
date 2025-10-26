"""
Anonymizer API routes
Handles PDF upload, PII detection, and anonymization preferences
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import tempfile
import os
import uuid

from api.auth import get_user_id
from services.anonymizer_service import anonymizer_service
from models.anonymizer import (
    DetectPIIResponse,
    PIIDetection,
    SaveAnonymizedRequest,
    SaveAnonymizedResponse,
    GenerateAnonymizedPDFRequest,
    GenerateAnonymizedPDFResponse
)
from config import supabase

router = APIRouter()


@router.post("/detect-pii", response_model=DetectPIIResponse)
async def detect_pii(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Upload PDF and detect PII locations

    Returns coordinates of all detected personal information

    Args:
        file: PDF file to analyze
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        DetectPIIResponse with detected PII and coordinates
    """
    try:
        # Validate PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are supported")

        # Read file
        file_content = await file.read()

        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
            temp.write(file_content)
            temp_path = temp.name

        try:
            # Upload original to Supabase storage
            file_id = str(uuid.uuid4())
            storage_path = f"{user_id}/anonymizer/{file_id}.pdf"

            print(f"📤 Uploading PDF to Supabase:")
            print(f"   File ID: {file_id}")
            print(f"   User ID: {user_id}")
            print(f"   Storage path: {storage_path}")
            print(f"   File size: {len(file_content)} bytes")

            upload_result = supabase.storage.from_("anonymized-resumes").upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

            print(f"✅ Upload successful: {upload_result}")

            original_url = supabase.storage.from_("anonymized-resumes").get_public_url(storage_path)
            print(f"📎 Public URL: {original_url}")

            # Detect PII with coordinates
            result = anonymizer_service.detect_pii_with_coordinates(temp_path)

            if not result["success"]:
                raise HTTPException(500, result.get("error", "PII detection failed"))

            return DetectPIIResponse(
                success=True,
                file_id=file_id,
                original_url=original_url,
                detections=result["detections"],
                total_pages=result["total_pages"]
            )

        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

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


@router.post("/save-anonymized", response_model=SaveAnonymizedResponse)
async def save_anonymized_resume(
    request: SaveAnonymizedRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Save user's anonymization preferences to database

    Stores which fields should be blurred

    Args:
        request: SaveAnonymizedRequest with file_id and detections
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        SaveAnonymizedResponse with success status
    """
    try:
        # Store in Supabase database
        supabase.table("anonymized_resumes").insert({
            "user_id": user_id,
            "file_id": request.file_id,
            "pii_detections": [d.model_dump() for d in request.detections],
        }).execute()

        return SaveAnonymizedResponse(
            success=True,
            message="Anonymization preferences saved successfully"
        )

    except Exception as e:
        print(f"Error saving anonymized resume: {e}")
        return SaveAnonymizedResponse(
            success=False,
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
        # Download original PDF from Supabase
        original_path = f"{user_id}/anonymizer/{request.file_id}.pdf"

        try:
            pdf_bytes = supabase.storage.from_("anonymized-resumes").download(original_path)
        except Exception as e:
            raise HTTPException(404, f"Original PDF not found: {str(e)}")

        # Generate anonymized PDF
        replacements = [r.model_dump() for r in request.replacements]
        result = anonymizer_service.generate_anonymized_pdf(pdf_bytes, replacements)

        if not result["success"]:
            raise HTTPException(500, f"PDF generation failed: {result.get('error')}")

        # Upload anonymized PDF to Supabase
        anonymized_path = f"{user_id}/anonymizer/{request.file_id}_anonymized.pdf"

        supabase.storage.from_("anonymized-resumes").upload(
            path=anonymized_path,
            file=result["pdf_bytes"],
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )

        # Get public URLs
        anonymized_url = supabase.storage.from_("anonymized-resumes").get_public_url(anonymized_path)
        original_url = supabase.storage.from_("anonymized-resumes").get_public_url(original_path)

        return GenerateAnonymizedPDFResponse(
            success=True,
            anonymized_url=anonymized_url,
            original_url=original_url
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating anonymized PDF: {e}")
        return GenerateAnonymizedPDFResponse(
            success=False,
            error=str(e)
        )
