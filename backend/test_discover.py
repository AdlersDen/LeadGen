import asyncio
import json
from fastapi.testclient import TestClient
from main import app
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

response = client.post("/api/discover", json={
    "pincode": "400606",
    "radius_km": 2,
    "industries": [],
    "tiers": ["A", "B"]
})

with open("test_resp.json", "w") as f:
    json.dump({"status": response.status_code, "body": response.json()}, f)
