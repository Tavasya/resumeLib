"""
Email service using Resend
"""
import os
import resend
from typing import Dict, Any


class EmailService:
    """Service for sending emails via Resend"""

    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        if self.api_key:
            resend.api_key = self.api_key

    def send_review_ready_email(
        self,
        to_email: str,
        first_name: str,
        review_url: str
    ) -> Dict[str, Any]:
        """
        Send email notification when resume review is ready

        Args:
            to_email: Recipient email address
            first_name: User's first name
            review_url: URL to view the review

        Returns:
            Dictionary with success status
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "RESEND_API_KEY not configured"
                }

            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2563eb;">Hi {first_name},</h2>

                        <p>Just a quick reminder, your resume review is ready! 🎉</p>

                        <p>You can view the feedback directly on your Review page in your Cooked Career dashboard.</p>

                        <p style="margin: 30px 0;">
                            <a href="{review_url}"
                               style="background-color: #2563eb;
                                      color: white;
                                      padding: 12px 24px;
                                      text-decoration: none;
                                      border-radius: 5px;
                                      display: inline-block;">
                                View Your Review
                            </a>
                        </p>

                        <p>If you have any questions or need further assistance, feel free to reach out, we're happy to help!</p>

                        <p style="margin-top: 30px;">
                            Best,<br>
                            <strong>Cooked Career Team</strong>
                        </p>
                    </div>
                </body>
            </html>
            """

            text_content = f"""
Hi {first_name},

Just a quick reminder, your resume review is ready! 🎉

You can view the feedback directly on your Review page in your Cooked Career dashboard:
{review_url}

If you have any questions or need further assistance, feel free to reach out, we're happy to help!

Best,
Cooked Career Team
            """

            params = {
                "from": "Cooked Career <noreply@cookedcareer.com>",
                "to": [to_email],
                "subject": "Your Resume Review is Ready! 🎉",
                "html": html_content,
                "text": text_content
            }

            response = resend.Emails.send(params)

            print(f"✅ Email sent successfully to {to_email}")
            print(f"   Email ID: {response.get('id')}")

            return {
                "success": True,
                "email_id": response.get("id")
            }

        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Global email service instance
email_service = EmailService()
