from sheets_db import db

# create a dummy company to test insertion
company = {
    "name": "Test Company Add Phone",
    "industry": "tech",
    "address": "test address",
    "domain": "testphone.com",
    "phone": "123-456-7890",
    "pincode": "999999",
    "employee_count": "10-50",
    "tier": "A",
    "contacts_extracted": "No",
    "status": "discovered"
}

try:
    res = db.add_companies_bulk([company])
    print("Added:", res)
except Exception as e:
    print("Error:", e)
