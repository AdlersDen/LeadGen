import os
import pytest
import sys

# Ensure backend module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from discovery import discover_companies, calculate_run_accuracy

TEST_CASES = [
    "Wagle Industrial Estate",
    "Magarpatta City Pune",
    "The Capital BKC Mumbai",
    "Urmi Estate Mumbai",
    "Mindspace Airoli"
]

def validate_results(complex_name, companies):
    pct, conf = calculate_run_accuracy(companies, complex_name)
    print(f"Results for {complex_name}: {len(companies)} companies, Accuracy: {pct:.1f}% ({conf})")
    assert len(companies) > 0, f"No companies found for {complex_name}"
    assert conf in ["High", "Medium"], f"Low accuracy for {complex_name}: {pct:.1f}%"

@pytest.mark.parametrize("complex_name", TEST_CASES)
def test_discovery(complex_name):
    # Ensure API key is present
    assert os.getenv("GOOGLE_MAPS_API_KEY"), "GOOGLE_MAPS_API_KEY not set"
    
    result = discover_companies(complex_name=complex_name)
    companies = result.get("companies", [])
    
    validate_results(complex_name, companies)
