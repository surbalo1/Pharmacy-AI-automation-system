"""
automations/intake.py - new patient intake workflow
collects info from new compound inquiries
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
import uuid

from integrations.ghl import ghl
from integrations.airtable import airtable
from brain.audit import log_action


class IntakeStep(Enum):
    STARTED = "started"
    NAME_COLLECTED = "name_collected"
    DOB_COLLECTED = "dob_collected"
    DOCTOR_ASKED = "doctor_asked"
    DOCTOR_COLLECTED = "doctor_collected"
    COMPLETED = "completed"


@dataclass
class IntakeSession:
    session_id: str
    contact_id: str
    current_step: IntakeStep
    data: Dict


# store active intake sessions - in prod use redis or db
active_sessions: Dict[str, IntakeSession] = {}


# prompts for each step
STEP_PROMPTS = {
    IntakeStep.STARTED: "Great! Let's get you set up. First, what's your full name?",
    IntakeStep.NAME_COLLECTED: "Thanks {name}! And what's your date of birth?",
    IntakeStep.DOB_COLLECTED: "Perfect. Do you have a prescribing doctor for your compound medication?",
    IntakeStep.DOCTOR_ASKED: "What's your doctor's name and clinic? (e.g., Dr. Smith at City Clinic)",
    IntakeStep.DOCTOR_COLLECTED: "Awesome, we have everything we need! Our team will reach out shortly to complete your intake. Thanks {name}!",
}


def start_intake(contact_id: str, initial_message: str) -> str:
    """
    start new patient intake flow
    returns first prompt
    """
    session_id = str(uuid.uuid4())
    
    session = IntakeSession(
        session_id=session_id,
        contact_id=contact_id,
        current_step=IntakeStep.STARTED,
        data={"initial_query": initial_message}
    )
    
    active_sessions[contact_id] = session
    
    log_action("intake_started", session_id, f"contact={contact_id}")
    
    return STEP_PROMPTS[IntakeStep.STARTED]


def process_intake_response(contact_id: str, response: str) -> str:
    """
    process response in intake flow
    advances to next step
    """
    session = active_sessions.get(contact_id)
    
    if not session:
        # no active session - maybe they're new
        return start_intake(contact_id, response)
    
    current = session.current_step
    
    # process based on current step
    if current == IntakeStep.STARTED:
        # collecting name
        session.data["name"] = response.strip()
        session.current_step = IntakeStep.NAME_COLLECTED
        return STEP_PROMPTS[IntakeStep.NAME_COLLECTED].format(name=session.data["name"].split()[0])
    
    elif current == IntakeStep.NAME_COLLECTED:
        # collecting dob
        session.data["dob"] = response.strip()
        session.current_step = IntakeStep.DOB_COLLECTED
        return STEP_PROMPTS[IntakeStep.DOB_COLLECTED]
    
    elif current == IntakeStep.DOB_COLLECTED:
        # asking about doctor
        resp_lower = response.lower()
        if "yes" in resp_lower or "yeah" in resp_lower:
            session.current_step = IntakeStep.DOCTOR_ASKED
            return STEP_PROMPTS[IntakeStep.DOCTOR_ASKED]
        elif "no" in resp_lower:
            session.data["doctor"] = "Need referral"
            return complete_intake(session)
        else:
            # assume it's doctor info
            session.data["doctor"] = response.strip()
            return complete_intake(session)
    
    elif current == IntakeStep.DOCTOR_ASKED:
        # collecting doctor info
        session.data["doctor"] = response.strip()
        return complete_intake(session)
    
    # shouldn't get here
    return "Something went wrong. Please call us at 555-123-4567."


def complete_intake(session: IntakeSession) -> str:
    """
    finish intake and create records
    """
    session.current_step = IntakeStep.COMPLETED
    
    # create patient record in airtable
    patient = airtable.create_record("Patients", {
        "Name": session.data.get("name", ""),
        "DOB": session.data.get("dob", ""),
        "ProviderName": session.data.get("doctor", ""),
        "Source": "SMS Intake",
        "GHLContactId": session.contact_id,
        "Status": "New"
    })
    
    # create task in ghl for follow up
    ghl.create_task(
        session.contact_id,
        f"New patient intake: {session.data.get('name', 'Unknown')} - needs follow up"
    )
    
    # add note with collected info
    note = f"Intake completed:\nName: {session.data.get('name')}\nDOB: {session.data.get('dob')}\nDoctor: {session.data.get('doctor')}"
    ghl.add_note(session.contact_id, note)
    
    log_action("intake_completed", session.session_id, f"patient created")
    
    # clean up session
    del active_sessions[session.contact_id]
    
    first_name = session.data.get("name", "").split()[0] if session.data.get("name") else ""
    return STEP_PROMPTS[IntakeStep.DOCTOR_COLLECTED].format(name=first_name)


def is_intake_active(contact_id: str) -> bool:
    """check if contact has active intake session"""
    return contact_id in active_sessions


def cancel_intake(contact_id: str):
    """cancel an active intake"""
    if contact_id in active_sessions:
        session = active_sessions[contact_id]
        log_action("intake_cancelled", session.session_id)
        del active_sessions[contact_id]


def lookup_provider(doctor_name: str, clinic: str = None) -> Optional[Dict]:
    """
    look up provider in database
    returns provider info if found
    """
    # search airtable for provider
    formula = f"FIND('{doctor_name}', {{Name}})"
    providers = airtable.get_records("Providers", formula, max_records=5)
    
    if not providers:
        return None
    
    # if clinic specified, try to match
    if clinic:
        for p in providers:
            if clinic.lower() in p.get("fields", {}).get("Clinic", "").lower():
                return p.get("fields")
    
    # return first match
    return providers[0].get("fields")


def verify_provider(doctor_name: str) -> Dict:
    """
    verify provider and get their info
    returns verification status and details
    """
    provider = lookup_provider(doctor_name)
    
    if provider:
        return {
            "verified": True,
            "name": provider.get("Name"),
            "clinic": provider.get("Clinic"),
            "npi": provider.get("NPI"),
            "fax": provider.get("Fax")
        }
    
    return {
        "verified": False,
        "message": "Provider not found in system - will need verification"
    }
