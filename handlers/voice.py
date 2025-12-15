"""
handlers/voice.py - voice agent logic
handles inbound calls via vapi
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import uuid

from brain.router import detect_intent, Intent
from brain.audit import log_action
from integrations.ghl import ghl


router = APIRouter()


class CallEvent(BaseModel):
    call_id: str
    caller_number: str
    event_type: str  # started, ended, transcription
    transcription: Optional[str] = None
    duration: Optional[int] = None


class VoiceResponse(BaseModel):
    action: str  # say, transfer, hangup
    message: Optional[str] = None
    transfer_to: Optional[str] = None


# caller type detection keywords
PROVIDER_KEYWORDS = ["doctor", "physician", "nurse", "clinic", "hospital", "prescriber", "dr."]
PATIENT_KEYWORDS = ["prescription", "medication", "refill", "pickup"]


# pre-approved responses
APPROVED_RESPONSES = {
    "hours": "Our pharmacy is open Monday through Friday, 9 AM to 6 PM, and Saturday 9 AM to 1 PM. We're closed on Sundays.",
    "location": "We're located at 123 Main Street. There's free parking available in the back of the building.",
    "fax": "Our fax number is 555-123-4568.",
    "hold": "Please hold while I transfer you to a team member.",
}


def detect_caller_type(transcription: str) -> str:
    """figure out if caller is patient, provider, or other"""
    text_lower = transcription.lower()
    
    for kw in PROVIDER_KEYWORDS:
        if kw in text_lower:
            return "provider"
    
    for kw in PATIENT_KEYWORDS:
        if kw in text_lower:
            return "patient"
    
    return "unknown"


@router.post("/event")
async def handle_call_event(event: CallEvent):
    """
    handle vapi call events
    """
    session_id = event.call_id
    
    log_action(f"call_{event.event_type}", session_id, f"from={event.caller_number}")
    
    if event.event_type == "started":
        # new call - greet
        return VoiceResponse(
            action="say",
            message="Thank you for calling. How can I help you today?"
        )
    
    if event.event_type == "ended":
        # log the call in ghl
        contacts = ghl.search_contacts(event.caller_number)
        if contacts:
            ghl.add_note(
                contacts[0].get("id"),
                f"Call received - duration: {event.duration}s"
            )
        return {"status": "logged"}
    
    if event.event_type == "transcription" and event.transcription:
        return await process_transcription(event)
    
    return {"status": "ok"}


async def process_transcription(event: CallEvent) -> VoiceResponse:
    """process caller speech and decide response"""
    session_id = event.call_id
    text = event.transcription.lower()
    
    # check for approved quick responses
    for keyword, response in APPROVED_RESPONSES.items():
        if keyword in text:
            log_action("call_auto_response", session_id, keyword)
            return VoiceResponse(action="say", message=response)
    
    # detect caller type
    caller_type = detect_caller_type(event.transcription)
    
    # detect intent
    intent, confidence = detect_intent(event.transcription)
    
    # provider calls always go to human
    if caller_type == "provider":
        log_action("call_transfer", session_id, "provider call")
        return VoiceResponse(
            action="transfer",
            message="I'll connect you with our pharmacy team right away.",
            transfer_to="main_line"
        )
    
    # handle based on intent
    if intent == Intent.RX_STATUS:
        return VoiceResponse(
            action="say",
            message="To check your prescription status, I'll need your name and date of birth. Or I can transfer you to a team member. Would you like me to transfer you?"
        )
    
    if intent == Intent.REFILL_REQUEST:
        return VoiceResponse(
            action="say",
            message="I can help with your refill. Please provide your name and the medication you need refilled. Or say 'transfer' to speak with someone directly."
        )
    
    if intent == Intent.COMPOUND_QUESTION:
        return VoiceResponse(
            action="say",
            message="We do offer custom compounded medications. Let me transfer you to a specialist who can answer your specific questions."
        )
    
    # low confidence or unknown - transfer
    if confidence < 0.6 or intent == Intent.UNKNOWN:
        log_action("call_transfer", session_id, f"low confidence: {confidence}")
        return VoiceResponse(
            action="transfer",
            message="Let me connect you with a team member who can better assist you.",
            transfer_to="main_line"
        )
    
    # default response
    return VoiceResponse(
        action="say",
        message="I'm not sure I understood. Would you like me to transfer you to speak with someone?"
    )


@router.get("/stats")
async def get_call_stats():
    """get call statistics - placeholder"""
    return {
        "today": {"total": 0, "automated": 0, "transferred": 0},
        "automation_rate": 0
    }
