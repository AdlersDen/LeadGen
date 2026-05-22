import os
from dotenv import load_dotenv
import requests

load_dotenv()
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

url = "https://api.apollo.io/v1/mixed_people/api_search"
headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "X-Api-Key": APOLLO_API_KEY,
}
payload = {
    "q_organization_domains": ["avdel.com"],
    "person_titles": ["HR", "Marketing", "Admin", "Procurement"],
    "page": 1,
    "per_page": 5,
}

print("Fetching from Apollo...")
resp = requests.post(url, json=payload, headers=headers)
print("Status:", resp.status_code)
data = resp.json()

people = data.get("people", [])
print(f"Found {len(people)} people.")
for p in people:
    print(f"- {p.get('name')}: {p.get('email')} ({p.get('title')})")

