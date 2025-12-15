"""
brain/reasoning.py - unified AI reasoning engine
wraps openai with de-identification
"""

from typing import Dict, Any, Optional
import json

from phi.deidentify import deidentify
from phi.reidentify import reidentify
from integrations.openai_client import get_completion
from .audit import log_action


# system prompts for different contexts
SYSTEM_PROMPTS = {
    "chat": """You are a helpful pharmacy assistant. You help patients with:
- Prescription status questions
- Refill requests
- General pharmacy questions
- Compound medication inquiries

Be friendly but professional. If you're unsure, say so.
Never make up information about medications or prescriptions.
If someone needs urgent medical help, tell them to call 911 or their doctor.""",
    
    "email": """You are an assistant helping triage pharmacy emails.
Classify the email intent and draft a helpful response.
Be professional and HIPAA-aware - don't include unnecessary details.""",
    
    "call": """You are a voice assistant for a pharmacy.
Keep responses brief and clear. Speak naturally.
Confirm important details by repeating them back.""",
}


class ReasoningEngine:
    """main AI reasoning wrapper"""
    
    def __init__(self, context: str = "chat"):
        self.context = context
        self.system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS["chat"])
    
    async def process(self, 
                      user_input: str, 
                      patient_data: Dict[str, str] = None,
                      session_id: str = None) -> Dict[str, Any]:
        """
        process user input through AI with phi safety
        
        args:
            user_input: what the user said/typed
            patient_data: known PHI to deidentify (name, phone, etc)
            session_id: for audit logging
        
        returns:
            dict with response and metadata
        """
        # step 1: deidentify
        safe_data = deidentify(user_input, patient_data)
        
        # log the action
        if session_id:
            log_action("ai_call", session_id, f"context={self.context}")
        
        # step 2: call AI with safe text
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": safe_data.text}
        ]
        
        ai_response = await get_completion(messages)
        
        # step 3: reidentify the response
        final_response = reidentify(ai_response, safe_data.token_map)
        
        return {
            "response": final_response,
            "deidentified_input": safe_data.text,
            "tokens_found": len(safe_data.token_map),
            "context": self.context
        }
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """
        classify text intent without generating a response
        useful for routing decisions
        """
        safe_data = deidentify(text)
        
        classify_prompt = f"""Classify this message intent. Return JSON only.
Categories: rx_status, refill, compound_question, new_patient, provider, general, urgent

Message: {safe_data.text}

Return format: {{"intent": "category", "confidence": 0.0-1.0, "summary": "brief description"}}"""
        
        messages = [
            {"role": "system", "content": "You are a classifier. Return valid JSON only."},
            {"role": "user", "content": classify_prompt}
        ]
        
        result = await get_completion(messages)
        
        # try to parse as json
        try:
            return json.loads(result)
        except:
            return {"intent": "unknown", "confidence": 0.3, "summary": result[:100]}


# convenience function
async def quick_response(user_input: str, context: str = "chat") -> str:
    """one-liner for simple responses"""
    engine = ReasoningEngine(context)
    result = await engine.process(user_input)
    return result["response"]
