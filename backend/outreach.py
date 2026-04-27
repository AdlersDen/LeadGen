"""
Module 5 — Email Outreach Engine
Sends personalized emails via SendGrid SMTP with:
  - Mandatory unsubscribe footer (PRD §6.5)
  - Bounce/delivery error handling
PRD §6.5
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "outreach@yourdomain.com")
FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Adler's Den")
UNSUBSCRIBE_URL = os.getenv("UNSUBSCRIBE_URL", "https://yourdomain.com/unsubscribe")


def _build_html_body(text_body: str, unsubscribe_url: str, recipient_email: str) -> str:
    """
    Wraps the plain text pitch in a clean, professional HTML email.
    Includes mandatory unsubscribe footer (PRD §6.5).
    """
    # Convert plain newlines to HTML line breaks
    html_paragraphs = "".join(
        f"<p style='margin:0 0 12px 0;'>{line}</p>" if line.strip() else "<br/>"
        for line in text_body.split("\n")
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Email from Adler's Den</title>
</head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f9f9f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9f9f9;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background-color:#1a1a2e;padding:24px 32px;">
              <p style="margin:0;color:#ffffff;font-size:20px;font-weight:bold;letter-spacing:0.5px;">
                Adler's Den
              </p>
              <p style="margin:4px 0 0 0;color:#a0aec0;font-size:12px;">
                Premium Corporate Gifting & Employee Engagement
              </p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px;color:#2d3748;font-size:15px;line-height:1.7;">
              {html_paragraphs}
            </td>
          </tr>
          <!-- Divider -->
          <tr>
            <td style="padding:0 32px;">
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0;" />
            </td>
          </tr>
          <!-- Footer — Mandatory Unsubscribe (PRD §6.5) -->
          <tr>
            <td style="padding:20px 32px;text-align:center;">
              <p style="margin:0;color:#a0aec0;font-size:11px;line-height:1.6;">
                You are receiving this email because your organisation may benefit from our services.
                <br/>
                If you wish to stop receiving emails from us, please
                <a href="{unsubscribe_url}?email={recipient_email}"
                   style="color:#667eea;text-decoration:underline;">unsubscribe here</a>.
                <br/><br/>
                &copy; Adler's Den | This email is intended for business decision-makers only.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> dict:
    """
    Main entry point for Module 5.
    Sends one email via SendGrid and returns a status dict.

    Returns: {"success": bool, "message_id": str | None, "error": str | None}
    """
    # --- TESTING MODE BYPASS ---
    # logger.info(f"[TEST MODE] Simulating email send to {to_email}")
    # return {"success": True, "message_id": "mock_id_for_testing", "error": None}
    # ---------------------------

    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY is not set. Email not sent.")
        return {"success": False, "message_id": None, "error": "SendGrid API key not configured."}

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent

        html_body = _build_html_body(body, UNSUBSCRIBE_URL, to_email)

        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
        )
        message.add_content(Content("text/plain", body))
        message.add_content(HtmlContent(html_body))



        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 202):
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(f"Email sent to {to_email}. SendGrid message_id: {message_id}")
            return {"success": True, "message_id": message_id, "error": None}
        else:
            error_msg = f"Unexpected SendGrid status: {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message_id": None, "error": error_msg}

    except Exception as e:
        logger.error(f"SendGrid dispatch failed for {to_email}: {e}")
        return {"success": False, "message_id": None, "error": str(e)}
