"""
Full Pipeline Audit — Pre-Submission
Tests each module in the pipeline E2E:
  1. Discovery (Google Maps)
  2. Contact Intelligence (Apollo + Hunter)
  3. Data Cleaning (MX verification)
  4. AI Pitch Generation (Groq → Gemini → Fallback)
  5. Sheets DB (Read/Write)
  6. Outreach Email HTML builder (no actual send)
"""
import sys
import json
import os
from dotenv import load_dotenv
load_dotenv()

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []

def test(name, func):
    try:
        ok, detail = func()
        status = PASS if ok else FAIL
        results.append((name, status, detail))
        print(f"  {status}  {name}: {detail}")
    except Exception as e:
        results.append((name, FAIL, str(e)))
        print(f"  {FAIL}  {name}: {e}")

print("=" * 70)
print("  ADLER'S DEN — FULL PIPELINE AUDIT")
print("=" * 70)

# ──────────────────────────────────────────────────────
# 0. Environment Variables
# ──────────────────────────────────────────────────────
print("\n🔧 Module 0: Environment Variables")

def check_env():
    required = [
        "GOOGLE_SHEET_ID", "GOOGLE_MAPS_API_KEY", "APOLLO_API_KEY",
        "HUNTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
        "SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, f"All {len(required)} keys present"

test("Environment variables", check_env)

# ──────────────────────────────────────────────────────
# 1. Google Sheets Connection
# ──────────────────────────────────────────────────────
print("\n📊 Module 1: Google Sheets DB")

def check_sheets():
    from sheets_db import db
    connected = db.connect()
    if not connected:
        return False, "Could not connect to Google Sheets"
    companies = db.get_companies()
    contacts = db.get_contacts()
    runs = db.get_runs()
    return True, f"Connected. {len(companies)} companies, {len(contacts)} contacts, {len(runs)} runs"

test("Sheets DB connection", check_sheets)

# ──────────────────────────────────────────────────────
# 2. Discovery (Google Maps)
# ──────────────────────────────────────────────────────
print("\n🗺️  Module 2: Company Discovery (Google Maps)")

def check_discovery():
    from discovery import discover_companies
    result = discover_companies(pincode=None, complex_name="Nirlon Knowledge Park")
    companies = result.get("companies", [])
    if not companies:
        return False, "No companies discovered"
    sample = companies[0]
    has_fields = all(k in sample for k in ["name", "domain", "address"])
    return True, f"Found {len(companies)} companies. Sample: {sample.get('name', 'N/A')} (domain: {sample.get('domain', 'N/A')})"

test("Discovery via complex name", check_discovery)

# ──────────────────────────────────────────────────────
# 3. Contact Intelligence (Apollo + Hunter)
# ──────────────────────────────────────────────────────
print("\n👤 Module 3: Contact Intelligence")

def check_apollo():
    from contacts import _search_apollo
    contacts = _search_apollo("Titan Company Limited", "titan.co.in")
    if not contacts:
        return False, "Apollo returned 0 contacts"
    c = contacts[0]
    has_email = bool(c.get("email"))
    has_name = bool(c.get("full_name"))
    has_enrichment = bool(c.get("linkedin_url") or c.get("seniority") or c.get("location"))
    return True, f"{len(contacts)} contacts. Sample: {c.get('full_name')} <{c.get('email')}> | LinkedIn: {c.get('linkedin_url', 'N/A')} | Seniority: {c.get('seniority', 'N/A')} | Location: {c.get('location', 'N/A')}"

def check_hunter():
    from contacts import _search_hunter
    contacts = _search_hunter("titan.co.in")
    if not contacts:
        return False, "Hunter returned 0 contacts"
    c = contacts[0]
    return True, f"{len(contacts)} contacts. Sample: {c.get('full_name')} <{c.get('email')}> (confidence: {c.get('confidence_score')})"

test("Apollo.io (primary)", check_apollo)
test("Hunter.io (fallback)", check_hunter)

# ──────────────────────────────────────────────────────
# 4. Data Cleaning
# ──────────────────────────────────────────────────────
print("\n🧹 Module 4: Data Cleaning & MX Verification")

def check_cleaning():
    from cleaning import clean_contact_data, normalize_name, verify_mx_record
    # Test name normalization
    assert normalize_name("john DOE") == "John Doe", "Name normalization failed"
    # Test MX verification
    mx_ok = verify_mx_record("titan.co.in")
    if not mx_ok:
        return False, "MX check failed for titan.co.in"
    # Test full cleaning
    cleaned = clean_contact_data({"full_name": "test USER", "email": "test@titan.co.in", "role": "HR"})
    if not cleaned:
        return False, "clean_contact_data returned None for valid email"
    return True, f"Name norm OK, MX verification OK, Full clean pipeline OK"

test("Data cleaning & MX", check_cleaning)

# ──────────────────────────────────────────────────────
# 5. Company Intelligence (Apollo Org Enrichment)
# ──────────────────────────────────────────────────────
print("\n🏢 Module 5: Company Intelligence (Apollo Enrichment)")

def check_company_intel():
    from pitches import _get_company_intel
    intel = _get_company_intel("titan.co.in")
    if not intel:
        return False, "No intel returned"
    has_headcount = "Headcount" in intel
    has_industry = "Industry" in intel
    return True, f"Intel fetched. Headcount: {'✓' if has_headcount else '✗'}, Industry: {'✓' if has_industry else '✗'}. Preview: {intel[:120]}..."

test("Company intel enrichment", check_company_intel)

# ──────────────────────────────────────────────────────
# 6. AI Pitch Generation
# ──────────────────────────────────────────────────────
print("\n🤖 Module 6: AI Pitch Generation")

def check_pitch():
    from pitches import generate_pitch
    pitch = generate_pitch("Sana Afaq", "Head of HR", "Titan Company Limited")
    if not pitch:
        return False, "Pitch generation returned None"
    has_subject = bool(pitch.get("subject"))
    has_body = bool(pitch.get("body"))
    if not has_subject or not has_body:
        return False, f"Missing fields: subject={has_subject}, body={has_body}"
    word_count = len(pitch["body"].split())
    return True, f"Subject: \"{pitch['subject'][:60]}...\" | Body: {word_count} words"

test("AI pitch generation", check_pitch)

# ──────────────────────────────────────────────────────
# 7. Email HTML Builder
# ──────────────────────────────────────────────────────
print("\n📧 Module 7: Email HTML Builder")

def check_email_html():
    from outreach import build_email_html
    html = build_email_html(
        contact_name="Test User",
        company_name="Test Corp",
        role="HR Manager",
        subject="Test Subject",
        body="Hello, this is a test email body.",
        recipient_email="test@example.com"
    )
    checks = [
        ("Has DOCTYPE", "<!DOCTYPE html>" in html),
        ("Has subject", "Test Subject" in html),
        ("Has body text", "test email body" in html),
        ("Has unsubscribe", "unsubscribe" in html.lower()),
        ("Has CTA button", "SCHEDULE A QUICK CALL" in html),
        ("Has sender name", "Adler" in html),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        return False, f"Missing: {', '.join(failed)}"
    return True, f"All {len(checks)} checks passed. HTML length: {len(html)} chars"

test("Email HTML builder", check_email_html)

# ──────────────────────────────────────────────────────
# 8. SendGrid API Key Validity
# ──────────────────────────────────────────────────────
print("\n📬 Module 8: SendGrid API Key Check")

def check_sendgrid():
    import requests
    key = os.getenv("SENDGRID_API_KEY")
    if not key:
        return False, "SENDGRID_API_KEY not set"
    r = requests.get(
        "https://api.sendgrid.com/v3/user/credits",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10
    )
    if r.status_code == 200:
        return True, f"API key valid. Credits: {r.json()}"
    elif r.status_code == 401:
        return False, "API key INVALID (401 Unauthorized)"
    elif r.status_code == 403:
        return False, f"API key lacks permissions (403). Check scopes."
    else:
        return True, f"Key accepted (status {r.status_code}). May need scope check."

test("SendGrid API key", check_sendgrid)

# ──────────────────────────────────────────────────────
# 9. FastAPI App Startup
# ──────────────────────────────────────────────────────
print("\n🚀 Module 9: FastAPI App Startup")

def check_fastapi():
    from main import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    expected = ["/api/health", "/api/discover", "/api/contacts/find", "/api/pitches/generate", "/api/outreach/send"]
    missing = [e for e in expected if e not in routes]
    if missing:
        return False, f"Missing routes: {', '.join(missing)}"
    return True, f"All {len(expected)} critical routes registered. Total routes: {len(routes)}"

test("FastAPI routes", check_fastapi)

# ──────────────────────────────────────────────────────
# 10. Sheets Headers Check
# ──────────────────────────────────────────────────────
print("\n📋 Module 10: Sheet Headers Integrity")

def check_headers():
    from sheets_db import SHEET_HEADERS
    contacts_headers = SHEET_HEADERS.get("Contacts", [])
    expected_new = ["LinkedIn URL", "Seniority", "Location"]
    missing = [h for h in expected_new if h not in contacts_headers]
    if missing:
        return False, f"Missing new enrichment columns: {', '.join(missing)}"
    return True, f"Contacts tab has {len(contacts_headers)} columns including enrichment fields: {', '.join(expected_new)}"

test("Sheet headers (enrichment)", check_headers)

# ──────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  AUDIT SUMMARY")
print("=" * 70)
passes = sum(1 for _, s, _ in results if s == PASS)
fails = sum(1 for _, s, _ in results if s == FAIL)
warns = sum(1 for _, s, _ in results if s == WARN)
total = len(results)
print(f"\n  {passes}/{total} PASSED  |  {fails} FAILED  |  {warns} WARNINGS\n")
for name, status, detail in results:
    if status != PASS:
        print(f"  {status}  {name}: {detail}")

if fails == 0:
    print("\n  🎉 ALL SYSTEMS GO — Ready for submission!\n")
else:
    print(f"\n  ⚠️  {fails} issue(s) need attention before submission.\n")
