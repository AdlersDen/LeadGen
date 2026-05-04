import gspread
import os
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

SHEET_HEADERS = {
    "Companies": [
        "ID", "Name", "Industry", "Address", "Domain", "Phone", "Pincode",
        "Employee Count", "Tier", "Contacts Extracted", "Status", "Created Date",
    ],
    "Contacts": [
        "ID", "Company ID", "Full Name", "Role", "Email",
        "Confidence Score", "Status", "Company Name", "Source", "Created Date",
    ],
    "Outreach Logs": [
        "ID", "Campaign ID", "Contact ID", "Contact Email", "Contact Name",
        "Company Name", "Subject", "Body", "Status", "Message ID", "Timestamp",
    ],
    "Runs": [
        "ID", "Pincode", "Complex Name", "Location Name", "Companies Found",
        "Contacts Found", "Emails Sent", "Status", "Timestamp",
    ],
    "Blocklist": ["Email", "Timestamp"],
}

class SheetsDB:
    def __init__(self):
        self.client = None
        self.doc = None

    def connect(self):
        """Initializes connection to Google Sheets."""
        if self.client and self.doc:
            return True

        if not SHEET_ID:
            logger.warning("GOOGLE_SHEET_ID not set. DB mock mode.")
            return False

        try:
            # Priority 1: JSON string in env var (Render production)
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                info = json.loads(service_account_json)
                self.client = gspread.service_account_from_dict(info)
                logger.info("Connected to Sheets via GOOGLE_SERVICE_ACCOUNT_JSON env var.")

            # Priority 2: Local file (local dev)
            elif os.path.exists("service_account.json"):
                self.client = gspread.service_account(filename="service_account.json")
                logger.info("Connected to Sheets via service_account.json file.")

            else:
                logger.error(
                    "No Google credentials found. "
                    "Set GOOGLE_SERVICE_ACCOUNT_JSON env var on Render, "
                    "or place service_account.json in project root for local dev."
                )
                return False

            self.doc = self.client.open_by_key(SHEET_ID)
            return True

        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
            self.client = None
            self.doc = None
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}", exc_info=True)
            self.client = None
            self.doc = None
            return False

    def _get_worksheet(self, title: str):
        """Helper to get a worksheet gracefully and ensure headers exist. Creates missing worksheets."""
        if not self.connect():
            return None
        try:
            ws = self.doc.worksheet(title)
            self._ensure_headers(ws, title)
            return ws
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Worksheet '{title}' not found. Creating it...")
            try:
                # Create with 1 row and enough columns for headers
                headers = SHEET_HEADERS.get(title, ["ID"])
                ws = self.doc.add_worksheet(title=title, rows="100", cols=str(max(20, len(headers))))
                self._ensure_headers(ws, title)
                return ws
            except Exception as e:
                logger.error(f"Failed to create worksheet '{title}': {e}")
                return None

    def _ensure_headers(self, ws, title: str):
        """Initializes missing headers while preserving any existing column order."""
        first_row = ws.row_values(1)
        expected_headers = SHEET_HEADERS.get(title, [])
        if not expected_headers:
            return

        if not first_row:
            ws.append_row(expected_headers)
            logger.info(f"Initialized headers for {title} tab.")
            return

        missing_headers = [header for header in expected_headers if header not in first_row]
        if not missing_headers:
            return

        for idx, header in enumerate(missing_headers, start=len(first_row) + 1):
            ws.update_cell(1, idx, header)
        logger.info(f"Added missing headers for {title}: {', '.join(missing_headers)}")

    def _get_headers(self, ws) -> list[str]:
        headers = ws.row_values(1)
        return headers if headers else []

    def _build_row_for_headers(self, headers: list[str], data: dict) -> list:
        return [data.get(header, "") for header in headers]

    def _append_record(self, ws, data: dict):
        headers = self._get_headers(ws)
        if not headers:
            return
        ws.append_row(self._build_row_for_headers(headers, data))

    def _append_records(self, ws, rows: list[dict]):
        headers = self._get_headers(ws)
        if not headers or not rows:
            return
        ws.append_rows([self._build_row_for_headers(headers, row) for row in rows])

    # --- Companies Tab ---
    def get_companies(self):
        ws = self._get_worksheet("Companies")
        if not ws:
            return []
        records = ws.get_all_records()
        # ── Column-swap normalizer ────────────────────────────────────────────
        # Older rows written before the contacts_extracted column fix have:
        #   Status          = ISO timestamp  (was Created Date)
        #   Contacts Extracted = "discovered" (was Status)
        #   Created Date    = ""             (was Contacts Extracted)
        # Detect and fix at read time so the UI is always correct.
        for r in records:
            status = r.get("Status", "")
            contacts_extracted = r.get("Contacts Extracted", "")
            created_date = r.get("Created Date", "")
            # A Status that looks like an ISO timestamp is actually a Created Date
            if status and "T" in str(status) and ":" in str(status):
                r["Created Date"] = status           # move timestamp to Created Date
                r["Status"] = contacts_extracted or "discovered"  # recover real status
                r["Contacts Extracted"] = ""         # clear the incorrectly set value
        return records

    def get_pending_companies(self):
        """Returns only companies where Contacts Extracted is not 'Yes' and status is not 'no_contacts_found'."""
        all_companies = self.get_companies()
        return [
            c for c in all_companies
            if str(c.get("Contacts Extracted", "")).strip().lower() != "yes" 
            and str(c.get("Status", "")).strip().lower() != "no_contacts_found"
        ]

    def add_company(self, company_data: dict):
        ws = self._get_worksheet("Companies")
        if not ws:
            return None

        record_id = str(uuid.uuid4())
        date_added = datetime.now(timezone.utc).isoformat()

        row_data = {
            "ID": record_id,
            "Name": company_data.get("name", ""),
            "Industry": company_data.get("industry", ""),
            "Address": company_data.get("address", ""),
            "Domain": company_data.get("domain", ""),
            "Phone": company_data.get("phone", ""),
            "Pincode": company_data.get("pincode", ""),
            "Employee Count": company_data.get("employee_count", ""),
            "Tier": company_data.get("tier", ""),
            "Contacts Extracted": company_data.get("contacts_extracted", ""),
            "Status": company_data.get("status", "discovered"),
            "Created Date": date_added,
        }
        self._append_record(ws, row_data)

        company_data["id"] = record_id
        company_data["created_date"] = date_added
        return company_data

    def add_companies_bulk(self, companies_data: list[dict]):
        """Appends multiple companies in a single API call, skipping duplicates."""
        ws = self._get_worksheet("Companies")
        if not ws or not companies_data:
            return []

        # --- Deduplication: fetch existing names + domains in one call ---
        # col_values is zero-cost compared to get_all_records() since we only
        # pull two columns instead of every cell in the sheet.
        existing_names = {v.strip().lower() for v in ws.col_values(2) if v.strip()}   # col B = Name
        existing_domains = {v.strip().lower() for v in ws.col_values(5) if v.strip()} # col E = Domain

        new_companies = []
        for company in companies_data:
            name   = (company.get("name")   or "").strip().lower()
            domain = (company.get("domain") or "").strip().lower()

            # Skip if the name already exists, or if it has a domain that already exists
            if name in existing_names:
                logger.info(f"Skipping duplicate company (name): {company.get('name')}")
                continue
            if domain and domain in existing_domains:
                logger.info(f"Skipping duplicate company (domain): {domain}")
                continue

            new_companies.append(company)

        if not new_companies:
            logger.info("Deduplication: 0 new companies to add.")
            return []

        # --- Build and append only the new rows ---
        date_added = datetime.now(timezone.utc).isoformat()
        rows = []
        for company_data in new_companies:
            record_id = str(uuid.uuid4())
            rows.append({
                "ID": record_id,
                "Name": company_data.get("name", ""),
                "Industry": company_data.get("industry", ""),
                "Address": company_data.get("address", ""),
                "Domain": company_data.get("domain", ""),
                "Phone": company_data.get("phone", ""),
                "Pincode": company_data.get("pincode", ""),
                "Employee Count": company_data.get("employee_count", ""),
                "Tier": company_data.get("tier", ""),
                "Contacts Extracted": company_data.get("contacts_extracted", ""),
                "Status": company_data.get("status", "discovered"),
                "Created Date": date_added,
            })
            company_data["id"] = record_id
            company_data["created_date"] = date_added

        self._append_records(ws, rows)
        logger.info(f"Added {len(new_companies)} new companies to Sheets.")
        return new_companies

    def mark_contacts_extracted_bulk(self, company_ids: list[str]):
        """Marks multiple companies as having had their contacts extracted in a single batch update."""
        ws = self._get_worksheet("Companies")
        if not ws or not company_ids:
            return

        all_values = ws.get_all_values()
        if not all_values:
            return

        headers = all_values[0]
        
        # Ensure 'Contacts Extracted' column exists
        if "Contacts Extracted" not in headers:
            col_idx = len(headers) + 1
            ws.update_cell(1, col_idx, "Contacts Extracted")
            headers.append("Contacts Extracted")
            # Update all_values so we know the new length
            for row in all_values:
                while len(row) < col_idx:
                    row.append("")
        else:
            col_idx = headers.index("Contacts Extracted") + 1

        id_col_idx = headers.index("ID") if "ID" in headers else 0
        
        # Find row indices for the given company IDs
        company_ids_set = set(company_ids)
        rows_to_update = []
        for row_idx, row in enumerate(all_values):
            if row_idx == 0: continue # Skip header
            if row[id_col_idx] in company_ids_set:
                rows_to_update.append(row_idx + 1) # +1 for 1-based index in gspread
        
        if not rows_to_update:
            return

        # Simple column letter conversion (works for A-Z)
        import string
        col_letter = string.ascii_uppercase[col_idx - 1]

        # Prepare batch update data
        batch_data = []
        for row_num in rows_to_update:
            batch_data.append({
                'range': f"{col_letter}{row_num}",
                'values': [["Yes"]]
            })

        try:
            ws.batch_update(batch_data)
            logger.info(f"Marked {len(rows_to_update)} companies as contacts extracted.")
        except Exception as e:
            logger.error(f"Failed to batch update Contacts Extracted: {e}")

    def mark_company_status(self, company_id: str, status: str):
        """Updates the Status column for a specific company."""
        ws = self._get_worksheet("Companies")
        if not ws or not company_id:
            return

        all_values = ws.get_all_values()
        if not all_values:
            return

        headers = all_values[0]
        if "Status" not in headers or "ID" not in headers:
            logger.warning("mark_company_status: required columns not found in Companies.")
            return

        id_col_idx = headers.index("ID")
        status_col_idx = headers.index("Status") + 1  # 1-based index

        for row_idx, row in enumerate(all_values):
            if row_idx == 0:
                continue
            if len(row) > id_col_idx and row[id_col_idx] == company_id:
                try:
                    ws.update_cell(row_idx + 1, status_col_idx, status)
                    logger.info(f"Updated company {company_id} status to '{status}'.")
                except Exception as e:
                    logger.error(f"Failed to update company status: {e}")
                return
        logger.warning(f"mark_company_status: company {company_id} not found.")

    # --- Contacts Tab ---
    def get_contacts(self):
        ws = self._get_worksheet("Contacts")
        return ws.get_all_records() if ws else []

    def add_contact(self, contact_data: dict, company_id: str):
        ws = self._get_worksheet("Contacts")
        if not ws:
            return None

        record_id = str(uuid.uuid4())
        date_added = datetime.now(timezone.utc).isoformat()

        row_data = {
            "ID": record_id,
            "Company ID": company_id,
            "Full Name": contact_data.get("full_name", ""),
            "Role": contact_data.get("role", ""),
            "Email": contact_data.get("email", ""),
            "Confidence Score": contact_data.get("confidence_score", ""),
            "Status": contact_data.get("status", "verified"),
            "Company Name": contact_data.get("company_name", ""),
            "Source": contact_data.get("source", ""),
            "Created Date": date_added,
        }
        self._append_record(ws, row_data)

        contact_data["id"] = record_id
        contact_data["company_id"] = company_id
        contact_data["created_date"] = date_added
        return contact_data

    # --- Outreach Logs Tab ---
    def get_outreach_logs(self):
        ws = self._get_worksheet("Outreach Logs")
        return ws.get_all_records() if ws else []

    def add_outreach_log(self, log_data: dict):
        ws = self._get_worksheet("Outreach Logs")
        if not ws:
            return None

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
            log_data.get("message_id", ""),   # SendGrid X-Message-Id for webhook matching
            timestamp
        ]
        ws.append_row(row)
        return record_id

    def update_outreach_status(self, message_id: str, status: str):
        """
        Called by the SendGrid webhook to update delivery/open/bounce status.
        Finds the row in Outreach Logs whose Message ID matches and updates Status.
        """
        ws = self._get_worksheet("Outreach Logs")
        if not ws or not message_id:
            return

        all_values = ws.get_all_values()
        if not all_values:
            return

        headers = all_values[0]
        if "Message ID" not in headers or "Status" not in headers:
            logger.warning("update_outreach_status: required columns not found in Outreach Logs.")
            return

        msg_col_idx    = headers.index("Message ID") + 1   # 1-based for gspread
        status_col_idx = headers.index("Status") + 1

        import string
        status_col_letter = string.ascii_uppercase[status_col_idx - 1]

        for row_idx, row in enumerate(all_values):
            if row_idx == 0:
                continue  # skip header
            if len(row) >= msg_col_idx and row[msg_col_idx - 1] == message_id:
                ws.update_cell(row_idx + 1, status_col_idx, status)
                logger.info(f"Updated outreach log row {row_idx + 1} status → {status} (msg_id={message_id})")
                return

        logger.warning(f"update_outreach_status: no row found for message_id={message_id}")

    def is_contact_recently_emailed(self, email: str, days=90) -> bool:
        """PRD Duplicate Prevention: 90-day cooldown."""
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
                rec_time = datetime.fromisoformat(rec_time_str.replace("Z", "+00:00"))
                if rec_time > cutoff_date:
                    return True
            except Exception:
                logger.warning(f"Failed to parse timestamp '{rec_time_str}' in Outreach Logs.")

        return False

    # --- Runs Tab ---
    def get_runs(self):
        ws = self._get_worksheet("Runs")
        return ws.get_all_records() if ws else []

    def add_run(self, run_data: dict):
        ws = self._get_worksheet("Runs")
        if not ws:
            return None

        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        location_name = (run_data.get("location_name") or run_data.get("complex_name") or run_data.get("pincode") or "").strip()
        row_data = {
            "ID": record_id,
            "Pincode": run_data.get("pincode", ""),
            "Complex Name": run_data.get("complex_name", ""),
            "Location Name": location_name,
            "Companies Found": run_data.get("companies_found", 0),
            "Contacts Found": run_data.get("contacts_found", 0),
            "Emails Sent": run_data.get("emails_sent", 0),
            "Status": run_data.get("status", "completed"),
            "Accuracy Pct": run_data.get("accuracy_pct", ""),
            "Confidence": run_data.get("confidence", "N/A"),
            "Timestamp": timestamp,
        }
        self._append_record(ws, row_data)

        run_data["id"] = record_id
        run_data["created_date"] = timestamp
        return run_data

    # --- Blocklist Tab (PRD §Phase3 — Unsubscribe compliance) ---
    def add_to_blocklist(self, email: str):
        """Adds an email to the Blocklist tab to prevent future outreach."""
        ws = self._get_worksheet("Blocklist")
        if not ws:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        ws.append_row([email.strip().lower(), timestamp])
        logger.info(f"Blocklisted: {email}")

    def is_blocklisted(self, email: str) -> bool:
        """Returns True if the email is on the unsubscribe blocklist."""
        ws = self._get_worksheet("Blocklist")
        if not ws:
            return False
        emails = {v.strip().lower() for v in ws.col_values(1) if v.strip()}
        return email.strip().lower() in emails


# Singleton instance for the app to use
db = SheetsDB()