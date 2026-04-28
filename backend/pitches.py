"""
Module 4 — AI Pitch Generation Engine
Generates a personalized cold outreach email per contact using
Google Gemini 2.5 Flash-Lite.

Rate limiting: 4-second delay between calls to stay under 15 RPM.
Caching: Prompt hash → skip re-generation if already cached.
PRD §6.4
"""

import time
import hashlib
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Simple in-memory cache (hash → result) ---
_pitch_cache: dict[str, dict] = {}

# --- Rate limit delay (PRD §6.4 — 4 seconds between calls) ---
RATE_LIMIT_DELAY_SECONDS = 4

# PRD §6.4 — Fallback static template when API is unavailable
FALLBACK_SUBJECT = "Elevating Employee Experience at {company}"
FALLBACK_BODY = """Hi {name},

I hope this finds you well. I'm reaching out from Adler's Den, where we specialise in premium corporate gifting and employee engagement solutions.

As {role} at {company}, I imagine you're always looking for meaningful ways to boost team morale and reward your people. We'd love to show you how our curated gift experiences have helped companies like yours do just that.

Would you be open to a quick 15-minute call this week?

Warm Regards,
The Adler's Den Team
"""


def _build_prompt(contact_name: str, role: str, company_name: str) -> str:
    """Builds the Gemini prompt exactly as specified in PRD §6.4."""
    return f"""You are an expert B2B sales copywriter. Write a cold outreach email for Adler's Den, a premium corporate gifting and employee engagement company.

Target contact: {contact_name}, {role} at {company_name}

Strict rules:
1. Under 120 words total (email body only, excluding subject).
2. Personalize based on the contact's specific role (e.g., HR gets a message about employee recognition, Marketing gets a message about client gifting).
3. Mention concrete gifting or employee engagement use cases relevant to their function.
4. End with a soft CTA—suggest a quick 15-minute call or meeting, NO pressure.
5. Warm, professional tone. No buzzwords. No generic fluff.
6. Include a compelling subject line.

Return ONLY a valid JSON object with exactly two keys: "subject" and "body". No markdown, no explanations."""


def _cache_key(contact_name: str, role: str, company_name: str) -> str:
    raw = f"{contact_name}::{role}::{company_name}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_pitch(contact_name: str, role: str, company_name: str) -> dict:
    """
    Main entry point for Module 4.
    Returns {"subject": str, "body": str}.
    Falls back to a static template if the API is unavailable or quota is exhausted.
    """
    key = _cache_key(contact_name, role, company_name)

    # --- Cache hit — skip API call ---
    if key in _pitch_cache:
        logger.info(f"Cache hit for pitch: {contact_name} @ {company_name}")
        return _pitch_cache[key]

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Using fallback template.")
        return _fallback_pitch(contact_name, role, company_name)

    # --- Rate limit delay (PRD §6.4) ---
    logger.info(f"Generating pitch for {contact_name} @ {company_name}. Waiting {RATE_LIMIT_DELAY_SECONDS}s...")
    time.sleep(RATE_LIMIT_DELAY_SECONDS)

    try:
        import google.generativeai as genai
        import json

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",  # PRD §6.4 — was incorrectly gemini-1.5-flash
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "max_output_tokens": 400,
            },
        )

        prompt = _build_prompt(contact_name, role, company_name)
        response = model.generate_content(prompt)

        result = json.loads(response.text)
        subject = result.get("subject", "")
        body = result.get("body", "")

        if not subject or not body:
            raise ValueError("Gemini returned an empty subject or body.")

        pitch = {"subject": subject, "body": body}

        # Store in cache
        _pitch_cache[key] = pitch
        logger.info(f"Pitch generated and cached for {contact_name} @ {company_name}")
        return pitch

    except Exception as e:
        logger.error(f"Gemini pitch generation failed: {e}. Using fallback.")
        return _fallback_pitch(contact_name, role, company_name)


def _fallback_pitch(contact_name: str, role: str, company_name: str) -> dict:
    """Returns a safe static template when Gemini is unavailable."""
    first_name = contact_name.split()[0] if contact_name else "there"
    subject = FALLBACK_SUBJECT.format(company=company_name)
    body = FALLBACK_BODY.format(name=first_name, role=role, company=company_name)
    return {"subject": subject, "body": body}
