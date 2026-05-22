"""
Apollo API - find correct domain filter param and test 2-step approach.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("APOLLO_API_KEY")
headers = {"Content-Type": "application/json", "X-Api-Key": key}

# Step 1: Find correct domain filter — try various param names
domain = "dnb.co.in"
params_to_try = [
    {"q_organization_domains_list": [domain]},
    {"person_domains": [domain]},
    {"domains": [domain]},
    {"q_domains": [domain]},
    {"prospected_by_current_team": "no", "q_organization_domains": domain},
]

print("=" * 60)
print("FINDING CORRECT DOMAIN FILTER PARAM")
print("=" * 60)
for params in params_to_try:
    params.update({"page": 1, "per_page": 3})
    r = requests.post(
        "https://api.apollo.io/v1/mixed_people/api_search",
        json=params,
        headers=headers, timeout=15
    )
    total = r.json().get("total_entries", "?")
    first_org = ""
    ppl = r.json().get("people", [])
    if ppl:
        first_org = ppl[0].get("organization", {}).get("name", "?")
    key_used = [k for k in params.keys() if k not in ("page", "per_page", "prospected_by_current_team")]
    print(f"  {key_used}: total={total}, first_org={first_org}")

# Step 2: Test /people/bulk_match with multiple people
print("\n" + "=" * 60)
print("BULK MATCH - multiple people from a company")
print("=" * 60)
r2 = requests.post(
    "https://api.apollo.io/v1/people/bulk_match",
    json={
        "details": [
            {"domain": "dnb.co.in", "organization_name": "Dun Bradstreet"},
        ],
        "reveal_personal_emails": False,
        "reveal_phone_number": False,
    },
    headers=headers, timeout=15
)
print(f"Status: {r2.status_code}")
d = r2.json()
matches = d.get("matches", [])
print(f"Matches: {len(matches)}")
for m in matches[:3]:
    print(f"  {m.get('name')} | {m.get('email')} | {m.get('title')}")

# Step 3: Check if /people/search with domain param works
print("\n" + "=" * 60)
print("CORRECT APPROACH: Search by name+domain via /people/match")
print("=" * 60)
# Known person from Hunter — Sana Afaq at dnb.co.in
r3 = requests.post(
    "https://api.apollo.io/v1/people/match",
    json={
        "first_name": "Sana",
        "last_name": "Afaq",
        "domain": "dnb.co.in",
        "reveal_personal_emails": True
    },
    headers=headers, timeout=15
)
print(f"Status: {r3.status_code}")
p = r3.json().get("person", {})
print(f"Name: {p.get('name')}")
print(f"Email: {p.get('email')}")
print(f"Title: {p.get('title')}")
print(f"LinkedIn: {p.get('linkedin_url')}")
