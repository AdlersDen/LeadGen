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
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
SENDER_NAME    = os.getenv("SENDER_NAME", "The Adler's Den Team")

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
{sender_name}
"""


import requests

def _get_company_intel(domain: str) -> str:
    """Fetches company intelligence from Apollo to enrich the AI pitch."""
    if not domain:
        return ""
        
    apollo_key = os.getenv("APOLLO_API_KEY")
    if not apollo_key:
        return ""
        
    try:
        r = requests.post(
            "https://api.apollo.io/v1/organizations/enrich",
            json={"domain": domain},
            headers={"Content-Type": "application/json", "X-Api-Key": apollo_key},
            timeout=5
        )
        data = r.json()
        org = data.get("organization", {})
        if not org:
            return ""
            
        intel = []
        if org.get("estimated_num_employees"):
            intel.append(f"Estimated Headcount: {org['estimated_num_employees']}")
        if org.get("latest_funding_stage"):
            intel.append(f"Funding Stage: {org['latest_funding_stage']}")
        if org.get("total_funding_printed"):
            intel.append(f"Total Funding: {org['total_funding_printed']}")
        if org.get("industry"):
            intel.append(f"Industry: {org['industry']}")
        if org.get("seo_description"):
            desc = org['seo_description']
            # Truncate description to keep prompt small
            if len(desc) > 200: desc = desc[:197] + "..."
            intel.append(f"Company Description: {desc}")
            
        if not intel:
            return ""
            
        return "\nCompany Context:\n- " + "\n- ".join(intel)
    except Exception as e:
        logger.warning(f"Failed to fetch company intel for {domain}: {e}")
        return ""

def _build_prompt(contact_name: str, role: str, company_name: str, company_intel: str = "", sender_name: str = "") -> str:
    """Builds the AI prompt for pitch generation."""
    first_name = contact_name.split()[0] if contact_name else "there"
    sign_off_name = sender_name or "The Adler's Den Team"

    research_instruction = ""
    if not company_intel:
        research_instruction = f"""
Company Research (use your training knowledge):
- Think about what you know about {company_name}: their industry, size, what they're known for, recent milestones.
- If you are 100% confident about a specific fact (e.g. they recently IPO'd, they have 10,000+ employees, they operate in a specific sector), weave ONE such fact naturally into the body paragraph.
- If you are not confident, do NOT invent or guess — just skip the company fact and personalise based on role only.
"""
    return f"""You are an expert B2B sales copywriter specialising in corporate gifting. Write a cold outreach email for Adler's Den — a premium corporate gifting company based in Mumbai.

What Adler's Den offers:
- Curated gift hampers and branded merchandise for employee recognition, onboarding, and milestone celebrations
- Bespoke gifting for client appreciation and business development
- Festive gifting campaigns, reward trips, and team experiences
- Custom-branded packaging and personalisation at scale

Target contact: {first_name} ({contact_name}), {role} at {company_name}
{company_intel}{research_instruction}

ROLE PERSONALISATION — match the pitch angle to the role:
- HR / People / Culture → employee recognition, onboarding kits, milestone gifting
- Marketing / Brand / CMO → client gifting, branded hampers, campaign giveaways
- Admin / Procurement / Office Manager → vendor gifts, festive office gifting, bulk orders
- Sales / BD / CRO → prospect gifting, deal-closing hampers, client retention
- Operations / Facilities → team celebrations, office event gifting
- CEO / Founder / Director → culture-building, leadership rewards, investor/client gifting

EMAIL STRUCTURE — write exactly 3 parts, separated by blank lines:

Part 1 — GREETING + HOOK (1 sentence):
Start with "Hi {first_name}," on its own line. Then ONE sentence that references something specific about their role or company — make it feel like you did your homework. Do NOT use "I hope this finds you well" or any generic opener.

Part 2 — BODY (2–3 sentences):
Introduce Adler's Den and connect our offering to their specific role/need. If you have a confident company fact, weave it in here naturally. Keep it conversational — no jargon, no buzzwords.

Part 3 — CTA + SIGN-OFF:
One soft call-to-action sentence: suggest a quick 15-minute call or offer to send a free sample curation. No pressure. Then on a NEW LINE, write the sign-off EXACTLY as shown — two separate lines:

Warm regards,
{sign_off_name}

SUBJECT LINE — choose ONE style:
- Personalised: "{first_name}, a gifting idea for your team at {company_name}"
- Question: "How does {company_name} reward its people?"
- Benefit: "A gift your clients will actually remember"

CRITICAL FORMAT RULES:
- The body value in the JSON must use \\n\\n between each of the 3 parts (blank line between paragraphs).
- The sign-off must be on its own lines, separated from the CTA by \\n\\n.
- Do NOT run the sign-off onto the same line as the CTA sentence.
- Return ONLY a valid JSON object with exactly two keys: "subject" and "body". No markdown, no code fences, no explanation."""


def _cache_key(contact_name: str, role: str, company_name: str) -> str:
    raw = f"{contact_name}::{role}::{company_name}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_pitch(contact_name: str, role: str, company_name: str) -> dict:
    """
    Main entry point for Module 4.
    Returns {"subject": str, "body": str}.
    Tries Groq first, falls back to Gemini, then falls back to a static template.
    """
    key = _cache_key(contact_name, role, company_name)

    # --- Cache hit — skip API call ---
    if key in _pitch_cache:
        logger.info(f"Cache hit for pitch: {contact_name} @ {company_name}")
        return _pitch_cache[key]

    if not GROQ_API_KEY and not GEMINI_API_KEY:
        logger.warning("No API keys set. Using fallback template.")
        return _fallback_pitch(contact_name, role, company_name)

    # --- Rate limit delay (PRD §6.4) ---
    logger.info(f"Generating pitch for {contact_name} @ {company_name}. Waiting {RATE_LIMIT_DELAY_SECONDS}s...")
    time.sleep(RATE_LIMIT_DELAY_SECONDS)

    # Fetch domain for company intel
    domain = ""
    try:
        from sheets_db import db
        companies = db.get_companies()
        for c in companies:
            if c.get("Name") == company_name or c.get("Company Name") == company_name:
                domain = c.get("Domain", "")
                break
    except Exception as e:
        logger.warning(f"Could not fetch domain for {company_name}: {e}")

    company_intel = _get_company_intel(domain)
    prompt = _build_prompt(contact_name, role, company_name, company_intel, sender_name=SENDER_NAME)
    pitch = None

    # Try Groq first
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            response_text = completion.choices[0].message.content
            result = json.loads(response_text)
            subject = result.get("subject", "")
            body = result.get("body", "")

            if not subject or not body:
                raise ValueError("Groq returned an empty subject or body.")

            pitch = {"subject": subject, "body": body}
            logger.info("Successfully generated pitch using Groq.")
            
        except Exception as e:
            logger.error(f"Groq pitch generation failed: {e}. Falling back to Gemini...")

    # Fallback to Gemini
    if not pitch and GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite",
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.7,
                    "max_output_tokens": 600,
                },
            )

            response = model.generate_content(prompt)
            result = json.loads(response.text)
            subject = result.get("subject", "")
            body = result.get("body", "")

            if not subject or not body:
                raise ValueError("Gemini returned an empty subject or body.")

            pitch = {"subject": subject, "body": body}
            logger.info("Successfully generated pitch using Gemini.")
            
        except Exception as e:
            logger.error(f"Gemini pitch generation failed: {e}.")

    # Fallback to static template
    if not pitch:
        logger.warning("All AI providers failed. Using fallback template.")
        pitch = _fallback_pitch(contact_name, role, company_name)

    # Store in cache
    _pitch_cache[key] = pitch
    logger.info(f"Pitch cached for {contact_name} @ {company_name}")
    return pitch


def _fallback_pitch(contact_name: str, role: str, company_name: str) -> dict:
    """Returns a safe static template when AI providers are unavailable."""
    first_name = contact_name.split()[0] if contact_name else "there"
    subject = FALLBACK_SUBJECT.format(company=company_name)
    body = FALLBACK_BODY.format(name=first_name, role=role, company=company_name, sender_name=SENDER_NAME)
    return {"subject": subject, "body": body}
