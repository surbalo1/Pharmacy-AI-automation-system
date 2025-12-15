"""
brain/audit.py - logging and audit trails for compliance
keeps track of what the system does for HIPAA
"""

import json
import os
from datetime import datetime
from typing import Optional

from phi.models import AuditEntry


# store logs here - in prod use a proper db
LOG_DIR = "logs"
AUDIT_FILE = "audit_log.jsonl"


def ensure_log_dir():
    """make sure log directory exists"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def log_action(action: str, session_id: str, details: str = None, 
               user_id: str = None) -> AuditEntry:
    """
    log an action for audit trail
    
    args:
        action: what happened (deidentify, reidentify, ai_call, etc)
        session_id: unique session identifier
        details: optional extra info
        user_id: optional user/staff id
    """
    ensure_log_dir()
    
    entry = AuditEntry(
        timestamp=datetime.now(),
        action=action,
        session_id=session_id,
        user_id=user_id,
        details=details
    )
    
    # append to jsonl file
    log_path = os.path.join(LOG_DIR, AUDIT_FILE)
    with open(log_path, "a") as f:
        f.write(entry.model_dump_json() + "\n")
    
    return entry


def get_session_logs(session_id: str) -> list[AuditEntry]:
    """get all logs for a session"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, AUDIT_FILE)
    
    if not os.path.exists(log_path):
        return []
    
    entries = []
    with open(log_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("session_id") == session_id:
                    entries.append(AuditEntry(**data))
            except:
                continue
    
    return entries


def get_logs_by_date(date: datetime) -> list[AuditEntry]:
    """get all logs for a specific date"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, AUDIT_FILE)
    
    if not os.path.exists(log_path):
        return []
    
    target_date = date.date()
    entries = []
    
    with open(log_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data["timestamp"])
                if ts.date() == target_date:
                    entries.append(AuditEntry(**data))
            except:
                continue
    
    return entries


def log_phi_access(session_id: str, phi_type: str, action: str):
    """special logging for PHI access"""
    log_action(
        action=f"phi_{action}",
        session_id=session_id,
        details=f"phi_type={phi_type}"
    )
