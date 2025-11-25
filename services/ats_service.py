"""
ATS Checker service for analyzing resume compatibility
"""
import os
import re
import io
from typing import Dict, Any, List, Optional
from openai import OpenAI
import PyPDF2
import requests
from config import settings, supabase


class ATSService:
    """Service for ATS resume analysis"""

    def __init__(self):
        self.client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self.client is None:
            api_key = settings.OPENAI_API_KEY
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                raise ValueError("OPENAI_API_KEY not configured")
        return self.client

    def get_resume_text_from_user_resume(
        self,
        resume_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Fetch a resume from user_resumes table and extract text

        Args:
            resume_id: UUID of resume in user_resumes table
            user_id: Clerk user ID for ownership verification

        Returns:
            Dictionary with success status and resume_text
        """
        try:
            # Fetch resume from database
            result = supabase.table("user_resumes")\
                .select("id, filename, file_url, resume_source, builder_content")\
                .eq("id", resume_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if not result.data:
                return {
                    "success": False,
                    "error": "Resume not found or access denied"
                }

            resume_data = result.data
            resume_source = resume_data.get("resume_source")
            file_url = resume_data.get("file_url")
            builder_content = resume_data.get("builder_content")

            resume_text = None

            # Option 1: Resume has a PDF (either uploaded or builder with generated PDF)
            if file_url:
                print(f"📄 Extracting text from PDF: {file_url}")

                # Download the PDF
                response = requests.get(file_url)
                response.raise_for_status()

                # Extract text from PDF
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                resume_text = ""
                for page in pdf_reader.pages:
                    resume_text += page.extract_text() + "\n"

            # Option 2: Builder resume without PDF - extract from JSON
            elif resume_source == "builder" and builder_content:
                print(f"📄 Extracting text from builder content JSON")
                resume_text = self.extract_text_from_builder_content(builder_content)

            else:
                return {
                    "success": False,
                    "error": "Resume has no PDF or builder content to analyze"
                }

            if not resume_text or not resume_text.strip():
                return {
                    "success": False,
                    "error": "Could not extract text from resume"
                }

            return {
                "success": True,
                "resume_text": resume_text
            }

        except Exception as e:
            print(f"❌ Error fetching resume: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def analyze_resume(
        self,
        resume_text: str,
        job_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze resume for ATS compatibility

        Args:
            resume_text: Extracted text from resume
            job_description: Optional job description to compare against

        Returns:
            Dictionary with score and suggestions
        """
        try:
            # Get OpenAI client (lazy initialization)
            client = self._get_client()

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(resume_text, job_description)

            # Call OpenAI to analyze
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ATS (Applicant Tracking System) analyzer. Analyze resumes for ATS compatibility and provide actionable suggestions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            # Parse the response
            result = response.choices[0].message.content
            print(f"🤖 OpenAI Response: {result[:200]}...")

            import json
            analysis = json.loads(result)

            print(f"✅ Parsed analysis: Score={analysis.get('score')}, Suggestions={len(analysis.get('suggestions', []))}")

            return {
                "success": True,
                "score": analysis.get("score", 0),
                "suggestions": analysis.get("suggestions", [])
            }

        except Exception as e:
            print(f"❌ Error analyzing resume: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "score": 0,
                "suggestions": []
            }

    def extract_text_from_builder_content(self, builder_content: Dict[str, Any]) -> str:
        """
        Extract plain text from Editor.js builder content JSON

        Args:
            builder_content: Editor.js JSON content

        Returns:
            Extracted plain text from all blocks
        """
        try:
            if not builder_content or not isinstance(builder_content, dict):
                return ""

            blocks = builder_content.get("blocks", [])
            if not blocks:
                return ""

            text_parts = []

            for block in blocks:
                block_type = block.get("type", "")
                data = block.get("data", {})

                # Extract text based on block type
                if block_type == "paragraph":
                    text = data.get("text", "")
                    if text:
                        text_parts.append(text)

                elif block_type == "header":
                    text = data.get("text", "")
                    if text:
                        text_parts.append(text)

                elif block_type == "list":
                    items = data.get("items", [])
                    for item in items:
                        if item:
                            text_parts.append(f"• {item}")

                elif block_type == "table":
                    content = data.get("content", [])
                    for row in content:
                        if isinstance(row, list):
                            text_parts.append(" | ".join(str(cell) for cell in row))

                elif block_type == "quote":
                    text = data.get("text", "")
                    if text:
                        text_parts.append(text)

                elif block_type == "code":
                    code = data.get("code", "")
                    if code:
                        text_parts.append(code)

                elif block_type == "delimiter":
                    text_parts.append("---")

                # For any other block type with a text field
                elif "text" in data:
                    text = data.get("text", "")
                    if text:
                        text_parts.append(text)

            # Join all text parts with newlines
            result = "\n\n".join(text_parts)

            # Clean up HTML tags if present (Editor.js sometimes includes inline HTML)
            result = re.sub(r'<[^>]+>', '', result)

            return result.strip()

        except Exception as e:
            print(f"❌ Error extracting text from builder content: {str(e)}")
            return ""

    def _build_analysis_prompt(self, resume_text: str, job_description: Optional[str]) -> str:
        """Build the prompt for OpenAI analysis"""

        base_prompt = f"""Analyze this resume for ATS (Applicant Tracking System) compatibility.

Resume:
{resume_text}
"""

        if job_description:
            base_prompt += f"""
Job Description:
{job_description}

Please compare the resume against this job description and identify:
1. Missing keywords and skills from the job description
2. Matching qualifications
3. Gaps in experience or requirements
"""

        base_prompt += """
Provide your analysis in JSON format with:
- score: Overall ATS compatibility score from 0-100
- suggestions: Array of suggestion objects with:
  - category: "critical", "warning", "success", or "info"
  - title: Short title (e.g., "Missing Keywords", "Formatting Issues")
  - description: Detailed explanation

Focus on:
- Keywords and skills matching (especially if job description provided)
- Resume formatting (section headers, bullet points, dates)
- Contact information visibility
- File format compatibility
- Use of standard section names (Experience, Education, Skills)
- Avoid complex formatting (tables, columns, graphics)
- Consistent date formatting
- Action verbs and quantifiable achievements

Return ONLY valid JSON with this structure:
{
  "score": 78,
  "suggestions": [
    {
      "category": "critical",
      "title": "Missing Keywords",
      "description": "Your resume is missing key skills..."
    }
  ]
}
"""
        return base_prompt


# Global ATS service instance
ats_service = ATSService()
