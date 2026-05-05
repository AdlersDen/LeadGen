"""
SendGrid Event Webhook Handler
Receives inbound delivery/engagement events from SendGrid and updates
the Outreach Logs sheet status in real time.

Registered events: delivered, bounce, open, unsubscribe

Setup in SendGrid:
  Settings → Mail Settings → Event Webhook
  HTTP POST URL: https://<your-render-url>/api/webhooks/sendgrid
  Events to check: Delivered, Bounced, Opened, Unsubscribed

PRD §6.6 — Tracking & Storage
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from sheets_db import db

logger = logging.getLogger(__name__)

router = APIRouter()

# Map SendGrid event strings to internal status values stored in Sheets
SENDGRID_EVENT_MAP = {
    "delivered":    "delivered",
    "bounce":       "bounced",
    "dropped":      "bounced",
    "open":         "opened",
    "unsubscribe":  "unsubscribed",
    "spamreport":   "spam",
}


@router.post("/api/webhooks/sendgrid")
@router.post("/webhooks/sendgrid")
async def sendgrid_webhook(request: Request):
    """
    Receives a JSON array of SendGrid events.
    For each event, updates the matching Outreach Log row's Status column.

    SendGrid sends events in batches — each POST body is a JSON list.
    """
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload from SendGrid.")

    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of events.")

    processed = 0
    for event in events:
        sg_event   = event.get("event", "").lower()
        message_id = event.get("sg_message_id", "").split(".")[0]  # strip SendGrid suffix
        email      = event.get("email", "")

        new_status = SENDGRID_EVENT_MAP.get(sg_event)
        if not new_status:
            logger.debug(f"Ignoring unmapped SendGrid event: {sg_event}")
            continue

        if not message_id:
            logger.warning(f"Received {sg_event} event with no sg_message_id — skipping.")
            continue

        try:
            db.update_outreach_status(message_id, new_status)
            processed += 1
            logger.info(f"Webhook: updated {email} → {new_status} (msg_id={message_id})")
        except Exception as e:
            logger.error(f"Webhook: failed to update status for {message_id}: {e}")

    return {"received": len(events), "processed": processed}
