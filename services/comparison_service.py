"""
Comparison service for analyzing user resumes against database resumes
"""
from typing import Optional, Dict, Any
import json
from openai import OpenAI
from config import settings


class ComparisonService:
    """Service for comparing resumes using OpenAI"""

    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Good balance of quality and cost for analysis

    def compare_resumes(
        self,
        user_resume_text: str,
        db_resume_text: str,
        db_resume_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare user's resume with a database resume using OpenAI

        Args:
            user_resume_text: Raw text from user's uploaded resume
            db_resume_text: Raw text from database resume
            db_resume_name: Name on the database resume

        Returns:
            Dictionary with comparison analysis, or None if analysis fails
        """
        try:
            # Create the comparison prompt
            prompt = self._create_comparison_prompt(
                user_resume_text,
                db_resume_text,
                db_resume_name
            )

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume analyst and ATS (Applicant Tracking System) specialist. Analyze resumes and return structured JSON feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Parse the JSON response
            result = response.choices[0].message.content
            analysis_data = json.loads(result)

            return {
                "success": True,
                "analysis": analysis_data,
                "db_resume_name": db_resume_name
            }

        except Exception as e:
            print(f"Error comparing resumes: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _create_comparison_prompt(
        self,
        user_resume_text: str,
        db_resume_text: str,
        db_resume_name: str
    ) -> str:
        """
        Create the comparison prompt for OpenAI

        Args:
            user_resume_text: User's resume text
            db_resume_text: Database resume text
            db_resume_name: Name on database resume

        Returns:
            Formatted prompt string
        """
        prompt = f"""Compare these two resumes and provide a structured analysis. The reference resume (by {db_resume_name}) is our curated high-quality example. The user's resume needs improvement.

**Reference Resume (by {db_resume_name}):**
```
{db_resume_text}
```

**User's Resume:**
```
{user_resume_text}
```

Return ONLY valid JSON with this EXACT structure:

{{
  "overall_match_score": 75,
  "user_resume_ats_score": 65,
  "db_resume_ats_score": 95,
  "what_to_write_instead": [
    {{"original": "Responsible for managing projects", "improved": "Led 5+ cross-functional teams to deliver projects 20% ahead of schedule"}},
    {{"original": "Worked with customers", "improved": "Resolved 100+ customer issues weekly, maintaining 98% satisfaction rate"}}
  ],
  "whats_working": [
    "Clear education section with relevant coursework",
    "Consistent formatting and easy-to-read layout"
  ],
  "what_needs_work": [
    "Lack of quantifiable achievements and metrics",
    "Generic job descriptions without specific impact"
  ],
  "next_steps": [
    "Add metrics to each bullet point (percentages, numbers, timeframes)",
    "Replace passive language with strong action verbs and results"
  ]
}}

Guidelines:
- overall_match_score: 0-100 rating of how well the user's resume compares to the reference (holistic quality assessment)
- user_resume_ats_score: 0-100% ATS compatibility score for user's resume
- db_resume_ats_score: 0-100% ATS compatibility score for reference resume
- what_to_write_instead: Provide 2 examples of weak text from user's resume and strong alternatives
- whats_working: 2 things the user is doing right
- what_needs_work: 2 critical areas for improvement
- next_steps: 2 actionable next steps to improve the resume

Be specific, constructive, and focus on actionable improvements."""

        return prompt


# Global service instance
comparison_service = ComparisonService()
