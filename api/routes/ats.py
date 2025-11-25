"""
ATS Checker API routes
Handles resume ATS compatibility analysis
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
import PyPDF2
import io

from api.auth import get_user_id
from services.ats_service import ats_service
from services.review_service import review_service
from models.ats import ATSAnalyzeResponse, ATSSuggestion

router = APIRouter()


@router.post("/analyze", response_model=ATSAnalyzeResponse)
async def analyze_resume(
    file: Optional[UploadFile] = File(None),
    existing_submission_id: Optional[str] = Form(None),
    existing_resume_id: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    user_id: str = Depends(get_user_id)
):
    """
    Analyze resume for ATS compatibility

    Supports three input methods:
    1. Upload a new PDF file
    2. Use an existing review submission (from review_submissions table)
    3. Use an existing resume (from user_resumes table - supports builder resumes!)

    Args:
        file: Optional PDF resume file (if uploading new)
        existing_submission_id: Optional ID of existing review submission
        existing_resume_id: Optional ID of existing resume from user_resumes (supports builder resumes)
        job_description: Optional job description to compare against
        user_id: Authenticated user ID from Clerk JWT

    Returns:
        ATSAnalyzeResponse with score and suggestions
    """
    try:
        resume_text = None

        # Option 1: Use existing resume from user_resumes (supports builder resumes!)
        if existing_resume_id:
            print(f"📄 Using existing resume from user_resumes: {existing_resume_id}")

            # Fetch and extract text from resume
            result = ats_service.get_resume_text_from_user_resume(existing_resume_id, user_id)

            if not result["success"]:
                raise HTTPException(404, result.get("error", "Failed to fetch resume"))

            resume_text = result["resume_text"]

        # Option 2: Use existing submission
        elif existing_submission_id:
            print(f"📄 Using existing submission: {existing_submission_id}")

            # Get submission details
            submission = review_service.get_submission(existing_submission_id, user_id)

            if not submission["success"]:
                raise HTTPException(404, "Submission not found or access denied")

            # Download the PDF from the file URL
            import requests
            file_url = submission["submission"]["file_url"]
            response = requests.get(file_url)
            response.raise_for_status()

            # Extract text from PDF
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            resume_text = ""
            for page in pdf_reader.pages:
                resume_text += page.extract_text() + "\n"

        # Option 2: Use uploaded file
        elif file:
            print(f"📄 Using uploaded file: {file.filename}")

            # Validate PDF
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(400, "Only PDF files are supported")

            # Read file content
            file_content = await file.read()

            # Extract text from PDF
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            resume_text = ""
            for page in pdf_reader.pages:
                resume_text += page.extract_text() + "\n"

        else:
            raise HTTPException(400, "Either file, existing_submission_id, or existing_resume_id is required")

        if not resume_text or not resume_text.strip():
            raise HTTPException(400, "Could not extract text from resume PDF")

        print(f"📊 Analyzing resume (length: {len(resume_text)} chars)")
        if job_description:
            print(f"   Job description provided (length: {len(job_description)} chars)")

        # Analyze the resume
        result = ats_service.analyze_resume(
            resume_text=resume_text,
            job_description=job_description
        )

        if not result["success"]:
            raise HTTPException(500, result.get("error", "Analysis failed"))

        print(f"✅ Analysis complete: Score {result['score']}, {len(result['suggestions'])} suggestions")

        # Convert suggestions to Pydantic models
        suggestions = [
            ATSSuggestion(**suggestion)
            for suggestion in result["suggestions"]
        ]

        return ATSAnalyzeResponse(
            success=True,
            score=result["score"],
            suggestions=suggestions
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing resume: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to analyze resume: {str(e)}")
