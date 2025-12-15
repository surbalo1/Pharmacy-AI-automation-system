"""
handlers/email.py - email triage system
classifies emails and drafts responses
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import uuid
import re

from brain.reasoning import ReasoningEngine
from brain.audit import log_action
from phi.deidentify import deidentify
from integrations.ghl import ghl


router = APIRouter()


class EmailPayload(BaseModel):
    from_email: str
    subject: str
    body: str
    thread_id: Optional[str] = None


class TriageResult(BaseModel):
    intent: str
    confidence: float
    priority: str
    draft_response: Optional[str] = None
    contact_id: Optional[str] = None
    tasks_created: List[str] = []


# email intent categories
EMAIL_INTENTS = [
    "compound_question",
    "refill_request", 
    "rx_status",
    "provider_update",
    "new_patient",
    "billing",
    "general",
    "spam"
]


def extract_email_metadata(body: str) -> dict:
    """pull out useful info from email body"""
    metadata = {}
    
    # try to find phone numbers
    phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', body)
    if phones:
        metadata["phone"] = phones[0]
    
    # try to find rx numbers
    rx_nums = re.findall(r'\bRX\d{6,}\b', body, re.IGNORECASE)
    if rx_nums:
        metadata["rx_number"] = rx_nums[0]
    
    return metadata


@router.post("/triage", response_model=TriageResult)
async def triage_email(email: EmailPayload):
    """
    triage incoming email
    classifies and drafts response
    """
    session_id = email.thread_id or str(uuid.uuid4())
    
    log_action("email_received", session_id, f"from={email.from_email}")
    
    # deidentify the email content
    safe_email = deidentify(f"Subject: {email.subject}\n\n{email.body}")
    
    # classify with AI
    engine = ReasoningEngine("email")
    
    classify_prompt = f"""Classify this pharmacy email and determine priority.

Email content:
{safe_email.text}

Classify as one of: {', '.join(EMAIL_INTENTS)}

Also determine priority: high, medium, low

Return JSON format:
{{"intent": "category", "confidence": 0.0-1.0, "priority": "high/medium/low", "summary": "brief description"}}"""
    
    result = await engine.classify(classify_prompt)
    
    intent = result.get("intent", "general")
    confidence = result.get("confidence", 0.5)
    priority = result.get("priority", "medium")
    
    # high priority intents
    if intent in ["new_patient", "provider_update", "rx_status"]:
        priority = "high"
    
    # look up contact
    metadata = extract_email_metadata(email.body)
    contact_id = None
    
    contacts = ghl.search_contacts(email.from_email)
    if contacts:
        contact_id = contacts[0].get("id")
    
    # draft response if confidence is high enough
    draft = None
    if confidence > 0.7 and intent != "spam":
        draft = await generate_draft_response(email, intent, safe_email.text)
    
    # create tasks based on intent
    tasks = []
    if contact_id:
        if intent in ["refill_request", "rx_status"]:
            task = ghl.create_task(contact_id, f"Email: {intent} - {email.subject[:30]}")
            tasks.append(task.get("id", ""))
        
        # add note with email summary
        ghl.add_note(contact_id, f"Email received: {result.get('summary', email.subject)[:100]}")
    
    log_action("email_triaged", session_id, f"intent={intent}, priority={priority}")
    
    return TriageResult(
        intent=intent,
        confidence=confidence,
        priority=priority,
        draft_response=draft,
        contact_id=contact_id,
        tasks_created=tasks
    )


async def generate_draft_response(email: EmailPayload, intent: str, 
                                   safe_body: str) -> str:
    """generate draft email response"""
    
    # templates for common responses
    templates = {
        "billing": "Thank you for reaching out about billing. Let me look into this for you...",
        "refill_request": "Thank you for your refill request. We've received it and...",
        "compound_question": "Thank you for your interest in compound medications. We'd be happy to help...",
        "general": "Thank you for contacting us. We've received your message and...",
    }
    
    base = templates.get(intent, templates["general"])
    
    # use AI to complete the draft
    engine = ReasoningEngine("email")
    
    prompt = f"""Complete this email response draft. Keep it professional and helpful.
Do not auto-approve anything medical. End with asking them to call if they have questions.

Original email (de-identified):
{safe_body[:500]}

Start of our response:
{base}

Complete the response:"""
    
    result = await engine.process(prompt)
    
    # combine template start with AI completion
    full_draft = base + " " + result["response"]
    
    return full_draft


@router.get("/pending")
async def get_pending_emails():
    """get emails awaiting review - placeholder"""
    return {"pending": [], "count": 0}
