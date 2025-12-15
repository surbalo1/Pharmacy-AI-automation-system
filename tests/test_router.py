"""
tests/test_router.py - tests for brain router
"""

import pytest
from brain.router import detect_intent, route_event, Intent, EventType


class TestIntentDetection:
    def test_rx_status(self):
        intent, conf = detect_intent("Where is my prescription?")
        assert intent == Intent.RX_STATUS
    
    def test_refill(self):
        intent, conf = detect_intent("I need to refill my medication")
        assert intent == Intent.REFILL_REQUEST
    
    def test_compound(self):
        intent, conf = detect_intent("Do you compound testosterone cream?")
        assert intent == Intent.COMPOUND_QUESTION
    
    def test_new_patient(self):
        intent, conf = detect_intent("I'm a new patient interested in your pharmacy")
        assert intent == Intent.NEW_PATIENT
    
    def test_unknown(self):
        intent, conf = detect_intent("asdfasdfasdf")
        assert intent == Intent.UNKNOWN
        assert conf < 0.5


class TestEventRouting:
    def test_chat_route(self):
        result = route_event(EventType.CHAT, {"message": "Hello"})
        assert result.handler == "handlers.chat"
    
    def test_sms_route(self):
        result = route_event(EventType.SMS, {"message": "Test"})
        assert result.handler == "handlers.sms"
    
    def test_high_confidence(self):
        result = route_event(EventType.CHAT, {"message": "I need to refill my meds"})
        assert result.needs_human == False
        assert result.intent == Intent.REFILL_REQUEST
    
    def test_low_confidence_escalate(self):
        result = route_event(EventType.CHAT, {"message": "xyzzy"})
        assert result.needs_human == True
