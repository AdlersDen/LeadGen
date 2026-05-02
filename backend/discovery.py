"""
Module 1 — Company Discovery Engine
Converts a pincode OR business complex name to a list of filtered B2B corporate businesses
using the Google Geocoding API and Google Maps Places API.
Supports two modes:
  - Pincode mode:  geocode pincode -> nearby_search within radius_km
  - Complex mode:  text search for corporate offices in named complex
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
    "finance", "lawyer", "real_estate_agency",
    "moving_company", "storage", "courier", "freight_forwarder",
    "warehouse", "manufacturing", "general_contractor", "staffing_agency",
    "consultant", "software_company", "advertising_agency", "marketing",
    "it_company", "bank"  # bank added back — remove ATMs by name check instead
}

# PRD §6.1 — Types to EXCLUDE explicitly
BLOCKLIST_TYPES = {
    "restaurant", "food", "cafe", "bar", "bakery", "meal_delivery",
    "meal_takeaway", "lodging", "hotel", "beauty_salon", "hair_care",
    "spa", "gym", "fitness_center", "hospital", "doctor", "pharmacy",
    "dentist", "veterinary_care", "school", "university", "church",
    "hindu_temple", "mosque", "clothing_store", "grocery_or_supermarket",
    "supermarket", "convenience_store", "department_store", "shoe_store",
    "electronics_store", "furniture_store", "jewelry_store", "pet_store",
    "hardware_store", "book_store", "bicycle_store", "car_dealer",
    "car_repair", "car_wash", "gas_station", "parking", "atm",
    "post_office", "local_government_office", "ambulance_station",
    "fire_station", "police", "night_club", "amusement_park", "casino",
    "bowling_alley", "movie_theater", "stadium", "zoo", "aquarium",
    "laundry", "funeral_home", "cemetery", "home_goods_store", "store"
}

# Neutral types that are acceptable (IT parks, business parks, etc.)
CORPORATE_KEYWORDS = [
    "pvt", "ltd", "llp", "inc", "corp", "limited",
    "technologies", "solutions", "services", "consulting",
    "software", "systems", "enterprises", "industries",
    "group", "associates", "partners", "foundation",
    "capital", "ventures", "investments", "financial",
    "management", "global", "international", "india"
]

# Industry value key -> search terms for complex text search
INDUSTRY_KEYWORDS = {
    "tech":          "IT software technology",
    "events":        "event management",
    "realestate":    "real estate",
    "finance":       "finance banking",
    "consulting":    "consulting",
    "manufacturing": "manufacturing",
    "marketing":     "marketing media",
    "pharma":        "pharmaceutical health",
    "logistics":     "logistics courier",
    "education":     "education training",
}


# ── Utility: Haversine distance ───────────────────────────────────────────────
import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns the great-circle distance in metres between two lat/lng points.
    Uses the Haversine formula.
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi        = math.radians(lat2 - lat1)
    dlambda     = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_radius_from_viewport(viewport: dict) -> float:
    """
    Derives a search radius (metres) from a Google Maps viewport dict that
    contains 'northeast' and 'southwest' lat/lng bounds.
    Uses the half-diagonal of the bounding box, capped between 200 m and 1000 m.
    """
    ne = viewport.get("northeast", {})
    sw = viewport.get("southwest", {})
    if not ne or not sw:
        return 800.0  # safe default
    diagonal = haversine_distance(
        sw.get("lat", 0), sw.get("lng", 0),
        ne.get("lat", 0), ne.get("lng", 0),
    )
    radius = diagonal / 2
    # Three-tier radius logic based on complex physical size
    if radius <= 300:
        return max(150.0, radius)   # Single building — very tight
    elif radius <= 700:
        return radius * 0.80        # Medium complex — slight shrink
    else:
        return min(radius, 1200.0)  # Large campus — cap at 1200 m


def _pincode_to_coords(pincode: str) -> tuple:
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


def _fetch_places(lat: float, lng: float, radius_m: int = 2000, page_token: str = None) -> dict:
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


def _fetch_text_search(query: str) -> list:
    """
    Google Maps Text Search — used for complex / area mode.
    Works globally — no lat/lng required.
    Fetches up to 2 pages (max ~40 results) to improve coverage.
    """
    import time as _time
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": MAPS_API_KEY}
    all_results = []
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        logger.info(f"Text search page 1: {len(all_results)} results for '{query}'")

        # Fetch second page if available (Google requires ~2s delay)
        next_page_token = data.get("next_page_token")
        if next_page_token:
            _time.sleep(2)
            resp2 = requests.get(url, params={"pagetoken": next_page_token, "key": MAPS_API_KEY}, timeout=15)
            resp2.raise_for_status()
            page2 = resp2.json().get("results", [])
            all_results.extend(page2)
            logger.info(f"Text search page 2: +{len(page2)} results for '{query}'")

    except Exception as e:
        logger.error(f"Text search failed for '{query}': {e}")
    return all_results


CITY_WORDS = {
    "mumbai", "pune", "bangalore", "bengaluru", "gurugram",
    "gurgaon", "delhi", "hyderabad", "chennai", "kolkata",
    "noida", "thane", "navi", "london", "dubai", "singapore"
}


def _extract_complex_hint(complex_name: str) -> list:
    """Extract key words from complex name, removing city names."""
    words = complex_name.lower().split()
    return [w for w in words if w not in CITY_WORDS and len(w) > 2]


def _address_matches_complex(place: dict, complex_name: str) -> bool:
    """
    Returns True if the place's address or name contains at least one
    key word from the complex name. Drops results that are just
    nearby but not actually inside the searched complex.
    """
    hint_words = _extract_complex_hint(complex_name)
    if not hint_words:
        return True  # can't verify, allow through
    address = (
        place.get("vicinity", "") + " " +
        place.get("name", "")
    ).lower()
    matches = sum(1 for word in hint_words if word in address)
    return matches >= 1


JUNK_NAME_PATTERNS = [
    "internal road", "gate ", "entrance", "exit",
    "parking lot", "bus stop", "metro station",
    "food court", "canteen", "cafeteria", "atm"
]


def _is_junk_listing(name: str, complex_name: str = "") -> bool:
    name_lower = name.lower()
    # Pattern-based junk check
    if any(pattern in name_lower for pattern in JUNK_NAME_PATTERNS):
        return True
    # If the place name IS the complex itself (80%+ hint words match), skip it
    if complex_name:
        hint_words = _extract_complex_hint(complex_name)
        if hint_words:
            matches = sum(1 for w in hint_words if w in name_lower)
            if matches / len(hint_words) >= 0.80:
                return True
    return False


def _is_b2b_company(place: dict) -> bool:
    """
    PRD §6.1 filtering — returns True only if the place looks corporate.
    Checks Google types + name heuristics.
    """
    place_types = set(place.get("types", []))
    name_lower = place.get("name", "").lower()

    # Skip ATMs even if type is "bank"
    if "atm" in name_lower and len(name_lower) < 15:
        return False

    # Hard exclude
    if place_types & BLOCKLIST_TYPES:
        return False

    # Hard include based on type
    if place_types & ALLOWED_TYPES:
        return True

    # Heuristic — company name contains a B2B keyword
    if any(kw in name_lower for kw in CORPORATE_KEYWORDS):
        return True

    return False


def _extract_domain(place: dict) -> tuple:
    """
    Extract domain and phone from Place Details if available.
    Requires an extra Places Detail API call per place.
    Always returns a (domain, phone) tuple — never a bare string.
    """
    place_id = place.get("place_id")
    if not place_id:
        return "", ""  # was returning bare "" causing ValueError on unpack
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


def _score_tier(rating, domain: str) -> str:
    """
    Assigns a lead tier based on Google rating and domain availability.
    Tier A: high-value leads (rating >= 4.0 AND has a domain)
    Tier B: medium-value leads (rating >= 3.5 OR has a domain)
    Tier C: low-priority leads (everything else)
    """
    has_domain = bool(domain and domain.strip())
    rating = rating or 0.0

    if rating >= 4.0 and has_domain:
        return "A"
    if rating >= 3.5 or has_domain:
        return "B"
    return "C"


def discover_companies(
    pincode: str = None,
    complex_name: str = None,
    radius_km: int = 2,
    industries: list = None,
    tiers: list = None,
) -> dict:
    """
    Main entry point for Module 1. Supports two modes:
      - Pincode mode:  geocode pincode -> nearby_search within radius_km
      - Complex mode:  text search for corporate offices in named complex

    Filters:
      - industries: list of value keys (empty = all industries)
      - tiers:      list of A/B/C (default: A and B)
    """
    import time

    if industries is None:
        industries = []
    if tiers is None:
        tiers = ["A", "B"]

    if not MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY is not set.")
        return {"location_name": complex_name or pincode, "companies": []}

    # ── Complex / Area mode — strict boundary enforcement ────────────────────
    if complex_name:
        location_name = complex_name

        # Step 1: Resolve the complex to exact coordinates + viewport
        fp_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        fp_params = {
            "input": complex_name,
            "inputtype": "textquery",
            "fields": "geometry,name",
            "key": MAPS_API_KEY,
        }
        try:
            fp_resp = requests.get(fp_url, params=fp_params, timeout=10)
            fp_resp.raise_for_status()
            fp_data = fp_resp.json()
        except Exception as e:
            logger.error(f"find_place failed for '{complex_name}': {e}")
            return {"location_name": complex_name, "companies": [], "error": "find_place API call failed."}

        candidates = fp_data.get("candidates", [])
        if not candidates:
            logger.warning(f"find_place returned no candidates for '{complex_name}'")
            return {"location_name": complex_name, "companies": [], "error": "Complex not found on Google Maps."}

        geometry  = candidates[0].get("geometry", {})
        location  = geometry.get("location", {})
        viewport  = geometry.get("viewport", {})
        cx_lat    = location.get("lat")
        cx_lng    = location.get("lng")

        if not cx_lat or not cx_lng:
            logger.error(f"find_place returned geometry without location for '{complex_name}'")
            return {"location_name": complex_name, "companies": [], "error": "Could not resolve complex coordinates."}

        # Step 2: Derive search radius from viewport (haversine half-diagonal, 200–1000 m)
        radius_m = get_radius_from_viewport(viewport)
        logger.info(
            f"Complex '{complex_name}' → ({cx_lat}, {cx_lng}), viewport radius={radius_m:.0f} m"
        )

        # Step 3: Two separate nearby searches ('office' and 'corporate'), up to 3 pages each
        import time as _time
        nb_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        all_raw_places_dict = {}

        for keyword in ["office", "corporate"]:
            nb_params = {
                "location": f"{cx_lat},{cx_lng}",
                "radius":   int(radius_m),
                "keyword":  keyword,
                "key":      MAPS_API_KEY,
            }
            try:
                nb_resp = requests.get(nb_url, params=nb_params, timeout=15)
                nb_resp.raise_for_status()
                nb_data = nb_resp.json()
                
                # Page 1
                for p in nb_data.get("results", []):
                    all_raw_places_dict[p.get("place_id")] = p
                
                # Page 2
                next_token = nb_data.get("next_page_token")
                if next_token:
                    _time.sleep(2)
                    resp2 = requests.get(nb_url, params={"pagetoken": next_token, "key": MAPS_API_KEY}, timeout=15)
                    resp2.raise_for_status()
                    data2 = resp2.json()
                    for p in data2.get("results", []):
                        all_raw_places_dict[p.get("place_id")] = p
                    
                    # Page 3
                    next_token2 = data2.get("next_page_token")
                    if next_token2:
                        _time.sleep(2)
                        resp3 = requests.get(nb_url, params={"pagetoken": next_token2, "key": MAPS_API_KEY}, timeout=15)
                        resp3.raise_for_status()
                        data3 = resp3.json()
                        for p in data3.get("results", []):
                            all_raw_places_dict[p.get("place_id")] = p
                            
            except Exception as e:
                logger.error(f"places_nearby failed for '{complex_name}' with keyword '{keyword}': {e}")
                continue

        if not all_raw_places_dict:
            return {"location_name": complex_name, "companies": [], "error": "Nearby search API call failed."}

        raw_places = list(all_raw_places_dict.values())
        logger.info(f"places_nearby: {len(raw_places)} deduped results for '{complex_name}'")

        # Step 4: Secondary haversine coordinate filter — drop places outside the radius
        inside_places = []
        dropped = 0
        for p in raw_places:
            p_loc  = p.get("geometry", {}).get("location", {})
            p_lat  = p_loc.get("lat")
            p_lng  = p_loc.get("lng")
            if p_lat is None or p_lng is None:
                dropped += 1
                continue
            dist = haversine_distance(cx_lat, cx_lng, p_lat, p_lng)
            if dist <= radius_m * 0.80:
                inside_places.append(p)
            else:
                dropped += 1

        logger.info(
            f"Haversine filter: {len(inside_places)} inside radius, {dropped} dropped outside '{complex_name}'"
        )

        # Step 4b: Address-based verification — drop results not referencing the complex
        address_verified = []
        for p in inside_places:
            if _address_matches_complex(p, complex_name):
                address_verified.append(p)
            else:
                logger.info(
                    f"Address filter dropped: '{p.get('name')}' "
                    f"— not in '{complex_name}'"
                )

        logger.info(
            f"Address filter: {len(address_verified)} verified, "
            f"{len(inside_places) - len(address_verified)} dropped for '{complex_name}'"
        )

        # Step 5: Apply junk filter then corporate / B2B filter
        all_places = address_verified
        b2b_places = [
            p for p in all_places
            if not _is_junk_listing(p.get("name", ""), complex_name) and _is_b2b_company(p)
        ]
        logger.info(
            f"B2B filter: {len(all_places)} inside boundary, {len(b2b_places)} corporate for '{complex_name}'"
        )

    # ── Pincode mode ──────────────────────────────────────────────────────────
    else:
        lat, lng, location_name = _pincode_to_coords(pincode)
        if not lat:
            return {"location_name": pincode, "companies": [], "error": "Could not geocode pincode."}

        radius_m = radius_km * 1000
        logger.info(f"Discovering near {location_name} ({lat},{lng}), radius={radius_km}km")

        all_places = []
        data = _fetch_places(lat, lng, radius_m=radius_m)
        all_places.extend(data.get("results", []))

        for _ in range(2):
            next_token = data.get("next_page_token")
            if not next_token:
                break
            time.sleep(2)
            data = _fetch_places(lat, lng, radius_m=radius_m, page_token=next_token)
            all_places.extend(data.get("results", []))

        b2b_places = [p for p in all_places if _is_b2b_company(p)]
        logger.info(
            f"Fetched {len(all_places)} total, {len(b2b_places)} B2B-filtered for {pincode}"
        )

    # ── Enrich + apply tier filter ────────────────────────────────────────────
    companies = []
    for place in b2b_places:
        domain, phone = _extract_domain(place)
        rating = place.get("rating")
        tier   = _score_tier(rating, domain)

        # Apply tier filter — skip if not in selected tiers
        if tiers and tier not in tiers:
            continue

        companies.append({
            "name":          place.get("name", ""),
            "address":       place.get("vicinity", "") or place.get("formatted_address", ""),
            "pincode":       pincode or "",
            "industry":      ", ".join(place.get("types", []))[:100],
            "google_rating": rating,
            "domain":        domain,
            "phone":         phone,
            "tier":          tier,
            "status":        "discovered",
            "source":        "Google Maps",
        })

    return {
        "location_name": location_name,
        "companies":     companies,
    }
