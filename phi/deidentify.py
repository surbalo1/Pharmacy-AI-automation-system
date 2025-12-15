"""
phi/deidentify.py - strips patient identifiers before AI processing
replaces real data with tokens like [NAME_1], [PHONE_1], etc
"""

import re
import uuid
from typing import Dict, Tuple
from datetime import datetime

from .models import DeidentifiedData


# patterns to catch PHI
PATTERNS = {
    "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    "dob": r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    "rx_num": r'\bRX\d{6,}\b',
}

# common name patterns - basic list, expand as needed
# in prod you'd use a proper NER model
COMMON_NAMES = [
    r'\b(Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
]


def deidentify(text: str, extra_pii: Dict[str, str] = None) -> DeidentifiedData:
    """
    strip PHI from text
    
    args:
        text: raw text that might have patient info
        extra_pii: known values to replace (like patient name from db)
    
    returns:
        DeidentifiedData with clean text and token map
    """
    token_map = {}
    clean_text = text
    counter = {}
    
    # first replace any known PII we pass in
    if extra_pii:
        for key, value in extra_pii.items():
            if value and value in clean_text:
                token_type = key.upper()
                counter[token_type] = counter.get(token_type, 0) + 1
                token = f"[{token_type}_{counter[token_type]}]"
                token_map[token] = value
                clean_text = clean_text.replace(value, token)
    
    # run pattern matching
    for pii_type, pattern in PATTERNS.items():
        matches = re.findall(pattern, clean_text, re.IGNORECASE)
        for match in matches:
            token_type = pii_type.upper()
            counter[token_type] = counter.get(token_type, 0) + 1
            token = f"[{token_type}_{counter[token_type]}]"
            token_map[token] = match
            clean_text = clean_text.replace(match, token)
    
    # check for name patterns
    for pattern in COMMON_NAMES:
        matches = re.findall(pattern, clean_text)
        for match in matches:
            counter["NAME"] = counter.get("NAME", 0) + 1
            token = f"[NAME_{counter['NAME']}]"
            # match is tuple from regex groups, get full match
            full_match = match if isinstance(match, str) else match[0]
            token_map[token] = full_match
            clean_text = clean_text.replace(full_match, token)
    
    return DeidentifiedData(
        text=clean_text,
        token_map=token_map,
        created_at=datetime.now()
    )


def quick_check(text: str) -> bool:
    """
    quick check if text might contain PHI
    use this before running full deidentify
    """
    for pattern in PATTERNS.values():
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
