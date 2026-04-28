"""Quick diagnostic script — run this to test Sheets connection."""
import os
import gspread
from dotenv import load_dotenv

load_dotenv()

SA_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

print(f"Service account file: {SA_FILE}")
print(f"File exists: {os.path.exists(SA_FILE)}")
print(f"Sheet ID: {SHEET_ID}")
print()

try:
    client = gspread.service_account(filename=SA_FILE)
    print("[OK] gspread.service_account()")
except Exception as e:
    print(f"[FAIL] gspread.service_account() failed: {e}")
    exit()

try:
    doc = client.open_by_key(SHEET_ID)
    print(f"[OK] Opened spreadsheet: '{doc.title}'")
except Exception as e:
    print(f"[FAIL] client.open_by_key() failed: {e}")
    exit()

try:
    worksheets = doc.worksheets()
    print(f"[OK] Worksheets found: {[ws.title for ws in worksheets]}")
except Exception as e:
    print(f"[FAIL] doc.worksheets() failed: {e}")
    exit()

try:
    ws = doc.worksheet("Companies")
    ws.append_row(["TEST_ID", "Test Company", "IT", "Test Address", "", "400001", "", "", "", "discovered", "2024-01-01"])
    print("[OK] Test row written to 'Companies' tab successfully!")
    print("\n[SUCCESS] Everything is working! Delete the test row from your sheet.")
except Exception as e:
    print(f"[FAIL] Writing to 'Companies' failed: {e}")
