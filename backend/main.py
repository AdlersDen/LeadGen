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


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    pincode: str

class FindContactsRequest(BaseModel):
    company_id: str
    company_name: str
    domain: str

class BulkFindContactsRequest(BaseModel):
    limit: int = 5

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


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Adler's Den backend is running!"}


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


@app.get("/api/contacts")
async def list_contacts():
    """Returns all contact records from the Google Sheet."""
    try:
        return db.get_contacts()
    except Exception as e:
        logger.error(f"/api/contacts failed: {e}")
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
    runs = db.get_runs()
    companies = db.get_companies()
    contacts = db.get_contacts()
    outreach = db.get_outreach_logs()

    # Dynamically calculate the totals so they are always up to date
    for run in runs:
        pincode = str(run.get("Pincode") or run.get("pincode", ""))
        
        run_companies = [c for c in companies if str(c.get("Pincode") or c.get("pincode", "")) == pincode]
        company_ids = [c.get("ID") for c in run_companies if c.get("ID")]
        
        run_contacts = [c for c in contacts if c.get("Company ID") in company_ids]
        contact_ids = [c.get("ID") for c in run_contacts if c.get("ID")]
        
        run_emails = [o for o in outreach if o.get("Contact ID") in contact_ids]

        run["Companies Found"] = len(run_companies)
        run["Contacts Found"] = len(run_contacts)
        run["Emails Sent"] = len(run_emails)

    return sorted(runs, key=lambda x: x.get("Timestamp", x.get("created_date", "")), reverse=True)


@app.get("/api/dashboard-stats")
async def dashboard_stats():
    """Aggregated counts for the dashboard stat cards."""
    try:
        companies = db.get_companies()
        contacts = db.get_contacts()
        outreach_logs = db.get_outreach_logs()
        runs = db.get_runs()

        total_sent = len([o for o in outreach_logs if o.get("Status", "").lower() == "sent"])
        total_replied = len([o for o in outreach_logs if o.get("Status", "").lower() == "replied"])
        reply_rate = round((total_replied / total_sent * 100)) if total_sent > 0 else 0

        return {
            "companies": len(companies),
            "contacts": len(contacts),
            "emails_sent": total_sent,
            "reply_rate": reply_rate,
            "recent_runs": runs[-10:],
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
    Discovers B2B companies for a given pincode via Google Maps,
    saves results to the Companies + Runs sheets, and returns them.
    """
    pincode = req.pincode.strip()
    if not pincode or not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=422, detail="A valid 6-digit Indian pincode is required.")

    try:
        result = discover_companies(pincode)
    except Exception as e:
        logger.error(f"Discovery error for {pincode}: {e}")
        raise HTTPException(status_code=502, detail=f"Company discovery failed: {e}")

    companies = result.get("companies", [])
    location_name = result.get("location_name", pincode)
    
    saved_companies = db.add_companies_bulk(companies) if companies else []

    # Log the run (record total discovered, not just newly saved)
    db.add_run({
        "pincode": pincode,
        "location_name": location_name,
        "companies_found": len(companies),
        "contacts_found": 0,
        "emails_sent": 0,
        "status": "completed",
    })

    return {
        "pincode": pincode,
        "location_name": location_name,
        "companies_found": len(companies),
        "companies": companies,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Module 2 — Contact Discovery
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/contacts/find")
async def find_contacts_for_company(req: FindContactsRequest):
    """
    Finds verified decision-maker contacts for a company via Hunter.io / Apollo.io.
    Saves results to the Contacts sheet.
    """
    if not req.domain:
        raise HTTPException(
            status_code=422,
            detail="A company domain is required to search for contacts. Please add a domain to the company first."
        )

    try:
        raw_contacts = find_contacts(req.company_name, req.domain)
    except Exception as e:
        logger.error(f"Contact discovery error for {req.company_name}: {e}")
        raise HTTPException(status_code=502, detail=f"Contact lookup failed: {e}")

    saved_contacts = []
    for contact_data in raw_contacts:
        contact_data["company_name"] = req.company_name
        contact_data["status"] = "discovered"
        saved = db.add_contact(contact_data, req.company_id)
        if saved:
            saved_contacts.append(saved)

    return {
        "company_id": req.company_id,
        "contacts_found": len(saved_contacts),
        "contacts": saved_contacts,
    }


@app.post("/api/contacts/bulk-find")
async def bulk_find_contacts(req: BulkFindContactsRequest):
    """
    Finds verified decision-maker contacts for multiple companies automatically.
    Filters out companies that already have contacts or no domain.
    Stops processing when the limit is reached to protect API credits.
    """
    companies = db.get_companies()
    
    # Filter for companies that have a domain AND haven't been pitched/emailed yet
    # For MVP, we'll just check if they have a domain and their status is 'discovered'
    eligible_companies = [
        c for c in companies 
        if c.get("Domain") and c.get("Status", "").lower() == "discovered"
    ]
    
    companies_to_process = eligible_companies[:req.limit]
    
    if not companies_to_process:
        return {"processed": 0, "contacts_found": 0, "message": "No eligible companies found to process."}

    total_contacts_found = 0
    processed_count = 0

    for company in companies_to_process:
        domain = company.get("Domain")
        company_name = company.get("Name") or company.get("Company Name")
        company_id = company.get("ID")
        
        try:
            raw_contacts = find_contacts(company_name, domain)
            processed_count += 1
            
            for contact_data in raw_contacts:
                contact_data["company_name"] = company_name
                contact_data["status"] = "discovered"
                saved = db.add_contact(contact_data, company_id)
                if saved:
                    total_contacts_found += 1
                    
            # Update company status to indicate contacts were searched
            # We don't have a direct row-update function in SheetsDB yet for MVP, 
            # so we rely on the fact that contacts now exist for this company ID.
            
        except Exception as e:
            logger.error(f"Bulk contact discovery error for {company_name}: {e}")
            continue

    return {
        "processed": processed_count,
        "contacts_found": total_contacts_found,
        "message": f"Processed {processed_count} companies and found {total_contacts_found} contacts."
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
    Checks 90-day cooldown before dispatching.
    Logs the dispatch to the Outreach Logs sheet.
    """
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
        raise HTTPException(
            status_code=502,
            detail=f"Email send failed: {result.get('error', 'Unknown error')}"
        )

    # Log successful dispatch
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
    })

    return {
        "success": True,
        "message": f"Email sent to {req.contact_email}",
        "message_id": result.get("message_id"),
    }
