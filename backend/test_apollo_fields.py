import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("APOLLO_API_KEY")
headers = {"Content-Type": "application/json", "X-Api-Key": key}

print("Fetching full profile for Sana Afaq at D&B to see available fields...")
r = requests.post(
    "https://api.apollo.io/v1/people/match",
    json={
        "first_name": "Sana",
        "last_name": "Afaq",
        "domain": "dnb.co.in",
        "reveal_personal_emails": True
    },
    headers=headers, timeout=15
)

data = r.json()
if "person" in data:
    print(json.dumps(data["person"], indent=2))
else:
    print("No person data found.")
