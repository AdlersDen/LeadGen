"""
Module 2 — Contact Intelligence Engine
Finds verified decision-makers at a company using:
  PRIMARY:  Apollo.io people search API
  FALLBACK: Hunter.io domain search API (when Apollo returns nothing)

PRD §6.2 — Updated: Apollo is primary per user decision.
"""

import requests
import logging
import os
from dotenv import load_dotenv
import tldextract
from cleaning import clean_contact_data

load_dotenv()
logger = logging.getLogger(__name__)

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

# PRD §6.2 — Target roles in priority order
TIER_1_KEYWORDS = [
    "hr", "human resource", "chro", "people", "culture", "employee experience", 
    "employee engagement", "reward", "benefit", "marketing", "cmo", "brand", 
    "growth", "admin", "office manager", "procurement", "purchase", "vendor"
]

TIER_2_KEYWORDS = [
    "operation", "coo", "chief operating officer", "workplace", "facility", 
    "facilities", "business development", "bd", "client success", "customer success", 
    "communication", "pr", "public relation", "sales", "cro", "chief revenue officer"
]

TIER_3_KEYWORDS = [
    "ceo", "founder", "owner", "managing director", "md", "director"
]

# PRD §6.3 — Minimum Hunter.io confidence score
MIN_CONFIDENCE = 50

# Personal email domains — prefer corporate emails when multiple are available
PERSONAL_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'yahoo.co.in', 'rediffmail.com', 'live.com', 'icloud.com',
    'protonmail.com', 'zoho.com',
}


def extract_root_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"
    return url


def _role_priority(title: str) -> int:
    """Return priority score for a role title (lower = higher priority)."""
    title_lower = title.lower()
    if any(k in title_lower for k in TIER_1_KEYWORDS):
        return 1
    if any(k in title_lower for k in TIER_2_KEYWORDS):
        return 2
    if any(k in title_lower for k in TIER_3_KEYWORDS):
        return 3
    return 99  # Not a target role


def _pick_best_email(match: dict) -> str:
    """Prefer corporate domain emails; fall back to personal if no alternative."""
    primary = match.get("email", "")
    all_emails = match.get("emails") or []
    if not all_emails and primary:
        all_emails = [{"email": primary}]

    corporate, personal = [], []
    for entry in all_emails:
        addr = entry.get("email", "") if isinstance(entry, dict) else str(entry)
        if not addr or "@" not in addr:
            continue
        domain = addr.split("@")[-1].lower()
        (personal if domain in PERSONAL_EMAIL_DOMAINS else corporate).append(addr)

    if corporate:
        return corporate[0]
    if personal:
        logger.debug(f"Only personal email available: {personal[0]}")
        return personal[0]
    return primary


def _search_apollo(company_name: str, domain: str) -> list[dict]:
    """
    Apollo.io People Search — PRIMARY source.
    Two-step approach:
      1. Search by domain using q_organization_domains_list → get candidates + titles
      2. Unlock emails for qualifying people via /v1/people/bulk_match
    """
    if not APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not set. Skipping Apollo.io lookup.")
        return []

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }

    # ── Step 1: Find people at this domain ───────────────────────────────────
    search_url = "https://api.apollo.io/v1/mixed_people/api_search"
    payload = {
        "q_organization_domains_list": [domain],
        "page": 1,
        "per_page": 25,  # Fetch more candidates to filter by role
    }
    try:
        resp = requests.post(search_url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        all_people = data.get("people", [])
        logger.info(f"Apollo Step 1: found {len(all_people)} raw candidates at {domain} (total in DB: {data.get('total_entries', 0)})")
    except Exception as e:
        logger.error(f"Apollo.io Step 1 (search) failed for {company_name}: {e}")
        return []

    # ── Step 2: Filter by role, then unlock emails via bulk_match ─────────────
    # Build candidate list — Apollo returns obfuscated names + title in search
    qualifying = []
    step1_linkedin = {}  # person_id → linkedin_url from Step 1 results
    for p in all_people:
        title = p.get("title", "") or ""
        priority = _role_priority(title)
        if priority == 99:
            continue  # Skip non-target roles

        # Apollo search returns first_name but obfuscates last_name
        first_name = p.get("first_name", "") or ""
        last_name_obf = p.get("last_name_obfuscated", "") or ""
        person_id = p.get("id", "")

        # Preserve LinkedIn URL from Step 1 — bulk_match sometimes omits it
        if person_id and p.get("linkedin_url"):
            step1_linkedin[person_id] = p["linkedin_url"]

        qualifying.append({
            "id": person_id,
            "first_name": first_name,
            "last_name_obfuscated": last_name_obf,
            "title": title,
            "_priority": priority,
        })

    if not qualifying:
        logger.info(f"Apollo.io: No qualifying roles found at {domain} for {company_name}")
        return []

    logger.info(f"Apollo Step 2: Unlocking emails for {len(qualifying[:10])} qualifying candidates at {domain}")

    # Unlock emails — use /people/bulk_match with person IDs
    bulk_url = "https://api.apollo.io/v1/people/bulk_match"
    details = [{"id": p["id"]} for p in qualifying[:10]]  # Max 10 to conserve credits
    try:
        bulk_resp = requests.post(
            bulk_url,
            json={"details": details, "reveal_personal_emails": False},
            headers=headers,
            timeout=20
        )
        bulk_resp.raise_for_status()
        bulk_data = bulk_resp.json()
        matches = bulk_data.get("matches", [])
    except Exception as e:
        try:
            body = bulk_resp.json()
        except Exception:
            body = getattr(bulk_resp, 'text', '')
        logger.error(f"Apollo.io Step 2 (bulk_match) failed for {company_name}: {e} | Response: {body}")
        return []

    # ── Step 3: Build final contact list from unlocked data ───────────────────
    contacts = []
    for match in matches:
        if match is None:
            continue
        email = _pick_best_email(match)
        if not email:
            continue

        title = match.get("title", "") or ""
        priority = _role_priority(title)
        if priority == 99:
            continue

        # Extract extra fields from Apollo match object
        # Fall back to Step 1 linkedin_url if bulk_match omits it
        person_id_match = match.get("id", "")
        linkedin_url = match.get("linkedin_url", "") or step1_linkedin.get(person_id_match, "")
        seniority = match.get("seniority", "")
        city = match.get("city", "")
        state = match.get("state", "")
        location_parts = [p for p in [city, state] if p]
        location = ", ".join(location_parts)

        # Extract phone — prefer direct_dial, fall back to first phone_numbers entry
        phone = ""
        direct_dial = match.get("direct_dial") or {}
        if isinstance(direct_dial, dict):
            phone = direct_dial.get("sanitized_number") or direct_dial.get("raw_number") or ""
        if not phone:
            phone_numbers = match.get("phone_numbers") or []
            if phone_numbers and isinstance(phone_numbers, list):
                first_ph = phone_numbers[0]
                if isinstance(first_ph, dict):
                    phone = first_ph.get("sanitized_number") or first_ph.get("raw_number") or ""

        contacts.append({
            "full_name": match.get("name", ""),
            "email": email,
            "role": title,
            "confidence_score": 85,  # Apollo matched + unlocked = high confidence
            "source": "apollo.io",
            "_priority": priority,
            "linkedin_url": linkedin_url,
            "seniority": seniority,
            "location": location,
            "phone": phone,
        })

    contacts.sort(key=lambda x: x["_priority"])
    for c in contacts:
        c.pop("_priority", None)

    logger.info(f"Apollo.io found {len(contacts)} qualifying contacts for {company_name}")
    return contacts



def _search_hunter(domain: str) -> list[dict]:
    """
    Hunter.io Domain Search — FALLBACK when Apollo returns nothing.
    We filter for target roles and confidence >= 50.
    """
    if not HUNTER_API_KEY:
        logger.warning("HUNTER_API_KEY not set. Skipping Hunter.io lookup.")
        return []

    root_domain = extract_root_domain(domain)
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": root_domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,
        "type": "personal",
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


def find_contacts(company_name: str, domain: str) -> list[dict]:
    """
    Main entry point for Module 2.

    Lookup order (per PRD decision):
      1. Apollo.io  — PRIMARY (richer profiles, unlocked emails)
      2. Hunter.io  — FALLBACK (when Apollo returns nothing)

    Each contact is run through clean_contact_data() (PRD §6.3):
      - MX record verification on the email domain
      - Name normalization (title case, strip specials)
    Contacts that fail cleaning are dropped before being saved.

    Returns a list of up to 3 verified decision-maker contacts.
    """
    if not domain:
        logger.warning(f"No domain provided for company: {company_name}. Cannot look up contacts.")
        return []

    # --- Primary: Apollo.io ---
    raw_contacts = _search_apollo(company_name, domain)

    # --- Fallback: Hunter.io (only if Apollo returned nothing) ---
    if not raw_contacts:
        logger.info(f"Apollo.io returned nothing for {domain}. Trying Hunter.io fallback.")
        raw_contacts = _search_hunter(domain)

    # --- PRD §6.3 — Data cleaning & MX verification ---
    clean_contacts = []
    for contact in raw_contacts:
        cleaned = clean_contact_data(contact)
        if cleaned is None:
            logger.info(f"Dropped contact {contact.get('full_name')} — failed MX/email validation.")
            continue
        clean_contacts.append(cleaned)

    # PRD §6.2 — Return max 3 decision-makers per company
    return clean_contacts[:3]
