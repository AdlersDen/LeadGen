"""
Module 2 — Contact Intelligence Engine
Finds verified decision-makers at a company using:
  Primary: Hunter.io domain search API
  Fallback: Apollo.io people search API (optional)
PRD §6.2
"""

import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

# PRD §6.2 — Target roles in priority order
TARGET_ROLE_KEYWORDS = [
    "hr", "human resource", "chro", "people",
    "marketing", "cmo", "brand", "growth",
    "admin", "procurement", "office manager", "facility",
]

# PRD §6.3 — Minimum Hunter.io confidence score
MIN_CONFIDENCE = 50


def _role_priority(title: str) -> int:
    """Return priority score for a role title (lower = higher priority)."""
    title_lower = title.lower()
    if any(k in title_lower for k in ["hr", "human resource", "chro", "people"]):
        return 1
    if any(k in title_lower for k in ["marketing", "cmo", "brand", "growth"]):
        return 2
    if any(k in title_lower for k in ["admin", "procurement", "office manager", "facility"]):
        return 3
    return 99  # Not a target role


def _search_hunter(domain: str) -> list[dict]:
    """
    Hunter.io Domain Search — returns all emails found for a domain.
    We filter for target roles and confidence >= 50.
    """
    if not HUNTER_API_KEY:
        logger.warning("HUNTER_API_KEY not set. Skipping Hunter.io lookup.")
        return []

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("errors"):
            logger.warning(f"Hunter.io error for {domain}: {data['errors']}")
            return []

        emails = data.get("data", {}).get("emails", [])
        contacts = []
        for e in emails:
            confidence = e.get("confidence", 0)
            if confidence < MIN_CONFIDENCE:
                continue

            position = e.get("position", "") or ""
            priority = _role_priority(position)
            if priority == 99:
                continue  # Skip non-target roles

            full_name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()
            contacts.append({
                "full_name": full_name,
                "email": e.get("value", ""),
                "role": position,
                "confidence_score": confidence,
                "source": "hunter.io",
                "_priority": priority,
            })

        # Sort by role priority
        contacts.sort(key=lambda x: x["_priority"])
        for c in contacts:
            c.pop("_priority", None)

        logger.info(f"Hunter.io found {len(contacts)} qualifying contacts for {domain}")
        return contacts

    except Exception as e:
        logger.error(f"Hunter.io request failed for {domain}: {e}")
        return []


def _search_apollo(company_name: str, domain: str) -> list[dict]:
    """
    Apollo.io People Search — fallback when Hunter.io returns nothing.
    Uses the /v1/mixed_people/search endpoint.
    """
    if not APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not set. Skipping Apollo.io lookup.")
        return []

    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }
    payload = {
        "q_organization_domains": [domain],
        "person_titles": [
            "HR Manager", "Head of HR", "CHRO",
            "Marketing Manager", "CMO", "Marketing Head",
            "Admin Manager", "Procurement Head", "Office Manager",
        ],
        "page": 1,
        "per_page": 10,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        people = data.get("people", [])
        contacts = []
        for p in people:
            email = p.get("email", "")
            if not email or email == "email_not_unlocked@domain.com":
                continue  # Apollo hides emails unless you unlock them

            title = p.get("title", "")
            priority = _role_priority(title)
            if priority == 99:
                continue

            contacts.append({
                "full_name": p.get("name", ""),
                "email": email,
                "role": title,
                "confidence_score": 70,  # Apollo unlocked emails are generally reliable
                "source": "apollo.io",
            })

        logger.info(f"Apollo.io found {len(contacts)} contacts for {company_name}")
        return contacts

    except Exception as e:
        logger.error(f"Apollo.io request failed for {company_name}: {e}")
        return []


def find_contacts(company_name: str, domain: str) -> list[dict]:
    """
    Main entry point for Module 2.
    Tries Hunter.io first; falls back to Apollo.io if nothing found.
    Returns a list of up to 3 verified decision-maker contacts.
    """
    if not domain:
        logger.warning(f"No domain provided for company: {company_name}. Cannot look up contacts.")
        return []

    # --- Primary: Hunter.io ---
    contacts = _search_hunter(domain)

    # --- Fallback: Apollo.io (optional) ---
    if not contacts and APOLLO_API_KEY:
        logger.info(f"Hunter.io returned nothing for {domain}. Trying Apollo.io fallback.")
        contacts = _search_apollo(company_name, domain)

    # PRD §4 — Return max 3 decision-makers per company
    return contacts[:3]
