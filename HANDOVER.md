# Adler's Den — Lead Intelligence App
## Handover & Usage Guide

---

## What This App Does

Automates B2B lead generation for Adler's Den corporate gifting:
1. **Discovers** companies near a pincode or inside a business complex
2. **Extracts** verified decision-maker contacts (HR, Marketing, Admin, etc.) via Apollo.io
3. **Sends** personalized outreach emails from `marketing@adlersden.com`

---

## Starting the App (Do This Every Time)

### Step 1 — Wake up the backend (Render)
The backend runs on Render's free tier and **sleeps after 15 minutes of inactivity**. You must wake it before using the app.

1. Open: `https://adlers-den-leadgen.onrender.com/health`
2. Wait for it to return `{"status": "ok"}` — this takes **30–90 seconds** on first load
3. Once you see that response, the backend is live

> If you skip this step, the frontend will appear to load but all actions (Discover, Extract, Send) will silently fail or time out.

### Step 2 — Open the frontend (Vercel)
1. Open: `https://adlersden-leadgen.vercel.app`
2. You're now on the Dashboard — the app is ready to use

---

## Full Workflow

### Module 1 — Discover Companies

**Go to:** Sidebar → **Discover**

**Two search modes:**

| Mode | When to use | Example |
|---|---|---|
| **Pincode** | Find all B2B companies near an area | `400021` (Nariman Point) |
| **Complex / Building** | Find companies inside a specific office building or IT park | `Maker Chambers`, `BKC`, `Mindspace Malad` |

**Optional filters:**
- **Industry** — select one or more (Event Management, Finance, IT/Tech, etc.) to narrow results. Leave blank for all industries.
- **Tier** — Tier A (high-value: rating ≥ 4.0 + has domain), Tier B (medium), Tier C (low signal). Default is A + B.

**Steps:**
1. Enter pincode or complex name
2. Select industry filter (optional)
3. Select tiers
4. Click **Discover**
5. Review the discovered companies — scroll through the cards
6. Click **Go to Contacts Extraction** or navigate to the Contacts page

---

### Module 2 — Extract Contacts

**Go to:** Sidebar → **Contacts** → click **Extract Contacts** button (top right)

1. A panel opens showing all companies that haven't had contacts extracted yet
2. Select the companies you want (checkbox per row, or "Select All")
3. Max **20 companies per extraction run**
4. Click **Extract for Selected**
5. Wait — extraction takes approximately **5–7 seconds per company** (Apollo.io API)
6. A progress bar shows status. Do not close the tab while running.

**What happens during extraction:**
- Apollo.io searches for decision-makers at each company's domain
- Targets: HR, Marketing, Admin, Procurement, Operations, Leadership
- Falls back to Hunter.io if Apollo returns nothing
- Each contact is MX-verified before being saved
- Up to **3 contacts per company** are saved

**After extraction:**
- Contacts appear in the table below
- Columns: Name, Role, Company, Email, Phone, Location, LinkedIn, Confidence, Status

**Useful table features:**
- **Search bar** — filter by name, company, or email
- **Group by Role** button — groups contacts into HR & People / Marketing & Brand / Admin & Procurement / Sales & BD / Operations / Leadership

---

### Module 3 — Send Outreach Emails

**Go to:** Sidebar → **Outreach**

1. Select contacts to email (checkbox per row, or select all)
2. Review or edit the **Subject** and **Email Body** (pre-filled with a template)
3. Click **Send**
4. Emails are sent from `marketing@adlersden.com` via Resend
5. A **90-day cooldown** is enforced per contact — the same person won't receive another email for 90 days (shown as "In Cooldown" badge)
6. **Daily send limit: 50 emails/day** (increase `DAILY_SEND_LIMIT` in Render env vars when ready to scale)

---

### Module 4 — View Run History

**Go to:** Sidebar → **Run History**

Shows a log of every extraction and outreach run with timestamps, company counts, and status.

---

### Module 5 — Companies List

**Go to:** Sidebar → **Companies**

Full list of all discovered companies with their tier, domain, rating, and extraction status. Use this to check what's already been processed.

---

## Important Limits & Gotchas

| Limit | Value | Where to change |
|---|---|---|
| Max companies per extraction | 20 | Hardcoded (UI enforced) |
| Daily email send limit | 50/day | `DAILY_SEND_LIMIT` env var on Render |
| Contact cooldown period | 90 days | Hardcoded |
| Apollo credits | Pay-per-unlock | Apollo.io billing dashboard |
| Resend free tier | 3,000 emails/month | Upgrade at resend.com |

---

## What Gets Filtered Out (Discovery)

The app automatically excludes:
- Residential societies, apartments, co-op housing
- Government bodies, PSUs (MSEB, BSNL, NTPC, etc.)
- Schools, coaching classes, tuition centres
- Restaurants, cafes, hotels
- Individual doctors, dental clinics
- Salons, spas, gyms
- Small retail jewellers
- Religious places, transit hubs, parks

---

## Where Data Is Stored

All data lives in **Google Sheets** (not a traditional database):
- Sheet: `test001` (shared with the service account)
- Tabs: `Companies`, `Contacts`, `Outreach`, `Runs`

To view raw data: open the Google Sheet directly from Google Drive.

---

## Key URLs

| Service | URL |
|---|---|
| **Frontend (Vercel)** | `https://adlersden-leadgen.vercel.app` |
| **Backend health check** | `https://adlers-den-leadgen.onrender.com/health` |
| **GitHub repo** | `https://github.com/AdlersDen/LeadGen` |
| **Google Sheet (database)** | Open from Google Drive — sheet named `test001` |
| **Render dashboard** | `https://dashboard.render.com` |
| **Resend dashboard** | `https://resend.com` |
| **Apollo.io** | `https://app.apollo.io` |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| App loads but nothing works | Backend is asleep | Open the `/health` URL and wait for it to wake |
| Discovery returns 0 results | Google Maps found nothing in that area | Try a broader pincode or remove industry filter |
| Contacts extraction shows 0 contacts | Apollo found no matching profiles | Try a different company, or the domain may be too small for Apollo's DB |
| Email says "daily limit reached" | 50/day cap hit | Wait until tomorrow or increase `DAILY_SEND_LIMIT` on Render |
| Email going to spam | Sender reputation issue | Check Resend dashboard logs for bounce/spam reports |
| LinkedIn column empty | Apollo didn't return LinkedIn for that contact | These get populated for newly extracted contacts going forward |

---

## Environment Variables (Render)

If you need to reconfigure the backend, these are the environment variables set on Render:

| Variable | Purpose |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Company discovery via Google Places |
| `APOLLO_API_KEY` | Contact extraction (primary) |
| `HUNTER_API_KEY` | Contact extraction (fallback) |
| `RESEND_API_KEY` | Email sending |
| `GOOGLE_SHEETS_ID` | Which Google Sheet to write to |
| `DAILY_SEND_LIMIT` | Max emails per day (default: 50) |

---

*Last updated: June 2026*
