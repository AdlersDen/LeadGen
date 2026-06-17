# Adler's Den — Lead Intelligence Engine
## Complete Technical Notes & Self-Learning Document

---

# 1. What We Built & Why

Adler's Den is a corporate gifting startup. The manual problem was: someone had to Google companies, find HR/marketing contacts, write personalised emails, and track responses — all by hand, for hundreds of companies. This app automates that entire pipeline.

**The pipeline in one line:**
> Find companies near a location → find the right person's email → send a personalised pitch → track what happened

---

# 2. System Architecture

## Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                           │
│                   React App (Vercel CDN)                        │
│          adlersden-leadgen.vercel.app                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │  HTTPS API calls (fetch/axios)
                          │  e.g. POST /api/discover
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVER                              │
│              Python FastAPI (Render.com)                        │
│          adlers-den-leadgen.onrender.com                        │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │discovery │  │contacts  │  │pitches   │  │outreach  │       │
│  │ .py      │  │ .py      │  │ .py      │  │ .py      │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼──────────────┼─────────────┘
        │             │             │              │
        ▼             ▼             ▼              ▼
  Google Maps    Apollo.io     Google Gemini    Resend.com
  Places API     Hunter.io     (AI email gen)   (email send)
  (discovery)    (contacts)

        All modules read/write to:
        ┌─────────────────────┐
        │   Google Sheets     │
        │   (sheets_db.py)    │
        │   Tab: Companies    │
        │   Tab: Contacts     │
        │   Tab: Outreach     │
        │   Tab: Runs         │
        │   Tab: Blocklist    │
        └─────────────────────┘
```

## Key Concept: Why Google Sheets as a Database?
Instead of PostgreSQL/MongoDB, we use Google Sheets via the `gspread` library. Reason: the client (Adler's Den team) can open the spreadsheet and see/edit data without any technical knowledge. It's a trade-off — Google Sheets is slower and has API rate limits, but it's zero cost and immediately accessible to non-technical users.

---

# 3. Tech Stack Explained

## Frontend
| Technology | What It Does | Why We Used It |
|---|---|---|
| **React 18** | UI framework | Industry standard, component-based |
| **Vite** | Build tool + dev server | Much faster than CRA, instant hot reload |
| **TanStack Query** | Server state management | Handles loading/error/cache states automatically |
| **shadcn/ui** | UI component library | Pre-built accessible components (Table, Button, Badge, etc.) |
| **Tailwind CSS** | Styling | Utility classes, no separate CSS files |
| **Lucide React** | Icons | Clean icon library used throughout |
| **Sonner** | Toast notifications | Lightweight toast library |

## Backend
| Technology | What It Does | Why We Used It |
|---|---|---|
| **Python 3** | Language | Strong for API integrations, easy to read |
| **FastAPI** | Web framework | Auto-generates docs, fast, modern Python |
| **Uvicorn** | ASGI server | Runs FastAPI in production |
| **Pydantic** | Request validation | Validates incoming JSON automatically |
| **gspread** | Google Sheets client | Read/write Sheets like a database |
| **tldextract** | Domain parsing | Extracts root domain from any URL safely |
| **dnspython** | DNS verification | MX record checks to validate email domains |
| **requests** | HTTP client | Calls external APIs (Google Maps, Apollo, Hunter) |

## External APIs
| API | Purpose | Free Tier |
|---|---|---|
| **Google Maps Places API** | Find companies near a pincode | $200 credit/month (~40k calls) |
| **Apollo.io** | Find decision-maker contacts + emails | 50 credits/month free |
| **Hunter.io** | Fallback contact finder | 25 searches/month free |
| **Google Gemini** | AI email pitch generation | Free (Flash model) |
| **Resend** | Send emails reliably | 3,000 emails/month free |
| **Google Sheets API** | Database via gspread | Free |

## Deployment
| Service | What Runs There | URL |
|---|---|---|
| **Vercel** | React frontend | adlersden-leadgen.vercel.app |
| **Render** | Python FastAPI backend | adlers-den-leadgen.onrender.com |
| **GitHub** | Source code | github.com/AdlersDen/LeadGen |

---

# 4. Module-by-Module Breakdown

## Module 1 — Company Discovery (`discovery.py`)

**Job:** Given a pincode OR a building/complex name → return a filtered list of B2B companies.

### Two Search Modes

```
MODE A: Pincode
──────────────
User enters "400021"
        │
        ▼
Google Geocoding API
converts pincode → lat/lng coordinates
(19.0760° N, 72.8777° E = Nariman Point)
        │
        ▼
Google Places Nearby Search API
searches radius (default 2km) around those coords
returns up to 60 establishments
        │
        ▼
_is_b2b_company() filter runs on each result
(removes schools, hospitals, restaurants, etc.)
        │
        ▼
_extract_domain() calls Places Details API
gets website + phone for each company
        │
        ▼
_score_tier() assigns A/B/C tier
(A = rating ≥ 4.0 AND has domain)
        │
        ▼
Results saved to Google Sheets → returned to frontend

MODE B: Complex Name
─────────────────────
User enters "Maker Chambers"
        │
        ▼
Google Find Place API
converts name → lat/lng + viewport
        │
        ▼
Google Text Search API
searches for "offices in Maker Chambers"
        │
        ▼
Haversine distance filter
(drops results outside the complex boundary)
        │
        ▼
Address verification filter
(drops results that mention a different complex)
        │
        ▼
Same _is_b2b_company() + domain + tier pipeline
```

### The Filter Logic (`_is_b2b_company`)
```
For each Google Places result:

1. Check name against NAME_BLOCKLIST_PATTERNS
   → blocks: "society", "coaching", "dr. ", "jewellers", etc.

2. Check Google type tags against BLOCKLIST_TYPES
   → blocks: school, restaurant, dentist, lodging, etc.

3. If passes both → keep it (default = include)
```

### Industry Filter (How It Works)
When user selects "Event Management":
```python
INDUSTRY_KEYWORDS = {
    "events": "event management",
    "finance": "finance banking",
    "tech": "IT software technology",
    ...
}
# This keyword gets passed to Google Places as:
# params["keyword"] = "event management"
# Google then prioritises event-related places in results
```

### Tier Scoring
```
Tier A → Google rating ≥ 4.0  AND  has a website domain
Tier B → Google rating ≥ 3.5  OR   has a website domain
Tier C → everything else (low signal)
```

---

## Module 2 — Contact Intelligence (`contacts.py`)

**Job:** Given a company name + domain → find verified decision-maker emails.

### Lookup Flow
```
Input: company_name="Reliance Industries", domain="ril.com"
        │
        ▼
Step 1: Apollo.io People Search
        POST /v1/mixed_people/search
        payload: { q_organization_domains_list: ["ril.com"] }
        returns: up to 10 people with names + titles (emails obfuscated)
        │
        ├─ If returns people:
        │       │
        │       ▼
        │  Filter by role priority
        │  (HR > Marketing > Admin > Operations > CEO)
        │       │
        │       ▼
        │  Apollo.io Bulk Email Unlock
        │  POST /v1/people/bulk_match
        │  payload: { details: [{id: "person_id"}], reveal_personal_emails: false }
        │  returns: full profiles with unlocked emails
        │       │
        │       ▼
        │  Build contact list → run through clean_contact_data()
        │
        └─ If returns nothing:
                │
                ▼
        Step 2: Hunter.io Fallback
        GET /v2/domain-search?domain=ril.com
        returns: emails found on the web for that domain
                │
                ▼
        Filter: confidence ≥ 50, target roles only

        Both paths:
                │
                ▼
        clean_contact_data() — MX record verification
        (checks the email domain actually has mail servers)
        Drops contacts with invalid/fake domains
                │
                ▼
        Return max 3 contacts per company
```

### Role Priority System
```python
TIER_1 (priority 1): HR, People, Culture, Marketing, CMO, Admin, Procurement
TIER_2 (priority 2): Operations, COO, Sales, Business Development
TIER_3 (priority 3): CEO, Founder, Director, MD

# Lower number = higher priority
# Contacts are sorted so HR/Marketing always comes first
```

### Why Root Domain Normalization?
```
Problem: Google Places returns "stores.maccosmetics.in"
Apollo rejects subdomains → 422 error

Fix: tldextract library
tldextract.extract("stores.maccosmetics.in")
→ domain="maccosmetics", suffix="in"
→ root domain = "maccosmetics.in"

Apollo now accepts it ✅
```

---

## Module 3 — AI Pitch Generation (`pitches.py`)

**Job:** Generate a personalised outreach email using AI.

```
Input: contact_name, role, company_name
        │
        ▼
Google Gemini 2.5 Flash-Lite API
Prompt includes: role, company name, Adler's Den description
Returns: subject + body personalised for that role
        │
        │  ALSO runs in parallel:
        ▼
Google Sheets "Templates" tab
Looks up pre-written template for the role category
(HR template, Marketing template, etc.)
        │
        ▼
Returns BOTH to frontend:
  - ai_pitch (Gemini-generated, dynamic)
  - predefined_pitch (template-based, consistent)
User picks which one to send
```

---

## Module 4 — Email Outreach (`outreach.py`)

**Job:** Send the email, enforce limits, log the result.

```
Input: contact details + subject + body
        │
        ▼
Blocklist check (Google Sheets "Blocklist" tab)
→ if email unsubscribed → reject with 409 error
        │
        ▼
90-day cooldown check
→ if emailed within last 90 days → reject with 409 error
        │
        ▼
Daily send limit check
→ if sent ≥ 50 today → reject (rate limit)
        │
        ▼
build_email_html()
→ wraps plain text body in premium HTML template
→ dark brown header (#2C1810), beige background (#F0EBE3)
→ CTA button → Calendly link
→ unsubscribe footer (compliance)
        │
        ▼
Resend API
POST https://api.resend.com/emails
from: "Adler's Den <marketing@adlersden.com>"
to: [recipient]
        │
        ▼
Log to Google Sheets "Outreach" tab
(contact_id, email, subject, status="sent", message_id)
        │
        ▼
Return success to frontend
```

### Email Deliverability Stack
```
marketing@adlersden.com → DNS: adlersden.com

SPF Record (TXT):
"v=spf1 include:amazonses.com ~all"
→ tells mail servers: "Resend/AWS SES is allowed to send from this domain"

DKIM Record (TXT):
resend._domainkey.adlersden.com → p=MIGfMA0G...
→ cryptographic signature that proves the email wasn't tampered with

DMARC Record (TXT):
_dmarc.adlersden.com → "v=DMARC1; p=none;"
→ policy for what to do when SPF/DKIM fail (none = monitor only)

Result: Corporate mail servers (Microsoft 365, Google Workspace)
accept the email instead of quarantining it
```

---

# 5. Database Schema (Google Sheets)

## Companies Tab
| Column | Type | Description |
|---|---|---|
| ID | UUID | Unique identifier |
| Name | String | Company name from Google Maps |
| Address | String | Full address |
| Pincode | String | Source pincode |
| Domain | String | Company website domain |
| Phone | String | Company phone from Google Places |
| Google Rating | Float | 1.0–5.0 star rating |
| Tier | A/B/C | Lead quality score |
| Industry | String | Google Places type tags |
| Status | String | discovered / no_contacts_found |
| Contacts Extracted | Yes/No | Whether contacts have been pulled |
| Source | String | "Google Maps" |
| Created Date | Timestamp | When discovered |

## Contacts Tab
| Column | Type | Description |
|---|---|---|
| ID | UUID | Unique identifier |
| Company ID | UUID | Links to Companies tab |
| Company Name | String | Denormalized for easy reading |
| Full Name | String | Person's name |
| Role | String | Job title |
| Email | String | Work email |
| Phone | String | Direct dial (if available) |
| LinkedIn URL | String | Profile URL |
| Location | String | City, State |
| Confidence Score | Int | 0–100, how confident we are the email is valid |
| Source | String | apollo.io / hunter.io |
| Status | String | verified |
| Last Contacted | Date | Last email sent date |
| Created Date | Timestamp | When extracted |

## Outreach Tab
| Column | Type | Description |
|---|---|---|
| ID | UUID | Unique identifier |
| Campaign ID | String | Groups emails by campaign |
| Contact ID | UUID | Links to Contacts tab |
| Contact Email | String | Recipient |
| Company Name | String | Company name |
| Subject | String | Email subject |
| Body | String | Email body (plain text) |
| Status | String | sent / delivered / opened / bounced |
| Message ID | String | Resend's message ID for tracking |
| Sent At | Timestamp | When sent |

---

# 6. All API Endpoints

**Base URL:** `https://adlers-den-leadgen.onrender.com`

## Read Endpoints (GET)
```
GET  /health                        → {"status": "ok"} — wake-up check
GET  /api/health                    → same
GET  /api/companies                 → all companies from Sheets
GET  /api/companies/pending         → companies with no contacts extracted
GET  /api/contacts                  → all contacts from Sheets
GET  /api/contacts/cooldown-status  → map of email → bool (in 90-day cooldown)
GET  /api/outreach                  → all outreach logs
GET  /api/runs                      → all discovery runs with aggregated stats
GET  /api/dashboard-stats           → counts for dashboard cards

Diagnostic (debugging only):
GET  /api/debug/version             → git commit hash of what's deployed
GET  /api/debug/apollo-test?domain= → test Apollo API key directly
```

## Write Endpoints (POST)
```
POST /api/discover
  Body: { pincode?, complex_name?, radius_km, industries[], tiers[] }
  → Calls Google Maps, saves companies, returns list

POST /api/contacts/find
  Body: { company_id, company_name, domain }
  → Calls Apollo/Hunter for one company, saves contacts

POST /api/contacts/bulk-find
  Body: { limit: 5 }
  → Extracts contacts for next N unprocessed companies

POST /api/contacts/extract-selected
  Body: { company_ids: ["id1", "id2", ...] }
  → Extracts contacts for specific user-selected companies (max 20)

POST /api/pitches/generate
  Body: { contact_name, role, company_name }
  → Returns AI pitch + template-based pitch

POST /api/outreach/send
  Body: { contact_id, contact_name, contact_email, company_name, role, subject, body }
  → Sends email via Resend, logs to Sheets

POST /api/unsubscribe
  Body: { email }
  → Adds email to blocklist tab
```

---

# 7. Request/Response Flow (Full Example)

**User clicks "Extract Contacts" for Reliance General Insurance:**

```
Browser                  Vercel Frontend              Render Backend
   │                           │                            │
   │── clicks Extract ────────▶│                            │
   │                           │── POST /api/contacts/ ────▶│
   │                           │   extract-selected         │
   │                           │   body: {company_ids:      │
   │                           │   ["uuid-123"]}            │
   │                           │                            │── get_companies()
   │                           │                            │   from Sheets
   │                           │                            │
   │                           │                            │── find_contacts(
   │                           │                            │   "Reliance General",
   │                           │                            │   "reliancegeneral.co.in")
   │                           │                            │
   │                           │                            │── Apollo Step 1:
   │                           │                            │   POST mixed_people/search
   │                           │                            │   {q_org_domains: ["reliancegeneral.co.in"]}
   │                           │                            │◀── 8 people returned
   │                           │                            │
   │                           │                            │── Filter: 3 match target roles
   │                           │                            │
   │                           │                            │── Apollo Step 2:
   │                           │                            │   POST people/bulk_match
   │                           │                            │   {details: [{id:...},{id:...},{id:...}]}
   │                           │                            │◀── emails unlocked
   │                           │                            │
   │                           │                            │── clean_contact_data()
   │                           │                            │   MX record check on domain
   │                           │                            │
   │                           │                            │── add_contact() x3
   │                           │                            │   write to Sheets
   │                           │                            │
   │                           │◀── {queued: 1,            │
   │                           │    contacts found: 3} ─────│
   │◀── table refreshes ───────│                            │
```

---

# 8. Key Concepts to Remember

## CORS (Cross-Origin Resource Sharing)
Your frontend is on `vercel.app` and backend is on `onrender.com` — different domains. By default browsers block this. FastAPI's `CORSMiddleware` explicitly allows the Vercel domain to make requests to the backend.

```python
# main.py — without this, every API call fails in browser
app.add_middleware(CORSMiddleware, allow_origins=["https://adlersden-leadgen.vercel.app"])
```

## Why Render Free Tier Sleeps
Render's free plan spins down after 15 mins of inactivity to save compute. First request wakes it (takes 30–90s). This is why you must open `/health` first before using the app.

## Apollo's Two-Step Pattern
Apollo doesn't give you emails in the search — it deliberately hides them. You must:
1. Search to find WHO works there (get their person IDs)
2. Unlock/reveal their emails separately (costs credits)

This is Apollo's business model — search is free, email reveal costs credits.

## Why 90-Day Cooldown?
Sending the same person multiple emails quickly = spam complaint = your domain gets blacklisted. 90 days gives enough gap to be professional and avoid spam filters.

## Haversine Formula
Used to calculate the straight-line distance between two GPS coordinates. We use it to check if a Google Places result is actually inside the business complex we searched for, not just nearby.

```
d = 2R × arcsin(√(sin²(Δlat/2) + cos(lat1)×cos(lat2)×sin²(Δlng/2)))
```
R = 6,371,000 metres (Earth's radius)

---

# 9. Environment Variables

Set on Render (backend) and Vercel (frontend):

**Backend (Render):**
```
GOOGLE_MAPS_API_KEY   → Places API, Geocoding API
APOLLO_API_KEY        → Contact search + email unlock
HUNTER_API_KEY        → Fallback contact finder
RESEND_API_KEY        → Email sending
GOOGLE_SHEETS_ID      → Spreadsheet ID from the URL
DAILY_SEND_LIMIT      → Max emails/day (default 50)
FRONTEND_URL          → Allowed CORS origin (optional)
CALENDAR_LINK         → Calendly URL in email CTA
SENDER_NAME           → Name in email signature
SENDER_TITLE          → Title in email signature
SENDER_PHONE          → Phone in email signature
```

**Frontend (Vercel):**
```
VITE_API_BASE_URL     → Points to the Render backend URL
```

---

# 10. File Structure

```
Part B v2/
├── src/                          ← React frontend
│   ├── pages/
│   │   ├── Dashboard.jsx         ← Stats overview
│   │   ├── Discover.jsx          ← Company discovery UI
│   │   ├── Contacts.jsx          ← Contact table + extraction
│   │   ├── Outreach.jsx          ← Email sending UI
│   │   └── RunHistory.jsx        ← Past runs log
│   ├── components/
│   │   ├── ui/                   ← shadcn/ui components
│   │   └── shared/               ← StatusBadge, RunAlert, etc.
│   ├── api/
│   │   └── apiClient.js          ← Axios wrapper pointing to backend
│   └── main.jsx                  ← App entry point
│
├── backend/
│   ├── main.py                   ← FastAPI app + all endpoints
│   ├── discovery.py              ← Module 1: Google Maps pipeline
│   ├── contacts.py               ← Module 2: Apollo/Hunter pipeline
│   ├── pitches.py                ← Module 3: Gemini AI pitch
│   ├── outreach.py               ← Module 4: Resend email
│   ├── sheets_db.py              ← Google Sheets CRUD
│   ├── cleaning.py               ← Contact data cleaning + MX check
│   ├── webhooks.py               ← Email event webhooks (delivered/opened)
│   └── requirements.txt          ← Python dependencies
│
├── vercel.json                   ← Frontend routing config
├── HANDOVER.md                   ← User guide
└── PROJECT_NOTES.md              ← This document
```

---

# 11. Things That Broke and What I Learned

| Problem | Root Cause | Fix | Lesson |
|---|---|---|---|
| Apollo returning 422 | Subdomain passed instead of root domain | tldextract to normalize | Always normalize external API inputs |
| Hunter hammering rate limit | Apollo failing → Hunter called for every company → immediate 429 | 5-min global cooldown + 1s pacing | Protect fallback APIs with cooldowns |
| Render not deploying | Service was set to Node runtime, not Python | Changed runtime in Render settings | Always verify the runtime environment |
| Emails not reaching corporate inboxes | Missing SPF/DKIM/DMARC DNS records | Added 3 CNAMEs + DMARC TXT to DNS | Email auth is mandatory for B2B |
| Emails quarantined by Microsoft 365 | SendGrid shared IP on spamcop blacklist | Switched to Resend (clean IPs) | Shared IPs = shared reputation risk |
| Discovery returning cities/localities | Google Places returns "Mumbai" as a result | Added locality/political to BLOCKLIST_TYPES | Google Places returns everything — you must filter |
| LinkedIn URLs empty | Apollo Step 2 (bulk_match) omits linkedin_url | Saved Step 1 URLs in a dict as fallback | Never trust a single API response — build fallbacks |
| Two Vercel accounts | Deployed to wrong account | Linked CLI to correct project | Always verify `vercel whoami` |

---

*Written: June 2026*
*Stack: React 18 + Vite + FastAPI + Google Sheets + Apollo + Resend*
