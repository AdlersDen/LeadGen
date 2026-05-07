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

# --- Brand sender & CTA config ---
CALENDAR_LINK = os.getenv("CALENDAR_LINK", "https://calendly.com/adlersden")
SENDER_NAME   = os.getenv("SENDER_NAME", "The Adler's Den Team")
SENDER_TITLE  = os.getenv("SENDER_TITLE", "Corporate Gifting Specialist")
SENDER_PHONE  = os.getenv("SENDER_PHONE", "+91 98XXX XXXXX")

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


def build_email_html(
    contact_name: str,
    company_name: str,
    role: str,
    subject: str,
    body: str,
    recipient_email: str = "",
) -> str:
    """
    Builds a premium, inline-CSS HTML email for Adler's Den outreach.
    All CSS is inline — no <style> tags, Gmail-safe.
    PRD §6.5 — includes mandatory unsubscribe footer.
    """
    # --- Body paragraphs: split on newline, wrap each non-empty line ---
    paragraphs_html = "".join(
        f'<p style="margin:0 0 14px 0;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:16px;color:#374151;line-height:1.7;">{line.strip()}</p>'
        for line in body.split("\n")
        if line.strip()
    )

    unsubscribe_href = f"{UNSUBSCRIBE_URL}?email={recipient_email}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#F0EBE3;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#F0EBE3;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;">

          <!-- ═══ HEADER BAND ═══ -->
          <tr>
            <td style="background-color:#2C1810;padding:16px 32px;text-align:center;">
              <span style="font-family:Arial,Helvetica,sans-serif;font-size:13px;
                           color:#FAF7F2;letter-spacing:2px;font-variant:small-caps;
                           font-weight:600;">
                ADLER&rsquo;S DEN &middot; CORPORATE GIFTING
              </span>
            </td>
          </tr>

          <!-- ═══ HERO HEADLINE ═══ -->
          <tr>
            <td style="background-color:#FAF7F2;padding:32px 40px 28px 40px;">
              <h1 style="margin:0;font-family:Georgia,'Times New Roman',Times,serif;
                         font-size:26px;font-weight:bold;color:#2C1810;line-height:1.35;">
                {subject}
              </h1>
            </td>
          </tr>

          <!-- ═══ BODY SECTION ═══ -->
          <tr>
            <td style="background-color:#ffffff;padding:32px 40px;">
              {paragraphs_html}

              <!-- ── Promise callout box ── -->
              <div style="background-color:#F5EFE6;border-left:3px solid #8B4513;
                          margin:24px 0;padding:16px 20px;">
                <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:14px;
                           color:#2C1810;font-style:italic;line-height:1.6;">
                  Every Adler&rsquo;s Den experience is thoughtfully curated, personally
                  delivered, and built around your company&rsquo;s values.
                </p>
              </div>

              <!-- ── CTA Button ── -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:28px 0 24px 0;">
                <tr>
                  <td align="center">
                    <a href="{CALENDAR_LINK}"
                       style="display:inline-block;background-color:#8B4513;color:#ffffff;
                              font-family:Arial,Helvetica,sans-serif;font-size:13px;
                              font-weight:bold;letter-spacing:1.5px;text-decoration:none;
                              text-transform:uppercase;padding:14px 32px;border-radius:4px;">
                      SCHEDULE A QUICK CALL
                    </a>
                  </td>
                </tr>
              </table>

              <!-- ── Signature ── -->
              <table cellpadding="0" cellspacing="0" border="0" style="margin-top:28px;">
                <tr>
                  <td>
                    <p style="margin:0 0 2px 0;font-family:Arial,Helvetica,sans-serif;
                               font-size:14px;font-weight:bold;color:#2C1810;line-height:2;">
                      {SENDER_NAME}
                    </p>
                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                               font-size:14px;color:#374151;line-height:2;">
                      {SENDER_TITLE}
                    </p>
                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                               font-size:14px;color:#374151;line-height:2;">
                      <a href="mailto:marketing@adlersden.com"
                         style="color:#8B4513;text-decoration:none;">
                        marketing@adlersden.com
                      </a>
                    </p>
                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                               font-size:14px;color:#374151;line-height:2;">
                      {SENDER_PHONE}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- ── P.S. line ── -->
              <p style="margin:24px 0 0 0;font-family:Arial,Helvetica,sans-serif;
                         font-size:13px;color:#6B7280;font-style:italic;line-height:1.6;">
                P.S. &mdash; We currently work with corporates across Mumbai, Pune, and
                Bangalore for their festive and milestone gifting. References available on
                request.
              </p>
            </td>
          </tr>

          <!-- ═══ FOOTER ═══ -->
          <tr>
            <td style="background-color:#F5EFE6;padding:20px 40px;text-align:center;">
              <p style="margin:0 0 4px 0;font-family:Arial,Helvetica,sans-serif;
                         font-size:14px;font-weight:600;color:#2C1810;
                         letter-spacing:1.5px;font-variant:small-caps;">
                Adler&rsquo;s Den
              </p>
              <p style="margin:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;
                         font-size:12px;color:#6B7280;">
                Artisan &middot; Ethical &middot; Exceptional &middot; Mumbai
              </p>
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                         font-size:11px;color:#9CA3AF;line-height:1.6;">
                You are receiving this because your organisation may benefit from our
                services.<br />
                <a href="{unsubscribe_href}"
                   style="color:#8B4513;text-decoration:underline;">Unsubscribe</a>
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
    contact_name: str = "",
    company_name: str = "",
    role: str = "",
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

        html_body = build_email_html(
            contact_name=contact_name or to_name,
            company_name=company_name,
            role=role,
            subject=subject,
            body=body,
            recipient_email=to_email,
        )

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
