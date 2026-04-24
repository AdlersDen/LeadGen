"""
Module 3 — Data Cleaning & Normalization
Standardizes company and contact names, verifies email domains via MX records.
PRD §6.3
"""

import re
import dns.resolver
import logging

logger = logging.getLogger(__name__)

def normalize_name(text: str) -> str:
    """
    Standardization (PRD §139):
    - Strips special characters
    - Lowercases names then title cases for display
    - Removes extra whitespace
    """
    if not text:
        return ""
    
    # Remove all non-alphanumeric characters except spaces and hyphens
    cleaned = re.sub(r'[^\w\s\-]', '', text)
    
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Title Case for professional look
    return cleaned.title()

def verify_mx_record(domain: str) -> bool:
    """
    Validation (PRD §141):
    - Performs MX record verification on domain.
    - Prevents sending to domains that cannot receive mail.
    """
    if not domain:
        return False
        
    try:
        # Resolve MX records
        answers = dns.resolver.resolve(domain, 'MX')
        if answers:
            logger.info(f"MX record found for domain: {domain}")
            return True
    except Exception as e:
        logger.warning(f"MX record verification failed for {domain}: {e}")
        
    return False

def clean_contact_data(contact_data: dict) -> dict | None:
    """
    Runs full cleaning suite on a contact record.
    Returns cleaned dict or None if invalid (MX failure).
    """
    full_name = contact_data.get("full_name", "")
    email = contact_data.get("email", "")
    
    if not email or "@" not in email:
        logger.warning(f"Skipping contact {full_name}: Invalid email format.")
        return None
        
    domain = email.split("@")[-1]
    
    # PRD Requirement: Skip if MX check fails
    if not verify_mx_record(domain):
        logger.warning(f"Skipping contact {full_name}: Domain {domain} has no valid MX records.")
        return None
        
    # Standardize names
    contact_data["full_name"] = normalize_name(full_name)
    contact_data["role"] = (contact_data.get("role") or "").strip()
    
    return contact_data

def clean_company_data(company_data: dict) -> dict:
    """Standardizes company name and industry."""
    name = company_data.get("name", "")
    company_data["name"] = normalize_name(name)
    return company_data
