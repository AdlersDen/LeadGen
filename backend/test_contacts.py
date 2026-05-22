import asyncio
from contacts import _search_apollo, _search_hunter, find_contacts
import logging

logging.basicConfig(level=logging.INFO)

def run_tests():
    company = "Titan Company Limited"
    domain = "titan.co.in"
    
    print(f"\n--- Testing Apollo.io ---")
    apollo_results = _search_apollo(company, domain)
    print(f"Apollo found {len(apollo_results)} contacts.")
    if apollo_results:
        print("First Apollo contact:", apollo_results[0])
        
    print(f"\n--- Testing Hunter.io ---")
    hunter_results = _search_hunter(domain)
    print(f"Hunter found {len(hunter_results)} contacts.")
    if hunter_results:
        print("First Hunter contact:", hunter_results[0])

if __name__ == "__main__":
    run_tests()
