"""
ATS Checker service for analyzing resume compatibility
"""
import os
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config import settings


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
