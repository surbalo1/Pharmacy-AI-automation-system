"""
phi/models.py - data models for PHI handling
"""

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class PatientData(BaseModel):
    """raw patient info - never send this to AI"""
    name: Optional[str] = None
    dob: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    ssn_last4: Optional[str] = None
    rx_number: Optional[str] = None


class DeidentifiedData(BaseModel):
    """safe to send to AI"""
    text: str
    token_map: Dict[str, str]  # token -> original value
    created_at: datetime = datetime.now()


class AuditEntry(BaseModel):
    """log entry for compliance"""
    timestamp: datetime
    action: str  # deidentify, reidentify, ai_call
    user_id: Optional[str] = None
    session_id: str
    details: Optional[str] = None
