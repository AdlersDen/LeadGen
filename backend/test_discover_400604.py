import asyncio
import json
from fastapi.testclient import TestClient
from main import app
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

print("Starting request...")
try:
    response = client.post("/api/discover", json={
        "pincode": "400604",
        "radius_km": 5,
        "industries": [],
        "tiers": ["A", "B", "C"]
    })

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    import traceback
    traceback.print_exc()
