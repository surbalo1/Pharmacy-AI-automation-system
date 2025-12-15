"""
handlers/analytics.py - analytics endpoints
provides data for the dashboard
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Dict, List

from integrations.airtable import airtable
from brain.audit import get_logs_by_date


router = APIRouter()


@router.get("/daily")
async def get_daily_stats():
    """
    get today's key metrics
    """
    today = datetime.now()
    
    # count today's audit logs by type
    logs = get_logs_by_date(today)
    
    chat_count = sum(1 for l in logs if l.action.startswith("chat"))
    sms_count = sum(1 for l in logs if l.action.startswith("sms"))
    call_count = sum(1 for l in logs if l.action.startswith("call"))
    email_count = sum(1 for l in logs if l.action.startswith("email"))
    
    return {
        "date": today.strftime("%Y-%m-%d"),
        "chats": chat_count,
        "sms": sms_count,
        "calls": call_count,
        "emails": email_count,
        "total_interactions": chat_count + sms_count + call_count + email_count
    }


@router.get("/prescriptions")
async def get_prescription_stats():
    """
    get prescription metrics
    in prod this would query pionerrx or airtable
    """
    # mock data for now
    return {
        "today": 47,
        "week": [42, 38, 45, 51, 47, 28, 12],
        "by_category": {
            "hormone": 35,
            "pain": 25,
            "dermal": 22,
            "other": 18
        }
    }


@router.get("/refills")
async def get_refill_stats():
    """
    refill reminder performance
    """
    today = datetime.now()
    logs = get_logs_by_date(today)
    
    reminders_sent = sum(1 for l in logs if "refill_reminder" in l.action)
    confirmations = sum(1 for l in logs if l.action == "refill_confirmed")
    
    return {
        "sent_today": reminders_sent,
        "confirmed": confirmations,
        "conversion_rate": round(confirmations / max(reminders_sent, 1) * 100, 1)
    }


@router.get("/open-orders")
async def get_open_orders():
    """
    get orders that are still processing
    """
    # in prod query pionerrx or airtable
    # mock data
    orders = [
        {"rx": "RX123456", "patient": "J. Smith", "med": "Testosterone Cream", 
         "status": "processing", "days_open": 2},
        {"rx": "RX123457", "patient": "M. Johnson", "med": "Progesterone Caps", 
         "status": "ready", "days_open": 1},
        {"rx": "RX123458", "patient": "R. Williams", "med": "Pain Compound", 
         "status": "pending", "days_open": 4},
    ]
    
    return {
        "orders": orders,
        "total": len(orders),
        "oldest_days": max(o["days_open"] for o in orders) if orders else 0
    }


@router.get("/automation-rate")
async def get_automation_rate():
    """
    what % of interactions are fully automated
    """
    today = datetime.now()
    logs = get_logs_by_date(today)
    
    total = len(logs)
    escalated = sum(1 for l in logs if "escalat" in l.action or "transfer" in l.action)
    
    if total == 0:
        return {"rate": 0, "total": 0, "automated": 0}
    
    automated = total - escalated
    rate = round(automated / total * 100, 1)
    
    return {
        "rate": rate,
        "total": total,
        "automated": automated,
        "escalated": escalated
    }
