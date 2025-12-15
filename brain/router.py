"""
brain/router.py - routes incoming events to correct workflow
figures out what to do with each request
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class EventType(Enum):
    CHAT = "chat"
    SMS = "sms"
    EMAIL = "email"
    CALL = "call"
    WEBHOOK = "webhook"


class Intent(Enum):
    # patient intents
    RX_STATUS = "rx_status"
    REFILL_REQUEST = "refill_request"
    COMPOUND_QUESTION = "compound_question"
    NEW_PATIENT = "new_patient"
    GENERAL_QUESTION = "general_question"
    
    # provider intents
    PROVIDER_UPDATE = "provider_update"
    NEW_RX = "new_rx"
    
    # other
    UNKNOWN = "unknown"
    HUMAN_NEEDED = "human_needed"


@dataclass
class RouteResult:
    handler: str  # which handler to use
    intent: Intent
    confidence: float
    needs_human: bool = False
    metadata: Dict[str, Any] = None


# keyword mappings for quick intent detection
INTENT_KEYWORDS = {
    Intent.RX_STATUS: ["where is", "status", "ready", "when will", "order"],
    Intent.REFILL_REQUEST: ["refill", "renew", "more of", "running out", "need more"],
    Intent.COMPOUND_QUESTION: ["compound", "custom", "make", "formulate", "cream", "capsule"],
    Intent.NEW_PATIENT: ["new patient", "first time", "never been", "start", "begin"],
}


def detect_intent(text: str) -> tuple[Intent, float]:
    """
    basic intent detection from text
    returns intent and confidence score
    """
    text_lower = text.lower()
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                # found a match - confidence based on keyword specificity
                confidence = 0.7 if len(kw) > 5 else 0.5
                return intent, confidence
    
    return Intent.UNKNOWN, 0.3


def route_event(event_type: EventType, payload: Dict[str, Any]) -> RouteResult:
    """
    main routing function
    takes an event and figures out where to send it
    """
    text = payload.get("message", "") or payload.get("body", "") or ""
    
    intent, confidence = detect_intent(text)
    
    # map event types to handlers
    handler_map = {
        EventType.CHAT: "handlers.chat",
        EventType.SMS: "handlers.sms",
        EventType.EMAIL: "handlers.email",
        EventType.CALL: "handlers.voice",
    }
    
    handler = handler_map.get(event_type, "handlers.fallback")
    
    # low confidence or unknown = human needed
    needs_human = confidence < 0.5 or intent == Intent.UNKNOWN
    
    return RouteResult(
        handler=handler,
        intent=intent,
        confidence=confidence,
        needs_human=needs_human,
        metadata={"original_text": text[:100]}  # truncate for logging
    )


def should_escalate(intent: Intent, confidence: float) -> bool:
    """
    check if this needs human intervention
    """
    # always escalate these
    if intent in [Intent.HUMAN_NEEDED, Intent.NEW_RX]:
        return True
    
    # low confidence = escalate
    if confidence < 0.6:
        return True
    
    return False
