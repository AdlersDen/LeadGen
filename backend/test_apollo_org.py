import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("APOLLO_API_KEY")
headers = {"Content-Type": "application/json", "X-Api-Key": key}

print("Fetching organization profile for dnb.co.in to see available fields...")
r = requests.post(
    "https://api.apollo.io/v1/organizations/enrich",
    json={"domain": "dnb.co.in"},
    headers=headers, timeout=15
)

data = r.json()
if "organization" in data:
    print(json.dumps(data["organization"], indent=2))
else:
    print(f"Error or no org: {data}")
