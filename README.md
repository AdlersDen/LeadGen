# Adler's Den — Corporate Outreach MVP

An automated B2B lead intelligence and outreach system that identifies corporate prospects via Google Maps, extracts decision-makers via Hunter.io, and sends AI-personalized pitches via SendGrid.

## 🚀 Architecture
- **Frontend**: React (Vite, Tailwind, Radix UI, TanStack Query)
- **Backend**: Python FastAPI (Uvicorn)
- **Primary Database**: Google Sheets (via `gspread`)
- **Intelligence Modules**: 
  - Google Maps Places API (Company Discovery)
  - Hunter.io & Apollo.io (Contact Extraction)
  - Google Gemini 2.5 Flash-Lite (AI Pitch Generation)
  - SendGrid (Email Outreach)

---

## 🛠️ Setup & Installation

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   - Copy `.env.example` to `.env`.
   - Fill in your API keys for Google Maps, Hunter, Gemini, and SendGrid.
4. Google Sheets Integration:
   - Place your Google Service Account JSON file in `backend/service_account.json`.
   - Set the `GOOGLE_SHEET_ID` in your `.env`.
   - Share your Google Sheet with the client email address found in the service account JSON.

### 2. Frontend Setup
1. Navigate to the project root.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 🏗️ Production Features (Phase 5)
- **Async Processing**: Long-running API searches run in the background using FastAPI `BackgroundTasks`.
- **Reputation Guard**: Every domain is verified via DNS MX records before outreach to prevent bounces.
- **90-Day Cooldown**: Prevents duplicate outreach to the same contact within a 3-month window.
- **Deliverability Tracking**: Integrated webhooks for real-time update of email status (Delivered, Opened, Bounced) in Google Sheets.

---

## 📂 Google Sheets Structure
Ensure your master sheet has the following tabs (names are case-sensitive):
1. **Companies** (ID, Name, Industry, Address, Domain, Pincode, Employees, Status, Date)
2. **Contacts** (ID, Company ID, Full Name, Role, Email, Confidence, Status, Company Name, Date)
3. **Outreach Logs** (Log ID, Campaign ID, Contact ID, Contact Email, Contact Name, Company Name, Subject, Body, Status, Timestamp)
4. **Runs** (ID, Pincode, Location, Companies Found, Contacts Found, Emails Sent, Status, Timestamp)
