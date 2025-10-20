"""
LLM service for parsing resume text into structured data using OpenAI
"""
from typing import Optional, Dict, Any
import json
from openai import OpenAI
from config import settings


class LLMService:
    """Service for using LLM to parse resume text"""

    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4.1-nano"  # Fast and cheap model, good for parsing

    def parse_resume(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse resume text into structured data using OpenAI

        Args:
            raw_text: Raw text extracted from resume

        Returns:
            Dictionary with structured resume data, or None if parsing fails
        """
        try:
            # Create the prompt for OpenAI
            prompt = self._create_parsing_prompt(raw_text)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a resume parser. Extract structured information from resume text and return it as valid JSON. If information is not present, use null."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,  # Deterministic output
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Parse the response
            result = response.choices[0].message.content
            parsed_data = json.loads(result)

            return parsed_data

        except Exception as e:
            print(f"  ⚠ LLM parsing error: {e}")
            return None

    def _create_parsing_prompt(self, raw_text: str) -> str:
        """
        Create the prompt for OpenAI to parse resume

        Args:
            raw_text: Raw resume text

        Returns:
            Formatted prompt string
        """
        prompt = f"""Parse the following resume text and extract structured information. Return ONLY valid JSON with this exact structure:

{{
  "name": "Full name of the candidate (just the name, no titles or extra text)",
  "location": "City, State/Country",
  "experience": [
    {{
      "company": "Company name",
      "title": "Job title",
      "start_date": "Start date (format: YYYY-MM or Month YYYY)",
      "end_date": "End date or 'Present'",
      "description": "Exact description text from resume (verbatim, do not summarize)"
    }}
  ],
  "education": [
    {{
      "institution": "School/University name",
      "degree": "Degree name",
      "field_of_study": "Major/Field",
      "graduation_date": "Graduation date (format: YYYY or Month YYYY)"
    }}
  ],
  "projects": [
    {{
      "name": "Project name",
      "description": "Exact project description text from resume (verbatim, do not summarize)",
      "technologies": ["tech1", "tech2"],
      "url": "Project URL if available"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification name",
      "issuer": "Issuing organization",
      "date": "Date obtained"
    }}
  ]
}}

Important:
- Extract as much information as possible from the resume
- If a field is not present in the resume, use null or empty array []
- For experience and project descriptions: copy the EXACT text from the resume, do NOT summarize or paraphrase
- Format dates consistently

Resume text:
---
{raw_text}
---

Return ONLY the JSON object, no additional text or explanation."""

        return prompt


# Global LLM service instance
llm_service = LLMService()