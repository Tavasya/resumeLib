"""
Comparison service for analyzing user resumes against database resumes
"""
from typing import Optional, Dict, Any
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
                        "content": "You are an expert resume analyst and career coach. Your job is to compare resumes and provide actionable feedback on why one resume is more effective than another."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
            )

            # Get the analysis
            analysis = response.choices[0].message.content

            return {
                "success": True,
                "analysis": analysis,
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
        prompt = f"""I need you to compare two resumes and explain why the reference resume is more effective.

**Reference Resume (by {db_resume_name}):**
```
{db_resume_text}
```

**User's Resume:**
```
{user_resume_text}
```

Please analyze both resumes and provide a detailed comparison covering:

1. **Overall Structure & Formatting**: How does the reference resume's structure make it more readable and impactful?

2. **Content Quality**:
   - How are accomplishments described differently?
   - What makes the reference resume's descriptions more compelling?
   - Are there specific metrics or results highlighted?

3. **Key Strengths of Reference Resume**: What specific elements make this resume stand out?

4. **Areas Where User's Resume Falls Short**: Be specific about what's missing or could be improved.

5. **Actionable Recommendations**: Give 3-5 concrete suggestions for how the user can improve their resume based on what works in the reference resume.

Please be constructive, specific, and focus on helping the user understand what makes an effective resume."""

        return prompt


# Global service instance
comparison_service = ComparisonService()
