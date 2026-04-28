"""
Module 5 — Email Outreach Engine
Sends personalized emails via SendGrid API with:
  - From: marketing@adlersden.com (verified domain: adlersden.com)
  - Open + click tracking enabled (PRD §6.6)
  - Daily send limit for warm-up compliance (PRD §6.5)
  - Mandatory unsubscribe footer (PRD §6.5)
  - Bounce/delivery error handling
PRD §6.5
"""

import logging
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SENDGRID_API_KEY   = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL         = os.getenv("SENDGRID_FROM_EMAIL", "marketing@adlersden.com")
FROM_NAME          = os.getenv("SENDGRID_FROM_NAME", "Adler's Den")
UNSUBSCRIBE_URL    = os.getenv("UNSUBSCRIBE_URL", "https://adlers-den-leadgen.vercel.app/unsubscribe")
DAILY_SEND_LIMIT   = int(os.getenv("DAILY_SEND_LIMIT", "50"))

# ─── In-memory daily send counter ────────────────────────────────────────────
# Resets automatically when the date changes (process restart on Render also resets it).
_send_counter: dict[str, int] = {}   # { "YYYY-MM-DD": count }


def _format_sendgrid_error(err: Exception) -> str:
    """Return the most useful SendGrid error message we can extract."""
    status_code = getattr(err, "status_code", None)
    body = getattr(err, "body", None)

    body_text = ""
    if isinstance(body, bytes):
        body_text = body.decode("utf-8", errors="replace")
    elif body:
        body_text = str(body)

    if status_code == 403:
        hint = (
            "SendGrid rejected the request with 403 Forbidden. "
            "Check that the API key has Mail Send permission and that "
            f"'{FROM_EMAIL}' is a verified sender identity."
        )
        return f"{hint} Response: {body_text or str(err)}"

    if body_text:
        return body_text

    return str(err)


def _check_daily_limit() -> bool:
    """
    Returns True if we are still within today's send quota.
    PRD §6.5 — warm-up: 50/day for first week, then scale to 300/day max.
    """
    today = str(date.today())
    count = _send_counter.get(today, 0)
    if count >= DAILY_SEND_LIMIT:
        logger.warning(
            f"Daily send limit reached ({count}/{DAILY_SEND_LIMIT}). "
            "Email not sent. Increase DAILY_SEND_LIMIT after warm-up."
        )
        return False
    return True


def _increment_counter():
    today = str(date.today())
    _send_counter[today] = _send_counter.get(today, 0) + 1


def _build_html_body(text_body: str, unsubscribe_url: str, recipient_email: str) -> str:
    """
    Wraps the plain text pitch in a clean, professional HTML email.
    Includes mandatory unsubscribe footer (PRD §6.5).
    """
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
                Premium Corporate Gifting &amp; Employee Engagement
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

    Enforces daily send limit (PRD §6.5 warm-up compliance).
    Enables open + click tracking (PRD §6.6 analytics).

    Returns: {"success": bool, "message_id": str | None, "error": str | None}
    """
    # --- Daily limit check (PRD §6.5 — warm-up: 50/day) ---
    if not _check_daily_limit():
        return {
            "success": False,
            "message_id": None,
            "error": f"Daily send limit of {DAILY_SEND_LIMIT} reached. Try again tomorrow or increase DAILY_SEND_LIMIT.",
        }

    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY is not set. Email not sent.")
        return {"success": False, "message_id": None, "error": "SendGrid API key not configured."}

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (
            Mail, Email, To, Content, HtmlContent,
            TrackingSettings, ClickTracking, OpenTracking,
        )

        html_body = _build_html_body(body, UNSUBSCRIBE_URL, to_email)

        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
        )
        message.add_content(Content("text/plain", body))
        message.add_content(HtmlContent(html_body))

        # --- PRD §6.6 — Enable open + click tracking for analytics ---
        tracking = TrackingSettings()
        tracking.click_tracking = ClickTracking(enable=True, enable_text=False)
        tracking.open_tracking = OpenTracking(enable=True)
        message.tracking_settings = tracking

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 202):
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(f"Email sent to {to_email}. SendGrid message_id: {message_id}")
            _increment_counter()
            return {"success": True, "message_id": message_id, "error": None}
        else:
            error_msg = f"Unexpected SendGrid status: {response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message_id": None, "error": error_msg}

    except Exception as e:
        error_message = _format_sendgrid_error(e)
        logger.error(f"SendGrid dispatch failed for {to_email}: {error_message}")
        return {"success": False, "message_id": None, "error": error_message}
