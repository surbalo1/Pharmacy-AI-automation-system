"""
handlers/chat.py - website chat widget endpoints
handles patient questions from the website
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from brain.reasoning import ReasoningEngine
from brain.router import detect_intent, Intent
from brain.audit import log_action
from integrations.airtable import airtable


router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    patient_phone: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    needs_human: bool = False
    intent: Optional[str] = None


# quick replies for common questions
QUICK_REPLIES = {
    "hours": "We're open Monday-Friday 9am-6pm and Saturday 9am-1pm. Closed Sundays.",
    "location": "We're located at 123 Main Street. There's parking in the back.",
    "insurance": "We accept most major insurance plans. Please call for specifics on your plan.",
}


@router.post("/message", response_model=ChatResponse)
async def handle_chat_message(msg: ChatMessage):
    """
    handle incoming chat message
    returns ai response or routes to human
    """
    session_id = msg.session_id or str(uuid.uuid4())
    
    # log the incoming message
    log_action("chat_received", session_id, msg.message[:100])
    
    # check for quick reply matches first
    msg_lower = msg.message.lower()
    for keyword, reply in QUICK_REPLIES.items():
        if keyword in msg_lower:
            return ChatResponse(
                response=reply,
                session_id=session_id,
                needs_human=False,
                intent="quick_reply"
            )
    
    # detect intent
    intent, confidence = detect_intent(msg.message)
    
    # if we need to look up patient data
    patient_data = None
    if msg.patient_phone:
        patient = airtable.find_patient_by_phone(msg.patient_phone)
        if patient:
            patient_data = {
                "name": patient.get("fields", {}).get("Name"),
                "phone": msg.patient_phone
            }
    
    # low confidence = route to human
    if confidence < 0.5 or intent == Intent.HUMAN_NEEDED:
        log_action("chat_escalated", session_id, f"intent={intent.value}")
        return ChatResponse(
            response="Let me connect you with someone who can help better. One moment please!",
            session_id=session_id,
            needs_human=True,
            intent=intent.value
        )
    
    # use AI for response
    engine = ReasoningEngine("chat")
    result = await engine.process(
        msg.message,
        patient_data=patient_data,
        session_id=session_id
    )
    
    log_action("chat_responded", session_id, f"tokens={result['tokens_found']}")
    
    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        needs_human=False,
        intent=intent.value
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """get chat history for a session - for debugging"""
    from brain.audit import get_session_logs
    logs = get_session_logs(session_id)
    return {"session_id": session_id, "logs": [l.model_dump() for l in logs]}
