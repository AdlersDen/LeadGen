"""
Adler's Den — Corporate Outreach MVP
FastAPI Entry Point

Routes:
  GET  /api/health              Health check
  GET  /api/companies           List all companies from Sheets
  GET  /api/contacts            List all contacts from Sheets
  GET  /api/outreach            List all outreach logs from Sheets
  GET  /api/runs                List all pincode runs from Sheets
  GET  /api/dashboard-stats     Aggregated counts for the dashboard
  POST /api/discover            Module 1: Discover companies by pincode
  POST /api/contacts/find       Module 2: Find contacts for a company
  POST /api/pitches/generate    Module 4: Generate AI email pitch
  POST /api/outreach/send       Module 5: Send email via SendGrid
"""

import logging
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# --- Local modules ---
from sheets_db import db
from discovery import discover_companies
from contacts import find_contacts
from pitches import generate_pitch
from outreach import send_email
from webhooks import router as webhook_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# App Initialization
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Adler's Den — Corporate Outreach MVP",
    description="Backend API for pincode discovery, contact extraction, AI pitches, and email outreach.",
    version="1.0.0",
)

# Define allowed origins for both local development and production
origins = [
    "http://localhost:5173",     # Vite default
    "http://127.0.0.1:5173",
    "http://localhost:3000",     # React/Next.js default
    "http://127.0.0.1:3000",
    "https://adlers-den-leadgen.vercel.app" # Production frontend
]

# Add Vercel preview environments support if FRONTEND_URL is set in environment
if os.environ.get("FRONTEND_URL"):
    origins.append(os.environ.get("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(webhook_router)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    pincode:      str | None       = None
    complex_name: str | None       = None
    radius_km:    int              = 2
    industries:   list[str]        = []
    tiers:        list[str]        = ["A", "B"]

class FindContactsRequest(BaseModel):
    company_id: str
    company_name: str
    domain: str

class BulkFindContactsRequest(BaseModel):
    limit: int = 5

class ExtractSelectedRequest(BaseModel):
    company_ids: list[str]

class GeneratePitchRequest(BaseModel):
    contact_name: str
    role: str
    company_name: str

class SendEmailRequest(BaseModel):
    contact_id: str
    contact_name: str
    contact_email: str
    company_name: str
    subject: str
    body: str

class UnsubscribeRequest(BaseModel):
    email: str


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Adler's Den backend is running!"}


# ───────────────────────────────────────────────────────────────────────────────
# Unsubscribe (PRD §6.5 Compliance)
# ───────────────────────────────────────────────────────────────────────────────

@app.post("/api/unsubscribe")
async def unsubscribe(req: UnsubscribeRequest):
    """
    Adds the email to the Blocklist tab in Google Sheets.
    Called by the /unsubscribe frontend page when user confirms opt-out.
    """
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="A valid email address is required.")
    try:
        db.add_to_blocklist(email)
        return {"success": True, "message": f"{email} has been unsubscribed."}
    except Exception as e:
        logger.error(f"/api/unsubscribe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# READ endpoints (for the frontend data tables)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/companies")
async def list_companies():
    """Returns all company records from the Google Sheet."""
    try:
        return db.get_companies()
    except Exception as e:
        logger.error(f"/api/companies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies/pending")
async def list_pending_companies():
    """Returns companies that have NOT yet had contacts extracted."""
    try:
        return db.get_pending_companies()
    except Exception as e:
        logger.error(f"/api/companies/pending failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contacts")
async def list_contacts():
    """Returns all contact records from the Google Sheet."""
    try:
        return db.get_contacts()
    except Exception as e:
        logger.error(f"/api/contacts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/contacts/cooldown-status")
async def get_cooldown_status():
    """
    Returns a dict mapping email -> bool indicating 90-day cooldown status.
    Used by the frontend to show 'In Cooldown' badges on Contacts and Outreach pages.
    """
    try:
        contacts = db.get_contacts()
        result = {}
        for contact in contacts:
            email = (contact.get("Email") or "").strip()
            if email:
                result[email] = db.is_contact_recently_emailed(email)
        return result
    except Exception as e:
        logger.error(f"/api/contacts/cooldown-status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outreach")
async def list_outreach():
    """Returns all outreach log records from the Google Sheet."""
    try:
        return db.get_outreach_logs()
    except Exception as e:
        logger.error(f"/api/outreach failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def get_runs():
    try:
        runs      = db.get_runs()
        companies = db.get_companies()
        contacts  = db.get_contacts()
        outreach  = db.get_outreach_logs()

        for run in runs:
            try:
                pincode  = str(run.get("Pincode") or run.get("pincode") or "").strip()
                complex_name = str(run.get("Complex Name") or run.get("complex_name") or "").strip()
                location = str(run.get("Location Name") or run.get("location_name") or "").strip()
                effective_location = location or complex_name

                if pincode:
                    # Pincode mode — match companies by pincode field
                    run_companies = [
                        c for c in companies
                        if str(c.get("Pincode") or c.get("pincode") or "").strip() == pincode
                    ]
                elif effective_location:
                    # Complex-mode run (no pincode) — fuzzy match by location name
                    loc_lower = effective_location.lower()
                    run_companies = [
                        c for c in companies
                        if loc_lower in str(c.get("Address") or "").lower()
                    ]
                else:
                    run_companies = []

                company_ids  = [c.get("ID") for c in run_companies if c.get("ID")]
                run_contacts = [c for c in contacts if c.get("Company ID") in company_ids]
                contact_ids  = [c.get("ID") for c in run_contacts if c.get("ID")]
                run_emails   = [o for o in outreach if o.get("Contact ID") in contact_ids]

                run["Companies Found"] = len(run_companies)
                run["Contacts Found"]  = len(run_contacts)
                run["Emails Sent"]     = len(run_emails)
                if effective_location:
                    run["Location Name"] = effective_location
                if not pincode and complex_name:
                    run["Pincode"] = "complex"

            except Exception as row_err:
                logger.warning(f"Skipping bad run row {run.get('ID')}: {row_err}")
                run.setdefault("Companies Found", 0)
                run.setdefault("Contacts Found", 0)
                run.setdefault("Emails Sent", 0)

        return sorted(
            runs,
            key=lambda x: x.get("Timestamp") or x.get("created_date") or "",
            reverse=True,
        )
    except Exception as e:
        logger.error(f"/api/runs failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard-stats")
async def dashboard_stats():
    """Aggregated counts for the dashboard stat cards."""
    try:
        companies = db.get_companies()
        contacts = db.get_contacts()
        outreach_logs = db.get_outreach_logs()
        runs = db.get_runs()

        # Count emails by status — "sent" = accepted by SendGrid (202 OK)
        # Webhook updates to "delivered"/"opened" if configured
        SENT_STATUSES      = {"sent", "delivered", "opened", "clicked", "replied"}
        DELIVERED_STATUSES = {"delivered", "opened", "clicked", "replied"}
        OPENED_STATUSES    = {"opened", "clicked"}
        BOUNCED_STATUSES   = {"bounced", "bounce", "dropped"}

        total_sent      = len([o for o in outreach_logs if (o.get("Status") or "").lower() in SENT_STATUSES])
        total_delivered = len([o for o in outreach_logs if (o.get("Status") or "").lower() in DELIVERED_STATUSES])
        total_opened    = len([o for o in outreach_logs if (o.get("Status") or "").lower() in OPENED_STATUSES])
        total_bounced   = len([o for o in outreach_logs if (o.get("Status") or "").lower() in BOUNCED_STATUSES])
        total_replied   = len([o for o in outreach_logs if (o.get("Status") or "").lower() == "replied"])

        delivery_rate = round((total_delivered / total_sent * 100)) if total_sent > 0 else 0
        open_rate     = round((total_opened    / total_sent * 100)) if total_sent > 0 else 0
        bounce_rate   = round((total_bounced   / total_sent * 100)) if total_sent > 0 else 0
        reply_rate    = round((total_replied   / total_sent * 100)) if total_sent > 0 else 0

        return {
            "companies":       len(companies),
            "contacts":        len(contacts),
            "emails_sent":     total_sent,
            "reply_rate":      reply_rate,
            "delivery_rate":   delivery_rate,
            "open_rate":       open_rate,
            "bounce_rate":     bounce_rate,
            "recent_runs":     runs[-10:],
            "recent_outreach": outreach_logs[-10:],
        }
    except Exception as e:
        logger.error(f"/api/dashboard-stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Module 1 — Company Discovery
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/discover")
async def discover(req: DiscoverRequest):
    """
    Discovers B2B companies via Google Maps.
    Supports two modes:
      - Pincode mode:  geocode pincode → nearby_search in radius_km
      - Complex mode:  text search for corporate offices in the named complex
    Optional filters: industries (multi-select), tiers (A/B/C).
    """
    if not req.pincode and not req.complex_name:
        raise HTTPException(status_code=422, detail="Provide either a pincode or a business complex name.")

    try:
        if req.complex_name:
            # Complex / area mode — pass to discovery module
            result = discover_companies(
                pincode=None,
                complex_name=req.complex_name.strip(),
                industries=req.industries,
                tiers=req.tiers,
            )
        else:
            # Pincode mode — validate then discover
            code = req.pincode.strip()
            if not code or not code.isdigit() or len(code) != 6:
                raise HTTPException(status_code=422, detail="A valid 6-digit Indian pincode is required.")
            result = discover_companies(
                pincode=code,
                radius_km=req.radius_km,
                industries=req.industries,
                tiers=req.tiers,
            )
    except HTTPException:
        raise
    except Exception as e:
        label = req.complex_name or req.pincode
        logger.error(f"Discovery error for {label}: {e}")
        raise HTTPException(status_code=502, detail=f"Company discovery failed: {e}")

    companies     = result.get("companies", [])
    location_name = result.get("location_name") or req.complex_name or req.pincode or ""

    saved_companies = db.add_companies_bulk(companies) if companies else []

    # Log the run
    db.add_run({
        "pincode":        req.pincode or "",
        "complex_name":   req.complex_name or "",
        "location_name":  location_name,
        "companies_found": len(companies),
        "contacts_found": 0,
        "emails_sent":    0,
        "status":         "completed",
    })

    return {
        "pincode":         req.pincode,
        "complex_name":    req.complex_name,
        "location_name":   location_name,
        "companies_found": len(companies),
        "companies":       companies,
    }


# ─────────────────────────────────────────────────────────────────────────────
                db.add_contact(contact_data, company_id)
            
            # If we attempted extraction (even if 0 found), we consider it processed
            # so we don't keep wasting credits on it.
            successful_company_ids.append(company_id)
                
        except Exception as e:
            logger.error(f"Selective contact extraction error for {company_name}: {e}")
            continue

    if successful_company_ids:
        db.mark_contacts_extracted_bulk(successful_company_ids)

    return {
        "queued": queued,
        "skipped_no_domain": skipped_no_domain,
        "skipped_already_extracted": skipped_already_extracted
    }


# ─────────────────────────────────────────────────────────────────────────────
# Module 4 — AI Pitch Generation
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/pitches/generate")
async def generate_pitch_for_contact(req: GeneratePitchRequest):
    """
    Generates a personalized outreach email using Gemini 2.5 Flash-Lite.
    Implements a 4-second delay and prompt caching as per the PRD.
    """
    try:
        pitch = generate_pitch(req.contact_name, req.role, req.company_name)
        return {"subject": pitch["subject"], "body": pitch["body"]}
    except Exception as e:
        logger.error(f"Pitch generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Pitch generation failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Module 5 — Email Outreach
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/outreach/send")
async def send_outreach_email(req: SendEmailRequest):
    """
    Sends a personalized email via SendGrid.
    Checks blocklist, then 90-day cooldown before dispatching.
    Logs the dispatch to the Outreach Logs sheet.
    """
    # PRD §Phase3 — Blocklist check (unsubscribed contacts)
    if db.is_blocklisted(req.contact_email):
        raise HTTPException(
            status_code=409,
            detail=f"{req.contact_email} has unsubscribed and cannot be contacted."
        )

    # PRD §6.6 — 90-day duplicate prevention
    if db.is_contact_recently_emailed(req.contact_email):
        raise HTTPException(
            status_code=409,
            detail=f"{req.contact_email} was already contacted within the last 90 days."
        )

    result = send_email(
        to_email=req.contact_email,
        to_name=req.contact_name,
        subject=req.subject,
        body=req.body,
    )

    if not result["success"]:
        status_code = 429 if "Daily send limit" in (result.get("error") or "") else 502
        raise HTTPException(
            status_code=status_code,
            detail=f"Email send failed: {result.get('error', 'Unknown error')}"
        )

    # Log successful dispatch (include message_id for webhook matching)
    campaign_id = f"campaign_{req.contact_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    db.add_outreach_log({
        "campaign_id": campaign_id,
        "contact_id": req.contact_id,
        "contact_email": req.contact_email,
        "contact_name": req.contact_name,
        "company_name": req.company_name,
        "subject": req.subject,
        "body": req.body,
        "status": "sent",
        "message_id": result.get("message_id", ""),
    })

    return {
        "success": True,
        "message": f"Email sent to {req.contact_email}",
        "message_id": result.get("message_id"),
    }
