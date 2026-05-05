import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from discovery import calculate_run_accuracy


def test_calculate_run_accuracy_handles_empty_input():
    pct, confidence = calculate_run_accuracy([], "Mindspace Airoli")
    assert pct == 0.0
    assert confidence == "N/A"


def test_calculate_run_accuracy_high_confidence_when_addresses_match():
    companies = [
        {"name": "Acme Pvt Ltd", "address": "Tower 1, Mindspace Airoli, Navi Mumbai"},
        {"name": "Beta Corp", "address": "Mindspace Airoli, Sector 1"},
        {"name": "Gamma Ltd", "address": "Near Mindspace Airoli, TTC Industrial Area"},
        {"name": "Delta Inc", "address": "Mindspace Airoli Campus"},
        {"name": "Epsilon Tech", "address": "Bldg B, Mindspace Airoli"},
    ]
    pct, confidence = calculate_run_accuracy(companies, "Mindspace Airoli")
    assert pct >= 80.0
    assert confidence == "High"
