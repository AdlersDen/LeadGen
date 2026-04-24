"""
Module 1 — Company Discovery Engine
Converts a pincode to a list of filtered B2B corporate businesses
using the Google Geocoding API and Google Maps Places API.
PRD §6.1
"""

import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# PRD §6.1 — Types to INCLUDE (must be corporate/office-type)
ALLOWED_TYPES = {
    "corporate_office", "office", "accounting", "insurance_agency",
    "finance", "lawyer", "real_estate_agency", "travel_agency",
    "moving_company", "storage", "courier", "freight_forwarder",
    "warehouse", "manufacturing", "general_contractor",
    "staffing_agency", "consultant", "software_company",
    "advertising_agency", "marketing", "it_company",
}

# PRD §6.1 — Types to EXCLUDE explicitly
EXCLUDED_TYPES = {
    "restaurant", "food", "cafe", "bar", "bakery", "meal_delivery",
    "meal_takeaway", "lodging", "hotel", "beauty_salon", "hair_care",
    "spa", "gym", "fitness_center", "hospital", "doctor", "pharmacy",
    "dentist", "veterinary_care", "school", "university", "church",
    "hindu_temple", "mosque", "clothing_store", "grocery_or_supermarket",
    "supermarket", "convenience_store", "department_store", "shoe_store",
    "electronics_store", "furniture_store", "jewelry_store", "pet_store",
    "hardware_store", "book_store", "bicycle_store", "car_dealer",
    "car_repair", "car_wash", "gas_station", "parking", "atm",
    "bank", "post_office", "local_government_office", "ambulance_station",
    "fire_station", "police",
}

# Neutral types that are acceptable (IT parks, business parks, etc.)
NEUTRAL_ALLOWED_KEYWORDS = ["pvt", "ltd", "llp", "inc", "corp", "limited", "technologies",
                              "solutions", "services", "consulting", "software", "systems",
                              "enterprises", "industries", "group", "associates", "partners"]


def _pincode_to_coords(pincode: str) -> tuple[float, float] | None:
    """Convert Indian pincode to lat/lng via Google Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": f"{pincode}, India",
        "key": MAPS_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            location_name = data["results"][0].get("formatted_address", pincode)
            return loc["lat"], loc["lng"], location_name
    except Exception as e:
        logger.error(f"Geocoding failed for pincode {pincode}: {e}")
    return None, None, pincode


def _fetch_places(lat: float, lng: float, radius_m: int = 3000, page_token: str = None) -> dict:
    """Query Google Maps Places API (Nearby Search)."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius_m,
        "type": "establishment",
        "key": MAPS_API_KEY,
    }
    if page_token:
        params = {"pagetoken": page_token, "key": MAPS_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Places API fetch failed: {e}")
        return {}


def _is_b2b_company(place: dict) -> bool:
    """
    PRD §6.1 filtering — returns True only if the place looks corporate.
    Checks Google types + name heuristics.
    """
    place_types = set(place.get("types", []))
    name = place.get("name", "").lower()

    # Hard exclude
    if place_types & EXCLUDED_TYPES:
        return False

    # Hard include based on type
    if place_types & ALLOWED_TYPES:
        return True

    # Heuristic — company name contains a B2B keyword
    if any(kw in name for kw in NEUTRAL_ALLOWED_KEYWORDS):
        return True

    return False


def _extract_domain(place: dict) -> str:
    """
    Extract domain from Place Details if available.
    Requires an extra Places Detail API call per place.
    Only called if we decide to enrich a record.
    """
    place_id = place.get("place_id")
    if not place_id:
        return ""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number",
        "key": MAPS_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        website = result.get("website", "")
        phone = result.get("formatted_phone_number", "")
        # Strip protocol and www
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        return domain, phone
    except Exception as e:
        logger.warning(f"Place detail fetch failed for {place_id}: {e}")
        return "", ""


def discover_companies(pincode: str) -> dict:
    """
    Main entry point for Module 1.
    Returns a dict with location_name and a list of filtered companies.
    """
    if not MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY is not set.")
        return {"location_name": pincode, "companies": []}

    lat, lng, location_name = _pincode_to_coords(pincode)
    if not lat:
        return {"location_name": pincode, "companies": [], "error": "Could not geocode pincode."}

    logger.info(f"Discovering companies near {location_name} ({lat}, {lng})")

    all_places = []
    data = _fetch_places(lat, lng)
    all_places.extend(data.get("results", []))

    # Fetch up to 2 pages of results (each page = 20 places)
    next_token = data.get("next_page_token")
    if next_token:
        import time
        time.sleep(2)  # Google requires a short delay before using next_page_token
        data2 = _fetch_places(lat, lng, page_token=next_token)
        all_places.extend(data2.get("results", []))

    # Filter
    b2b_places = [p for p in all_places if _is_b2b_company(p)]
    logger.info(f"Found {len(all_places)} total places, {len(b2b_places)} passed B2B filter for {pincode}")

    companies = []
    for place in b2b_places:
        domain, phone = _extract_domain(place)
        companies.append({
            "name": place.get("name", ""),
            "address": place.get("vicinity", ""),
            "pincode": pincode,
            "industry": ", ".join(place.get("types", []))[:100],
            "google_rating": place.get("rating"),
            "domain": domain,
            "phone": phone,
            "status": "discovered",
            "source": "Google Maps",
        })

    return {
        "location_name": location_name,
        "companies": companies,
    }
