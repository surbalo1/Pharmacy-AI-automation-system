"""
handlers/sms.py - sms webhook handler
processes incoming sms from ghl
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import uuid

from brain.reasoning import ReasoningEngine
from brain.router import detect_intent, Intent
from brain.audit import log_action
from integrations.ghl import ghl
from integrations.airtable import airtable


router = APIRouter()


class SMSWebhook(BaseModel):
    contactId: str
    message: str
    phone: Optional[str] = None
    conversationId: Optional[str] = None


# auto-replies for specific keywords
AUTO_REPLIES = {
    "yes": None,  # handled specially for refill confirmation
    "stop": "You've been unsubscribed. Reply START to resubscribe.",
    "help": "Reply with your question or call us at 555-123-4567.",
}


@router.post("/webhook")
async def handle_sms_webhook(webhook: SMSWebhook):
    """
    handle incoming sms from ghl webhook
    """
    session_id = webhook.conversationId or str(uuid.uuid4())
    
    log_action("sms_received", session_id, f"contact={webhook.contactId}")
    
    msg_lower = webhook.message.strip().lower()
    
    # check for stop/help keywords
    if msg_lower in AUTO_REPLIES:
        reply = AUTO_REPLIES[msg_lower]
        if reply:
            ghl.send_sms(webhook.contactId, reply)
            return {"status": "auto_reply", "message": reply}
    
    # check for "yes" - refill confirmation
    if msg_lower == "yes":
        return await handle_refill_confirmation(webhook, session_id)
    
    # detect intent
    intent, confidence = detect_intent(webhook.message)
    
    # get patient info
    patient_data = None
    if webhook.phone:
        patient = airtable.find_patient_by_phone(webhook.phone)
        if patient:
            patient_data = {
                "name": patient.get("fields", {}).get("Name"),
                "phone": webhook.phone
            }
    
    # handle based on intent
    if intent == Intent.RX_STATUS:
        response = await handle_rx_status(webhook, patient_data)
    elif intent == Intent.REFILL_REQUEST:
        response = await handle_refill_request(webhook, patient_data)
    elif confidence < 0.5:
        # low confidence - create task for staff
        ghl.create_task(
            webhook.contactId,
            f"SMS needs review: {webhook.message[:50]}..."
        )
        response = "Thanks for your message! Someone from our team will get back to you shortly."
    else:
        # use AI
        engine = ReasoningEngine("chat")
        result = await engine.process(
            webhook.message,
            patient_data=patient_data,
            session_id=session_id
        )
        response = result["response"]
    
    # send response
    ghl.send_sms(webhook.contactId, response)
    log_action("sms_sent", session_id, response[:100])
    
    return {"status": "ok", "response": response}


async def handle_rx_status(webhook: SMSWebhook, patient_data: dict) -> str:
    """handle prescription status inquiry"""
    if not patient_data:
        return "I couldn't find your account. Please call us at 555-123-4567 for status updates."
    
    # get prescriptions from airtable
    patient = airtable.find_patient_by_phone(patient_data.get("phone", ""))
    if not patient:
        return "I couldn't find your prescriptions. Please call us for help."
    
    prescriptions = airtable.get_prescriptions(patient.get("id", ""))
    
    if not prescriptions:
        return "I don't see any active prescriptions. Want me to have someone call you?"
    
    # get most recent
    latest = prescriptions[0].get("fields", {})
    status = latest.get("Status", "processing")
    
    return f"Your prescription is currently: {status}. Call us if you have questions!"


async def handle_refill_request(webhook: SMSWebhook, patient_data: dict) -> str:
    """handle refill request"""
    if not patient_data:
        return "To request a refill, please call us at 555-123-4567 or visit our website."
    
    # create task for pharmacy staff
    ghl.create_task(
        webhook.contactId,
        f"Refill request from {patient_data.get('name', 'patient')}"
    )
    
    return "Got it! We'll process your refill request and text you when it's ready. Usually 24-48 hours."


async def handle_refill_confirmation(webhook: SMSWebhook, session_id: str) -> dict:
    """handle YES reply for refill confirmation"""
    # add note to contact
    ghl.add_note(
        webhook.contactId,
        "Patient confirmed refill via SMS"
    )
    
    # create task
    ghl.create_task(
        webhook.contactId,
        "Confirmed refill - please process"
    )
    
    response = "Perfect! Your refill has been confirmed. We'll text you when it's ready for pickup."
    ghl.send_sms(webhook.contactId, response)
    
    log_action("refill_confirmed", session_id, f"contact={webhook.contactId}")
    
    return {"status": "refill_confirmed", "response": response}
