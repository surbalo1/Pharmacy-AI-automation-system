"""
tests/test_phi.py - tests for phi module
"""

import pytest
from phi.deidentify import deidentify, quick_check
from phi.reidentify import reidentify, partial_reidentify


class TestDeidentify:
    def test_deidentify_phone(self):
        text = "Call me at 555-123-4567"
        result = deidentify(text)
        
        assert "555-123-4567" not in result.text
        assert "[PHONE_1]" in result.text
        assert "[PHONE_1]" in result.token_map
    
    def test_deidentify_email(self):
        text = "Email me at test@email.com"
        result = deidentify(text)
        
        assert "test@email.com" not in result.text
        assert "[EMAIL_1]" in result.text
    
    def test_deidentify_ssn(self):
        text = "My SSN is 123-45-6789"
        result = deidentify(text)
        
        assert "123-45-6789" not in result.text
        assert "[SSN_1]" in result.text
    
    def test_deidentify_dob(self):
        text = "Born on 12/25/1990"
        result = deidentify(text)
        
        assert "12/25/1990" not in result.text
        assert "[DOB_1]" in result.text
    
    def test_deidentify_rx(self):
        text = "Prescription RX1234567"
        result = deidentify(text)
        
        assert "RX1234567" not in result.text
        assert "[RX_NUM_1]" in result.text
    
    def test_extra_pii(self):
        text = "Hello John Smith"
        result = deidentify(text, {"name": "John Smith"})
        
        assert "John Smith" not in result.text
        assert "[NAME_1]" in result.text
    
    def test_quick_check_positive(self):
        assert quick_check("Call 555-123-4567") == True
    
    def test_quick_check_negative(self):
        assert quick_check("Hello world") == False


class TestReidentify:
    def test_reidentify_simple(self):
        token_map = {"[PHONE_1]": "555-123-4567"}
        text = "Call me at [PHONE_1]"
        
        result = reidentify(text, token_map)
        assert result == "Call me at 555-123-4567"
    
    def test_reidentify_multiple(self):
        token_map = {
            "[PHONE_1]": "555-123-4567",
            "[NAME_1]": "John"
        }
        text = "Hi [NAME_1], call [PHONE_1]"
        
        result = reidentify(text, token_map)
        assert result == "Hi John, call 555-123-4567"
    
    def test_partial_reidentify(self):
        token_map = {
            "[PHONE_1]": "555-123-4567",
            "[NAME_1]": "John"
        }
        text = "Hi [NAME_1], call [PHONE_1]"
        
        result = partial_reidentify(text, token_map, ["NAME"])
        assert "[NAME_1]" not in result
        assert "[PHONE_1]" in result  # phone stays masked


class TestRoundTrip:
    def test_full_cycle(self):
        original = "Hi, I'm John Smith. Call me at 555-123-4567"
        
        # deidentify
        safe = deidentify(original, {"name": "John Smith"})
        assert "John Smith" not in safe.text
        assert "555-123-4567" not in safe.text
        
        # reidentify
        restored = reidentify(safe.text, safe.token_map)
        assert restored == original
