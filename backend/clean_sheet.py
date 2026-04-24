import os
import gspread
from dotenv import load_dotenv

load_dotenv()

SA_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

client = gspread.service_account(filename=SA_FILE)
doc = client.open_by_key(SHEET_ID)

print("Cleaning Companies tab...")
ws_companies = doc.worksheet("Companies")
ws_companies.clear()
ws_companies.append_row(["ID", "Name", "Industry", "Address", "Domain", "Pincode", "Employee Count", "Status", "Created Date"])
print("Companies tab formatted with headers!")

print("Cleaning Runs tab...")
ws_runs = doc.worksheet("Runs")
ws_runs.clear()
ws_runs.append_row(["ID", "Pincode", "Location Name", "Companies Found", "Contacts Found", "Emails Sent", "Status", "Timestamp"])
print("Runs tab formatted with headers!")

print("Cleaning Contacts tab...")
ws_contacts = doc.worksheet("Contacts")
ws_contacts.clear()
ws_contacts.append_row(["ID", "Company ID", "Full Name", "Role", "Email", "Confidence Score", "Status", "Company Name", "Created Date"])

print("Cleaning Outreach Logs tab...")
ws_logs = doc.worksheet("Outreach Logs")
ws_logs.clear()
ws_logs.append_row(["ID", "Campaign ID", "Contact ID", "Contact Email", "Contact Name", "Company Name", "Subject", "Body", "Status", "Timestamp"])

print("All tabs cleaned and headers initialized successfully!")
