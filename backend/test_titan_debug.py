"""Debug: Check if Titan appears in raw Google Maps results for Equinox."""
import requests, json, os, math
from dotenv import load_dotenv
load_dotenv()

KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Step 1: Get Equinox coordinates
fp_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
resp = requests.get(fp_url, params={
    "input": "Equinox Business Park Kurla",
    "inputtype": "textquery",
    "fields": "geometry,name",
    "key": KEY,
})
candidates = resp.json().get("candidates", [])
geo = candidates[0]["geometry"]["location"]
cx_lat, cx_lng = geo["lat"], geo["lng"]
print(f"Equinox center: ({cx_lat}, {cx_lng})")

# Step 2: Search for Titan specifically
fp2 = requests.get(fp_url, params={
    "input": "Titan Company Limited Kurla",
    "inputtype": "textquery",
    "fields": "geometry,name,formatted_address,types,place_id",
    "key": KEY,
})
titan_candidates = fp2.json().get("candidates", [])
if titan_candidates:
    t = titan_candidates[0]
    t_geo = t["geometry"]["location"]
    print(f"\nTitan found via find_place:")
    print(f"  Name: {t.get('name')}")
    print(f"  Location: ({t_geo['lat']}, {t_geo['lng']})")
    
    # Calculate distance from Equinox center
    R = 6_371_000
    phi1, phi2 = math.radians(cx_lat), math.radians(t_geo['lat'])
    dphi = math.radians(t_geo['lat'] - cx_lat)
    dlambda = math.radians(t_geo['lng'] - cx_lng)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    print(f"  Distance from Equinox center: {dist:.0f} m")
    print(f"  Within 350m radius? {'YES' if dist <= 350 else 'NO'}")
    print(f"  Within 280m (0.8x350)? {'YES' if dist <= 280 else 'NO'}")

# Step 3: Check what types Titan has via Place Details
if titan_candidates:
    pid = titan_candidates[0].get("place_id")
    if pid:
        det = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params={
            "place_id": pid,
            "fields": "types,name,formatted_address,website",
            "key": KEY,
        })
        result = det.json().get("result", {})
        print(f"\nTitan Place Details:")
        print(f"  Types: {result.get('types', [])}")
        print(f"  Address: {result.get('formatted_address')}")
        print(f"  Website: {result.get('website', 'N/A')}")

# Step 4: Try nearby search with each keyword to see which one catches Titan
print(f"\n{'='*60}")
print("Checking nearby search keywords that return Titan:")
nb_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
for kw in ["office", "corporate", "company", "pvt ltd", "manufacturer", "limited"]:
    resp = requests.get(nb_url, params={
        "location": f"{cx_lat},{cx_lng}",
        "radius": 350,
        "keyword": kw,
        "key": KEY,
    })
    results = resp.json().get("results", [])
    titan_hit = [r for r in results if "titan" in r.get("name", "").lower()]
    print(f"  keyword='{kw}': {len(results)} results, Titan found: {bool(titan_hit)}")
    if titan_hit:
        t = titan_hit[0]
        print(f"    -> {t['name']} | types: {t.get('types',[])} | vicinity: {t.get('vicinity','')}")

# Step 5: Try text search
print(f"\n{'='*60}")
print("Checking text search queries:")
ts_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
for q in ["companies in Equinox Business Park Kurla", "Equinox Building Kurla offices"]:
    resp = requests.get(ts_url, params={"query": q, "key": KEY})
    results = resp.json().get("results", [])
    titan_hit = [r for r in results if "titan" in r.get("name", "").lower()]
    print(f"  query='{q}': {len(results)} results, Titan found: {bool(titan_hit)}")
