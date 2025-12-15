"""
integrations/ghl.py - gohighlevel api wrapper
contacts, sms, pipelines
"""

import requests
from typing import Dict, Any, Optional, List

from config import settings


class GHLClient:
    """wrapper for gohighlevel api"""
    
    def __init__(self):
        self.base_url = settings.GHL_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.GHL_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """make api request"""
        # mock mode
        if settings.MOCK_MODE:
            return {"id": "mock_123", "status": "ok", "message": "[MOCK] Request simulated"}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=self.headers, params=data)
            elif method == "POST":
                resp = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                resp = requests.put(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"unsupported method: {method}")
            
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    # contacts
    def get_contact(self, contact_id: str) -> Dict:
        """get contact by id"""
        return self._request("GET", f"/contacts/{contact_id}")
    
    def search_contacts(self, query: str) -> List[Dict]:
        """search contacts by email or phone"""
        result = self._request("GET", "/contacts/", {"query": query})
        return result.get("contacts", [])
    
    def create_contact(self, data: Dict) -> Dict:
        """create new contact"""
        data["locationId"] = settings.GHL_LOCATION_ID
        return self._request("POST", "/contacts/", data)
    
    def update_contact(self, contact_id: str, data: Dict) -> Dict:
        """update existing contact"""
        return self._request("PUT", f"/contacts/{contact_id}", data)
    
    # sms
    def send_sms(self, contact_id: str, message: str) -> Dict:
        """send sms to contact"""
        data = {
            "type": "SMS",
            "contactId": contact_id,
            "message": message
        }
        return self._request("POST", "/conversations/messages", data)
    
    # pipeline
    def move_to_stage(self, contact_id: str, pipeline_id: str, 
                      stage_id: str) -> Dict:
        """move contact to pipeline stage"""
        data = {
            "pipelineId": pipeline_id,
            "pipelineStageId": stage_id
        }
        return self._request("PUT", f"/contacts/{contact_id}", data)
    
    # tasks
    def create_task(self, contact_id: str, title: str, 
                    due_date: str = None) -> Dict:
        """create task for contact"""
        data = {
            "contactId": contact_id,
            "title": title,
            "dueDate": due_date
        }
        return self._request("POST", "/tasks/", data)
    
    # notes
    def add_note(self, contact_id: str, body: str) -> Dict:
        """add note to contact"""
        data = {
            "contactId": contact_id,
            "body": body
        }
        return self._request("POST", "/contacts/notes", data)


# singleton instance
ghl = GHLClient()
