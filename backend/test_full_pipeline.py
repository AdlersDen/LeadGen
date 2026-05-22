"""
End-to-end test: Discover companies in Mumbai business complexes,
then test Apollo + Hunter contact extraction on each.
"""
import logging
from discovery import discover_companies
from contacts import _search_apollo, _search_hunter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

COMPLEXES = [
    "Nirlon Knowledge Park Mumbai",
    "One BKC Mumbai",
    "Equinox Business Park Kurla",
]

def run():
    for cx in COMPLEXES:
        print("\n" + "=" * 60)
        print(f"  COMPLEX: {cx}")
        print("=" * 60)

        result = discover_companies(complex_name=cx, tiers=["A", "B", "C"])
        companies = result.get("companies", [])
        print(f"\nDiscovered {len(companies)} companies")

        # Pick up to 2 companies that have a domain
        targets = [c for c in companies if c.get("domain")][:2]
        if not targets:
            print("  No companies with a domain found — skipping contact test")
            continue

        for comp in targets:
            name = comp["name"]
            domain = comp["domain"]
            print(f"\n  --- {name} ({domain}) ---")

            # Test Apollo
            apollo = _search_apollo(name, domain)
            print(f"  Apollo: {len(apollo)} contacts")
            for c in apollo[:2]:
                print(f"    > {c['full_name']} | {c['email']} | {c['role']}")

            # Test Hunter
            hunter = _search_hunter(domain)
            print(f"  Hunter: {len(hunter)} contacts")
            for c in hunter[:2]:
                print(f"    > {c['full_name']} | {c['email']} | {c['role']}")


if __name__ == "__main__":
    run()
