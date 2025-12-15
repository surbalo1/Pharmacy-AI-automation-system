"""
automations/refill_reminders.py - automated refill sequences
sends sms reminders for 30-day compound meds
"""

from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass

from integrations.ghl import ghl
from integrations.airtable import airtable
from brain.audit import log_action


@dataclass
class RefillReminder:
    patient_id: str
    contact_id: str
    medication: str
    days_since_fill: int
    reminder_type: str  # day21, day26, day35


# reminder schedule - days after fill
REMINDER_SCHEDULE = [
    (21, "day21", "Hey! Just a heads up - your {med} should be running low soon. Reply YES to refill or call us."),
    (26, "day26", "Reminder: Your {med} refill is due. Reply YES and we'll get it started for you!"),
    (35, "day35", "We noticed you haven't refilled your {med}. Everything okay? Reply or give us a call."),
]


def get_patients_needing_reminders() -> List[RefillReminder]:
    """
    find patients who need refill reminders
    looks for 30-day compound prescriptions
    """
    reminders = []
    
    # get prescriptions that are 30-day compounds
    # filter for fill dates in our reminder windows
    today = datetime.now()
    
    for days, reminder_type, _ in REMINDER_SCHEDULE:
        target_date = today - timedelta(days=days)
        # format for airtable filter
        date_str = target_date.strftime("%Y-%m-%d")
        
        formula = f"AND({{DaysSupply}} = 30, {{FillDate}} = '{date_str}', {{IsCompound}} = TRUE())"
        prescriptions = airtable.get_records("Prescriptions", formula)
        
        for rx in prescriptions:
            fields = rx.get("fields", {})
            patient_id = fields.get("PatientId")
            
            if not patient_id:
                continue
            
            # get patient contact id
            patient = airtable.get_patient(patient_id)
            contact_id = patient.get("fields", {}).get("GHLContactId")
            
            if contact_id:
                reminders.append(RefillReminder(
                    patient_id=patient_id,
                    contact_id=contact_id,
                    medication=fields.get("MedicationName", "medication"),
                    days_since_fill=days,
                    reminder_type=reminder_type
                ))
    
    return reminders


def send_reminder(reminder: RefillReminder) -> bool:
    """send a single refill reminder"""
    # get the message template
    template = None
    for days, rtype, msg in REMINDER_SCHEDULE:
        if rtype == reminder.reminder_type:
            template = msg
            break
    
    if not template:
        return False
    
    # personalize message
    message = template.format(med=reminder.medication)
    
    # send via ghl
    result = ghl.send_sms(reminder.contact_id, message)
    
    if "error" not in result:
        log_action(
            "refill_reminder_sent",
            reminder.patient_id,
            f"{reminder.reminder_type}: {reminder.medication}"
        )
        return True
    
    return False


def consolidate_reminders(reminders: List[RefillReminder]) -> Dict[str, List[RefillReminder]]:
    """
    group reminders by patient
    so we don't spam people with multiple meds
    """
    by_patient = {}
    for r in reminders:
        if r.patient_id not in by_patient:
            by_patient[r.patient_id] = []
        by_patient[r.patient_id].append(r)
    return by_patient


def send_consolidated_reminder(patient_id: str, reminders: List[RefillReminder]) -> bool:
    """send one message for multiple meds"""
    if not reminders:
        return False
    
    contact_id = reminders[0].contact_id
    meds = [r.medication for r in reminders]
    
    if len(meds) == 1:
        # single med - use normal flow
        return send_reminder(reminders[0])
    
    # multiple meds - consolidated message
    med_list = ", ".join(meds[:-1]) + f" and {meds[-1]}"
    message = f"Hey! Your {med_list} should be ready for refill. Reply YES to refill all, or call us to discuss."
    
    result = ghl.send_sms(contact_id, message)
    
    if "error" not in result:
        log_action(
            "refill_reminder_consolidated",
            patient_id,
            f"{len(meds)} medications"
        )
        return True
    
    return False


def run_daily_reminders():
    """
    main function to run daily
    finds and sends all due reminders
    """
    reminders = get_patients_needing_reminders()
    
    if not reminders:
        return {"sent": 0, "patients": 0}
    
    # consolidate by patient
    by_patient = consolidate_reminders(reminders)
    
    sent_count = 0
    for patient_id, patient_reminders in by_patient.items():
        if send_consolidated_reminder(patient_id, patient_reminders):
            sent_count += 1
    
    return {
        "sent": sent_count,
        "patients": len(by_patient),
        "total_meds": len(reminders)
    }


def send_quarterly_checkin():
    """
    friendly quarterly check-in for compound patients
    runs every 3 months
    """
    # get patients who haven't had activity in 60+ days
    formula = "AND({IsCompoundPatient} = TRUE(), {DaysSinceLastOrder} > 60)"
    patients = airtable.get_records("Patients", formula, max_records=50)
    
    sent = 0
    for patient in patients:
        contact_id = patient.get("fields", {}).get("GHLContactId")
        name = patient.get("fields", {}).get("FirstName", "")
        
        if contact_id:
            message = f"Hi{' ' + name if name else ''}! Just checking in from your pharmacy. Hope you're doing well! Let us know if you need anything."
            result = ghl.send_sms(contact_id, message)
            
            if "error" not in result:
                sent += 1
    
    return {"checkins_sent": sent}
