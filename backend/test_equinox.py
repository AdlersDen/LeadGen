"""Quick test: discover companies at Equinox Business Park, Kurla
and check if Titan Company Limited appears in results."""
import json
from fastapi.testclient import TestClient
from main import app
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

response = client.post("/api/discover", json={
    "complex_name": "Equinox Business Park Kurla",
    "industries": [],
    "tiers": ["A", "B", "C"]
})

data = response.json()
companies = data.get("companies", [])

print(f"\n{'='*60}")
print(f"Complex: Equinox Business Park Kurla")
print(f"Status: {response.status_code}")
print(f"Total companies found: {len(companies)}")
print(f"{'='*60}\n")

titan_found = False
for c in companies:
    name = c.get("name", "")
    if "titan" in name.lower():
        titan_found = True
        print(f">>> TITAN FOUND: {name}")
        print(f"    Address: {c.get('address')}")
        print(f"    Tier: {c.get('tier')}")
        print(f"    Domain: {c.get('domain')}")
        print()
    print(f"  - {name} (Tier {c.get('tier')})")

print(f"\n{'='*60}")
if titan_found:
    print("TEST PASSED -- Titan Company Limited is in the results!")
else:
    print("TEST FAILED -- Titan Company Limited was NOT found.")
print(f"{'='*60}")
