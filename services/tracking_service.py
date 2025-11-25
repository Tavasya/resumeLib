"""
Service for tracking analytics events
"""
from typing import Optional
from config import supabase


class TrackingService:
    """Service for analytics tracking"""

    def track_ats_check(
        self,
        user_id: str,
        score: int,
        resume_source: Optional[str] = None,
        user_resume_id: Optional[str] = None,
        submission_id: Optional[str] = None,
        has_job_description: bool = False
    ) -> None:
        """
        Track ATS checker usage in the database

        Args:
            user_id: Clerk user ID
            score: ATS score from analysis
            resume_source: Source type ('builder', 'upload', 'submission', 'new_file')
            user_resume_id: Optional resume ID from user_resumes
            submission_id: Optional submission ID from review_submissions
            has_job_description: Whether job description was provided
        """
        try:
            supabase.table("ats_checks").insert({
                "user_id": user_id,
                "resume_source": resume_source,
                "user_resume_id": user_resume_id,
                "submission_id": submission_id,
                "has_job_description": has_job_description,
                "score": score
            }).execute()
            print(f"✅ Tracked ATS check: user={user_id}, source={resume_source}, score={score}")
        except Exception as e:
            # Don't fail the request if tracking fails
            print(f"⚠️  Failed to track ATS check: {e}")


# Global instance
tracking_service = TrackingService()
