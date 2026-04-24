import gspread
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Constants
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

class SheetsDB:
    def __init__(self):
        self.client = None
        self.doc = None

    def connect(self):
        """Initializes connection to Google Sheets."""
        if not self.client or not self.doc:
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                logger.warning(f"Service account file {SERVICE_ACCOUNT_FILE} not found. DB mock mode.")
                return False
            if not SHEET_ID:
                logger.warning("GOOGLE_SHEET_ID not set. DB mock mode.")
                return False
                
            try:
                service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
                if service_account_json:
                    import json
                    info = json.loads(service_account_json)
                    self.client = gspread.service_account_from_dict(info)
                    logger.info("Connected to Sheets via GOOGLE_SERVICE_ACCOUNT_JSON env var.")
                else:
                    self.client = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
                    logger.info(f"Connected to Sheets via {SERVICE_ACCOUNT_FILE}.")
                
                self.doc = self.client.open_by_key(SHEET_ID)
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {e}", exc_info=True)
                self.client = None # Reset so we try again next time
                self.doc = None
                return False
        return True

    def _get_worksheet(self, title: str):
        """Helper to get a worksheet gracefully and ensure headers exist."""
        if not self.connect():
            return None
        try:
            ws = self.doc.worksheet(title)
            self._ensure_headers(ws, title)
            return ws
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{title}' not found in Google Sheet.")
            return None

    def _ensure_headers(self, ws, title: str):
        """Initializes headers if the sheet is completely empty."""
        first_row = ws.row_values(1)
        if not first_row:
            headers = []
            if title == "Companies":
                headers = ["ID", "Name", "Industry", "Address", "Domain", "Pincode", "Employee Count", "Status", "Created Date"]
            elif title == "Contacts":
                headers = ["ID", "Company ID", "Full Name", "Role", "Email", "Confidence Score", "Status", "Company Name", "Created Date"]
            elif title == "Outreach Logs":
                headers = ["ID", "Campaign ID", "Contact ID", "Contact Email", "Contact Name", "Company Name", "Subject", "Body", "Status", "Timestamp"]
            elif title == "Runs":
                headers = ["ID", "Pincode", "Location Name", "Companies Found", "Contacts Found", "Emails Sent", "Status", "Timestamp"]
            
            if headers:
                ws.append_row(headers)
                logger.info(f"Initialized headers for {title} tab.")

    # --- Companies Tab ---
    def get_companies(self):
        ws = self._get_worksheet("Companies")
        return ws.get_all_records() if ws else []

    def add_company(self, company_data: dict):
        """
        Expected keys: name, domain, address, pincode, industry, employee_count, phone, google_rating, status, source, notes
        """
        ws = self._get_worksheet("Companies")
        if not ws: return None

        record_id = str(uuid.uuid4())
        date_added = datetime.now(timezone.utc).isoformat()
        
        row = [
            record_id,
            company_data.get("name", ""),
            company_data.get("industry", ""),
            company_data.get("address", ""),
            company_data.get("domain", ""),
            company_data.get("pincode", ""),
            company_data.get("employee_count", ""),
            company_data.get("status", "discovered"),
            date_added
        ]
        ws.append_row(row)
        
        company_data["id"] = record_id
        company_data["created_date"] = date_added
        return company_data

    def add_companies_bulk(self, companies_data: list[dict]):
        """
        Appends multiple companies in a single API call to avoid timeouts.
        """
        ws = self._get_worksheet("Companies")
        if not ws or not companies_data: return []

        date_added = datetime.now(timezone.utc).isoformat()
        rows = []
        for company_data in companies_data:
            record_id = str(uuid.uuid4())
            row = [
                record_id,
                company_data.get("name", ""),
                company_data.get("industry", ""),
                company_data.get("address", ""),
                company_data.get("domain", ""),
                company_data.get("pincode", ""),
                company_data.get("employee_count", ""),
                company_data.get("status", "discovered"),
                date_added
            ]
            rows.append(row)
            company_data["id"] = record_id
            company_data["created_date"] = date_added
            
        ws.append_rows(rows)
        return companies_data

    # --- Contacts Tab ---
    def get_contacts(self):
        ws = self._get_worksheet("Contacts")
        return ws.get_all_records() if ws else []

    def add_contact(self, contact_data: dict, company_id: str):
        """
        Expected keys: company_name, full_name, role, email, confidence_score, status
        """
        ws = self._get_worksheet("Contacts")
        if not ws: return None

        record_id = str(uuid.uuid4())
        date_added = datetime.now(timezone.utc).isoformat()
        
        row = [
            record_id,
            company_id,
            contact_data.get("full_name", ""),
            contact_data.get("role", ""),
            contact_data.get("email", ""),
            contact_data.get("confidence_score", ""),
            contact_data.get("status", "discovered"),
            contact_data.get("company_name", ""),
            date_added
        ]
        ws.append_row(row)
        
        contact_data["id"] = record_id
        contact_data["company_id"] = company_id
        contact_data["created_date"] = date_added
        return contact_data

    # --- Outreach Logs Tab ---
    def get_outreach_logs(self):
        ws = self._get_worksheet("Outreach Logs")
        return ws.get_all_records() if ws else []
        
    def add_outreach_log(self, log_data: dict):
        """
        Expected keys: campaign_id, contact_id, subject, body, status, opened
        """
        ws = self._get_worksheet("Outreach Logs")
        if not ws: return None

        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        row = [
            record_id,
            log_data.get("campaign_id", ""),
            log_data.get("contact_id", ""),
            log_data.get("contact_email", ""),
            log_data.get("contact_name", ""),
            log_data.get("company_name", ""),
            log_data.get("subject", ""),
            log_data.get("body", ""),
            log_data.get("status", "sent"),
            timestamp
        ]
        ws.append_row(row)
        return record_id

    def is_contact_recently_emailed(self, email: str, days=90) -> bool:
        """PRD Duplicate Prevention: 90-day cooldown via get_all checks."""
        logs = self.get_outreach_logs()
        if not logs:
            return False
            
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        for record in logs:
            rec_email = record.get("Contact Email", "")
            if not rec_email or rec_email.strip().lower() != email.strip().lower():
                continue
                
            rec_time_str = record.get("Timestamp", "")
            if not rec_time_str:
                continue
                
            try:
                # Handle isoformat variations.
                rec_time = datetime.fromisoformat(rec_time_str.replace("Z", "+00:00"))
                if rec_time > cutoff_date:
                    return True  # Emailed recently!
            except Exception as e:
                logger.warning(f"Failed to parse timestamp {rec_time_str} in Outreach Logs.")
                
        return False

    # --- Runs Tab (To support frontend history) ---
    def get_runs(self):
        ws = self._get_worksheet("Runs")
        return ws.get_all_records() if ws else []
        
    def add_run(self, run_data: dict):
        ws = self._get_worksheet("Runs")
        if not ws: return None

        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        row = [
            record_id,
            run_data.get("pincode", ""),
            run_data.get("location_name", ""),
            run_data.get("companies_found", 0),
            run_data.get("contacts_found", 0),
            run_data.get("emails_sent", 0),
            run_data.get("status", "completed"),
            timestamp
        ]
        ws.append_row(row)
        
        run_data["id"] = record_id
        run_data["created_date"] = timestamp
        return run_data

# Singleton instance for the app to use
db = SheetsDB()
