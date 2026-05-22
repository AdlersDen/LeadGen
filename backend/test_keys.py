"""Quick test to verify both Apollo.io and Hunter.io API keys."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_apollo():
    print("=" * 40)
    print("  APOLLO.IO API KEY TEST")
    print("=" * 40)
    key = os.getenv("APOLLO_API_KEY")
    if not key:
        print("FAIL: APOLLO_API_KEY not set in .env")
        return

    print(f"Key: {key[:8]}...{key[-4:]}")
    url = "https://api.apollo.io/v1/mixed_people/api_search"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": key,
    }
    payload = {
        "q_organization_domains": ["google.com"],
        "page": 1,
        "per_page": 2,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            people = data.get("people", [])
            print(f"People returned: {len(people)}")
            for p in people:
                print(f"  - {p.get('name')}: {p.get('title')}")
            print("RESULT: PASS")
        else:
            print(f"Error: {resp.text}")
            print("RESULT: FAIL")
    except Exception as e:
        print(f"Exception: {e}")
        print("RESULT: FAIL")


def test_hunter():
    print()
    print("=" * 40)
    print("  HUNTER.IO API KEY TEST")
    print("=" * 40)
    key = os.getenv("HUNTER_API_KEY")
    if not key:
        print("FAIL: HUNTER_API_KEY not set in .env")
        return

    print(f"Key: {key[:8]}...{key[-4:]}")
    # Use the /account endpoint to check key validity and credits
    url = "https://api.hunter.io/v2/account"
    params = {"api_key": key}
    try:
        resp = requests.get(url, params=params, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            print(f"Account email: {data.get('email')}")
            print(f"Plan: {data.get('plan_name')}")
            reqs = data.get("requests", {})
            searches = reqs.get("searches", {})
            verifs = reqs.get("verifications", {})
            print(f"Searches used/available: {searches.get('used', '?')}/{searches.get('available', '?')}")
            print(f"Verifications used/available: {verifs.get('used', '?')}/{verifs.get('available', '?')}")
            print("RESULT: PASS")
        else:
            print(f"Error: {resp.text}")
            print("RESULT: FAIL")
    except Exception as e:
        print(f"Exception: {e}")
        print("RESULT: FAIL")


if __name__ == "__main__":
    test_apollo()
    test_hunter()
