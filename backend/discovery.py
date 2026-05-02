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

# Large campus / IT park keywords for expanded radius detection
LARGE_CAMPUS_KEYWORDS = [
    "tech park", "it park", "knowledge park", "business park",
    "industrial area", "midc", "sez", "special economic zone",
    "mindspace", "manyata", "nesco", "hinjewadi", "electronic city",
    "cyber city", "cybercity", "hitech city", "whitefield",
    "gigaplex", "airoli", "powai", "andheri midc"
]

# Single-building/tower keywords — tighter radius
SMALL_BUILDING_KEYWORDS = [
    "tower", "house", "centre", "center", "plaza",
    "court", "square", "point"
]

# Adjacent complexes that share a street/pin and often bleed into each other
ADJACENT_COMPLEX_CONFLICTS = {
    "nirlon": ["nesco", "it 4, nesco"],
    "nesco": ["nirlon", "nirlon knowledge"],
    "equinox": ["kanakia", "zillion", "trade centre", "trade center"],
    "mindspace": ["kanchpada", "new link road", "link road"],
    "one bkc": ["platina", "trade world"],
    "the capital": ["il&fs financial centre", "peninsula business park"],
    "urmi": ["peninsula business park", "marathon futurex"],
    "manyata": ["loma it park", "aurum"],
    "reliance corporate": ["aurum q parc", "loma it park"],
    "am naik": ["atl corporate", "saki vihar", "emerald isle"],
    "cyber city": [
        "phase 1,", "phase i,", "phase 2,", "phase ii,",
        "phase 4,", "phase iv,", "phase 5,", "phase v,",
        "south city", "sector 24,", "sector 25,",
        "golf course road", "mg road gurgaon"
    ],
    "dlf cyber": [
        "phase 1", "phase 2", "phase 4", "phase 5",
        "south city", "sector 24", "sector 25"
    ],
}

# Known IT/business parks for cross-park contamination detection
KNOWN_IT_PARKS = [
    "nirlon", "nesco", "equinox", "mindspace", "one bkc", "the capital",
    "urmi estate", "manyata", "reliance corporate", "bkc", "peninsula business park",
    "marathon futurex", "loma it park", "aurum q parc", "kanakia", "zillion",
    "platina", "trade world", "trade centre", "trade center", "il&fs financial centre",
    "gigaplex", "hinjewadi", "magarpatta", "cybercity", "hitech city",
    "prestige tech park", "bagmane", "rmz ecospace", "embassy golf links",
]

# Fixed radius overrides for specific complexes (bypass all viewport logic)
LARGE_CAMPUS_OVERRIDES = {
    "mindspace malad": 500,
    "mindspace airoli": 1000,
    "raheja mindspace": 1200,
    "equinox business park": 350,
    "equinox kurla": 350,
    "urmi estate": 200,
    "one international center": 200,
    "odyssey it park": 250,
    "ashar it park": 250,
    "centrum business": 250,
    "opal square": 200,
    "am naik tower": 150,
    "l&t am naik": 150,
}

# Dense industrial/IT corridors where address strictness must be absolute
DENSE_IT_CORRIDORS = [
    "wagle", "wagle estate", "marol industrial",
    "seepz", "midc andheri", "turbhe midc", "mahape midc"
]

# Proximity prepositions that signal a place is near but not inside the complex
PROXIMITY_PREPOSITIONS = [
    "opposite ", "opp ", "opp.", "near ", "beside ",
    "next to ", "adjacent to ", "behind "
]

# Single-tenant campus name patterns — handled as a fast path
SINGLE_TENANT_PATTERNS = [
    "tcs ", "tcs campus", "infosys campus", "wipro campus",
    "hcl campus", "accenture campus", "cognizant campus"
]

# Government / gated SEZ overrides with hardcoded coords (find_place often fails for these)
GOVERNMENT_SEZ_OVERRIDES = {
    "seepz": {
        "lat": 19.1197, "lng": 72.8680, "radius": 800,
        "aliases": ["seepz", "andheri east", "sez", "santacruz electronics"]
    },
    "millennium business park": {
        "lat": 19.1147, "lng": 72.9010, "radius": 400,
        "aliases": ["millennium business", "mahape", "millennium park"]
    },
    "jio world centre": {
        "lat": 19.0664, "lng": 72.8652, "radius": 300,
        "aliases": ["jio world", "bkc", "bandra kurla", "jio world centre"]
    },
    "gift city": {
        "lat": 23.1685, "lng": 72.6840, "radius": 1000,
        "aliases": ["gift city", "gift sez", "gandhinagar", "ifsc", "gujarat international"]
    },
    "gift sez": {
        "lat": 23.1685, "lng": 72.6840, "radius": 1000,
        "aliases": ["gift city", "gift sez", "gandhinagar", "ifsc", "gujarat international"]
    },
}

# Known aliases for complexes whose Google Maps addresses use different words
COMPLEX_ADDRESS_ALIASES = {
    "seepz": ["seepz", "andheri east", "sez", "santacruz electronics", "midc andheri"],
    "millennium business": ["millennium business", "mahape", "millennium park"],
    "jio world": ["jio world", "bkc", "bandra kurla"],
    "nesco": ["nesco", "nesco it", "western express", "goregaon"],
    "nirlon": ["nirlon", "nirlon knowledge", "western express", "goregaon"],
    "bandra kurla": ["bkc", "bandra kurla", "kurla"],
    "one bkc": ["bkc", "bandra kurla", "one bkc"],
    "gigaplex": ["gigaplex", "airoli", "thane belapur"],
    "manyata": ["manyata", "nagavara", "hebbal"],
    "hinjewadi": ["hinjewadi", "rajiv gandhi", "phase"],
    "magarpatta": ["magarpatta", "hadapsar", "cybercity"],
    "gift city": ["gift city", "gift sez", "gandhinagar", "ifsc", "gujarat international"],
    "gift sez": ["gift city", "gift sez", "gandhinagar", "ifsc", "gujarat international"],
    "cyber city": ["cyber city", "cybercity", "dlf cyber", "sector 25", "sector 24", "gurgaon"],
    "eon": ["eon", "kharadi", "eon free zone", "weikfield"],
    "magarpatta cybercity": ["magarpatta", "hadapsar", "cybercity", "magarpatta city"],
}

# Mixed-use venues that respond poorly to nearby keyword searches — use text search instead
MIXED_USE_VENUES = [
    "jio world centre", "worli", "lower parel",
    "phoenix mills", "one world centre", "peninsula business park",
    "trade centre", "wockhardt towers", "express towers"
]

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
    "laundry", "funeral_home", "cemetery", "home_goods_store", "store",
    "natural_feature", "park", "airport"
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


def get_radius_from_viewport(viewport: dict, complex_name: str = "") -> float:
    """
    Derives a search radius (metres) from a Google Maps viewport dict.
    Applies large-campus detection to expand the radius for known IT/business parks.
    Checks LARGE_CAMPUS_OVERRIDES first for fixed-radius complexes.
    """
    cn_lower = complex_name.lower()

    # Fixed override check — bypasses all other logic
    for key, fixed_radius in LARGE_CAMPUS_OVERRIDES.items():
        if key in cn_lower:
            logger.info(f"Radius override for '{complex_name}': {fixed_radius} m (from LARGE_CAMPUS_OVERRIDES)")
            return float(fixed_radius)

    is_large_campus = any(kw in cn_lower for kw in LARGE_CAMPUS_KEYWORDS)

    ne = viewport.get("northeast", {})
    sw = viewport.get("southwest", {})
    if not ne or not sw:
        return 1000.0 if is_large_campus else 800.0

    diagonal = haversine_distance(
        sw.get("lat", 0), sw.get("lng", 0),
        ne.get("lat", 0), ne.get("lng", 0),
    )
    radius = diagonal / 2

    # Large campus override — expand aggressively, cap at 2000 m
    if is_large_campus:
        return max(800.0, min(radius * 1.5, 2000.0))

    # Small building cap — tighten radius if not a large campus
    cn_lower = complex_name.lower()
    if not is_large_campus and any(kw in cn_lower for kw in SMALL_BUILDING_KEYWORDS):
        return max(150.0, min(radius, 400.0))

    # Three-tier radius logic based on complex physical size
    if radius <= 300:
        return max(150.0, radius)   # Single building — very tight
    elif radius <= 700:
        return radius * 0.80        # Medium complex — slight shrink
    else:
        return min(radius, 1200.0)  # Large area — cap at 1200 m


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


# Locality-to-city mapping for complex name simplification
_LOCALITY_TO_CITY = {
    "mahape": "Navi Mumbai", "juinagar": "Navi Mumbai", "ghansoli": "Navi Mumbai",
    "turbhe": "Navi Mumbai", "airoli": "Navi Mumbai",
    "kharadi": "Pune", "hinjewadi": "Pune",
    "whitefield": "Bangalore", "nagavara": "Bangalore",
}


def simplify_complex_name(complex_name: str) -> str:
    """Replace known locality words with their parent city name."""
    words = complex_name.split()
    out = []
    for w in words:
        replacement = _LOCALITY_TO_CITY.get(w.lower())
        if replacement and replacement not in " ".join(out):
            out.append(replacement)
        else:
            out.append(w)
    return " ".join(out)


CITY_WORDS = {
    "mumbai", "pune", "bangalore", "bengaluru", "gurugram",
    "gurgaon", "delhi", "hyderabad", "chennai", "kolkata",
    "noida", "thane", "navi", "london", "dubai", "singapore",
    "vashi", "sector", "kharghar", "belapur", "ghansoli",
    "turbhe", "sanpada", "juinagar", "nerul", "seawoods",
    "mahape", "airoli", "andheri", "goregaon", "malad",
    "kurla", "dadar", "worli", "parel"
}


# Phrases that must be preserved as units in hint extraction (not split into individual words)
PRESERVE_PHRASES = [
    "cyber city", "cyber hub", "gift city", "gift sez",
    "world trade", "knowledge park", "business park",
    "tech park", "it park", "free zone"
]


def _extract_complex_hint(complex_name: str) -> list:
    """Extract key words from complex name, removing city names.
    Preserves multi-word phrases (e.g. 'cyber city') as single hint tokens
    so they match correctly in address strings.
    """
    cn_lower = complex_name.lower()
    hints = []
    remaining = cn_lower

    # Extract and preserve multi-word phrases first
    for phrase in PRESERVE_PHRASES:
        if phrase in remaining:
            hints.append(phrase)
            remaining = remaining.replace(phrase, " ")  # blank out so words aren't re-added

    # Process remaining individual words
    for w in remaining.split():
        if w not in CITY_WORDS and len(w) > 2:
            hints.append(w)

    return hints


def _get_accepted_aliases(complex_name: str) -> list:
    """
    Returns the accepted alias word list for this complex.
    Falls back to _extract_complex_hint() if no alias entry found.
    """
    cn_lower = complex_name.lower()
    for key, aliases in COMPLEX_ADDRESS_ALIASES.items():
        if key in cn_lower:
            return aliases
    return _extract_complex_hint(complex_name)


def calculate_run_accuracy(companies: list, complex_name: str) -> tuple[float, str]:
    """
    Calculates accuracy based on how many results contain at least one hint word
    in their address.
    Returns (accuracy_percentage, confidence_label).
    """
    if not complex_name or not companies:
        return 0.0, "N/A"
    
    hint_words = _get_accepted_aliases(complex_name)
    if not hint_words:
        return 100.0, "High"  # If no hints, we can't verify, assume correct.
        
    matches = 0
    for c in companies:
        address = (c.get("address", "") + " " + c.get("name", "")).lower()
        if any(w in address for w in hint_words):
            matches += 1
            
    pct = (matches / len(companies)) * 100
    if pct >= 80:
        conf = "High"
    elif pct >= 50:
        conf = "Medium"
    else:
        conf = "Low"
    return pct, conf


def _is_dense_corridor(complex_name: str) -> bool:
    """Returns True if the complex is inside a known dense industrial/IT corridor."""
    cn_lower = complex_name.lower()
    return any(kw in cn_lower for kw in DENSE_IT_CORRIDORS)


def _is_mixed_use_venue(complex_name: str) -> bool:
    """Returns True if the complex is a mixed-use venue that needs text search."""
    cn_lower = complex_name.lower()
    return any(kw in cn_lower for kw in MIXED_USE_VENUES)


def _address_matches_complex(place: dict, complex_name: str) -> bool:
    """
    Returns True if the place's address or name contains at least one
    accepted alias or hint word from the complex name.
    In dense corridors, zero matches = automatic rejection.
    """
    hint_words = _get_accepted_aliases(complex_name)
    if not hint_words:
        return True  # can't verify, allow through
    address = (
        place.get("vicinity", "") + " " +
        place.get("name", "")
    ).lower()
    matches = sum(1 for word in hint_words if word in address)
    if _is_dense_corridor(complex_name) and matches == 0:
        return False  # strict — no proximity fallback in dense corridors
    return matches >= 1


def _is_proximity_address(place: dict, complex_name: str) -> bool:
    """
    Returns True if a proximity preposition appears in the place's
    vicinity address AND the complex hint words appear after it.
    Catches "Opposite Mindspace", "Near Nesco IT Park" etc.
    """
    hint_words = _extract_complex_hint(complex_name)
    if not hint_words:
        return False
    address = (
        place.get("vicinity", "") + " " +
        place.get("formatted_address", "")
    ).lower()
    for prep in PROXIMITY_PREPOSITIONS:
        if prep in address:
            after = address[address.index(prep) + len(prep):]
            if any(w in after for w in hint_words):
                logger.info(
                    f"Proximity filter: '{place.get('name')}' is '{prep.strip()}' "
                    f"'{complex_name}' — dropping"
                )
                return True
    return False


JUNK_NAME_PATTERNS = [
    "internal road", "gate ", "entrance", "exit",
    "parking lot", "bus stop", "metro station",
    "food court", "canteen", "cafeteria", "atm",
    "lake", "helipad", "garden", "ground", "playground",
    "security", "reception", "lobby"
]


def _is_conflicting_complex(place: dict, complex_name: str) -> bool:
    """
    Returns True if the place's address or name contains a known adjacent
    complex that conflicts with the one being searched.
    """
    cn_lower = complex_name.lower()
    # Find which conflict list to use (match partial key)
    conflict_list = []
    for key, conflicts in ADJACENT_COMPLEX_CONFLICTS.items():
        if key in cn_lower:
            conflict_list = conflicts
            break
    if not conflict_list:
        return False
    address = (
        place.get("vicinity", "") + " " + place.get("name", "")
    ).lower()
    return any(conflict in address for conflict in conflict_list)


def _mentions_different_park(place: dict, complex_name: str) -> bool:
    """
    Returns True if the place's address or name references a different
    known IT/business park than the one being searched.
    """
    cn_lower = complex_name.lower()
    address = (
        place.get("vicinity", "") + " " + place.get("name", "")
    ).lower()
    for park in KNOWN_IT_PARKS:
        if park in cn_lower:
            continue  # This is the park we're searching — skip it
        if park in address:
            return True
    return False


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

        # Fast path: single-tenant campus — return just that company without full pipeline
        cn_lower = complex_name.lower()
        if any(pat in cn_lower for pat in SINGLE_TENANT_PATTERNS):
            logger.info(f"Single-tenant campus detected: '{complex_name}' — using fast path")
            fp_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            try:
                st_resp = requests.get(fp_url, params={
                    "input": complex_name, "inputtype": "textquery",
                    "fields": "geometry,name,place_id", "key": MAPS_API_KEY,
                }, timeout=10)
                st_resp.raise_for_status()
                st_candidates = st_resp.json().get("candidates", [])
                if st_candidates:
                    c = st_candidates[0]
                    c_name = c.get("name", complex_name)
                    return {
                        "location_name": complex_name,
                        "companies": [{
                            "name": c_name,
                            "address": complex_name,
                            "pincode": "",
                            "industry": "it_company",
                            "google_rating": None,
                            "domain": "",
                            "phone": "",
                            "tier": "A",
                            "status": "discovered",
                            "source": "Google Maps (single-tenant campus)",
                        }],
                    }
            except Exception as e:
                logger.warning(f"Single-tenant fast path failed for '{complex_name}': {e}")
                # Fall through to full pipeline

        # Step 1: Resolve the complex to exact coordinates + viewport
        # First check GOVERNMENT_SEZ_OVERRIDES for hardcoded coords
        sez_override = None
        for sez_key, sez_data in GOVERNMENT_SEZ_OVERRIDES.items():
            if sez_key in complex_name.lower():
                sez_override = sez_data
                logger.info(f"SEZ override matched for '{complex_name}': using hardcoded coords ({sez_data['lat']}, {sez_data['lng']})")
                break

        if sez_override:
            cx_lat = sez_override["lat"]
            cx_lng = sez_override["lng"]
            radius_m = float(sez_override["radius"])
            logger.info(f"Complex '{complex_name}' → SEZ override ({cx_lat}, {cx_lng}), radius={radius_m:.0f} m")
        else:
            # Step 1: Resolve the complex to exact coordinates + viewport (3-strategy fallback)
            fp_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

            def _find_place(query: str):
                """Call find_place and return candidates list."""
                try:
                    resp = requests.get(fp_url, params={
                        "input": query, "inputtype": "textquery",
                        "fields": "geometry,name", "key": MAPS_API_KEY,
                    }, timeout=10)
                    resp.raise_for_status()
                    return resp.json().get("candidates", [])
                except Exception as e:
                    logger.error(f"find_place HTTP error for '{query}': {e}")
                    return []

            # Strategy 1: exact name
            candidates = _find_place(complex_name)

            # Strategy 2: simplified name (swap locality → city)
            if not candidates:
                simplified = simplify_complex_name(complex_name)
                if simplified != complex_name:
                    logger.info(f"find_place retry with simplified name: '{simplified}'")
                    candidates = _find_place(simplified)

            # Strategy 3: geocode fallback
            if not candidates:
                logger.info(f"find_place failed — falling back to geocode for '{complex_name}'")
                try:
                    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
                    geo_resp = requests.get(geo_url, params={"address": complex_name, "key": MAPS_API_KEY}, timeout=10)
                    geo_resp.raise_for_status()
                    geo_results = geo_resp.json().get("results", [])
                    if geo_results:
                        candidates = [{"geometry": geo_results[0]["geometry"]}]
                        logger.info(f"Geocode fallback found: {geo_results[0].get('formatted_address')}")
                except Exception as e:
                    logger.error(f"Geocode fallback failed for '{complex_name}': {e}")

            if not candidates:
                msg = f"Complex '{complex_name}' not found via find_place or geocode."
                logger.error(msg)
                return {"location_name": complex_name, "companies": [], "error": msg}

            geometry  = candidates[0].get("geometry", {})
            location  = geometry.get("location", {})
            viewport  = geometry.get("viewport", {})
            cx_lat    = location.get("lat")
            cx_lng    = location.get("lng")

            if not cx_lat or not cx_lng:
                logger.error(f"find_place returned geometry without location for '{complex_name}'")
                return {"location_name": complex_name, "companies": [], "error": "Could not resolve complex coordinates."}

            # Step 2: Derive search radius from viewport
            radius_m = get_radius_from_viewport(viewport, complex_name)
            logger.info(
                f"Complex '{complex_name}' → ({cx_lat}, {cx_lng}), viewport radius={radius_m:.0f} m"
            )

        # Step 3: Search for places — text search for mixed-use venues, nearby search otherwise
        import time as _time
        all_raw_places_dict = {}

        if _is_mixed_use_venue(complex_name):
            logger.info(f"Mixed-use venue detected for '{complex_name}' — using text search")
            ts_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            for ts_query in [
                f"private limited office {complex_name}",
                f"corporate office {complex_name}",
                f"pvt ltd {complex_name}",
            ]:
                try:
                    ts_resp = requests.get(ts_url, params={"query": ts_query, "key": MAPS_API_KEY}, timeout=15)
                    ts_resp.raise_for_status()
                    for p in ts_resp.json().get("results", []):
                        all_raw_places_dict[p.get("place_id")] = p
                except Exception as e:
                    logger.error(f"Text search failed for '{ts_query}': {e}")
        else:
            nb_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

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

        # Step 5: Apply junk filter, conflict filter, then corporate / B2B filter
        all_places = address_verified
        b2b_places = []
        for p in all_places:
            name = p.get("name", "")
            if _is_junk_listing(name, complex_name):
                continue
            if _is_proximity_address(p, complex_name):
                continue
            if _is_conflicting_complex(p, complex_name):
                logger.info(f"Conflict filter dropped: '{name}' — adjacent complex in '{complex_name}'")
                continue
            if _mentions_different_park(p, complex_name):
                logger.info(f"Park filter dropped: '{name}' — references different park")
                continue
            if _is_b2b_company(p):
                b2b_places.append(p)
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
