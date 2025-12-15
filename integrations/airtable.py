"""
integrations/airtable.py - airtable data layer
crud operations for our data warehouse
"""

import requests
from typing import Dict, Any, List, Optional

from config import settings


class AirtableClient:
    """wrapper for airtable api"""
    
    def __init__(self):
        self.base_url = f"{settings.AIRTABLE_BASE_URL}/{settings.AIRTABLE_BASE_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, table: str, 
                 data: Dict = None, record_id: str = None) -> Dict:
        """make api request"""
        # mock mode
        if settings.MOCK_MODE:
            return {
                "id": "rec_mock_123",
                "fields": {"Name": "Test Patient", "Status": "Active"},
                "records": []
            }
        
        url = f"{self.base_url}/{table}"
        if record_id:
            url += f"/{record_id}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=self.headers, params=data)
            elif method == "POST":
                resp = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                resp = requests.patch(url, headers=self.headers, json=data)
            elif method == "DELETE":
                resp = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"bad method: {method}")
            
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    # generic crud
    def get_records(self, table: str, filter_formula: str = None,
                    max_records: int = 100) -> List[Dict]:
        """get records from table"""
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        result = self._request("GET", table, params)
        return result.get("records", [])
    
    def get_record(self, table: str, record_id: str) -> Dict:
        """get single record"""
        return self._request("GET", table, record_id=record_id)
    
    def create_record(self, table: str, fields: Dict) -> Dict:
        """create new record"""
        return self._request("POST", table, {"fields": fields})
    
    def update_record(self, table: str, record_id: str, 
                      fields: Dict) -> Dict:
        """update record"""
        return self._request("PATCH", table, {"fields": fields}, record_id)
    
    def delete_record(self, table: str, record_id: str) -> Dict:
        """delete record"""
        return self._request("DELETE", table, record_id=record_id)
    
    # convenience methods for common tables
    def get_patient(self, patient_id: str) -> Dict:
        """get patient by id"""
        return self.get_record("Patients", patient_id)
    
    def find_patient_by_phone(self, phone: str) -> Optional[Dict]:
        """find patient by phone number"""
        # clean phone format
        clean_phone = ''.join(filter(str.isdigit, phone))
        formula = f"FIND('{clean_phone}', {{Phone}})"
        records = self.get_records("Patients", formula, max_records=1)
        return records[0] if records else None
    
    def get_prescriptions(self, patient_id: str) -> List[Dict]:
        """get prescriptions for patient"""
        formula = f"{{PatientId}} = '{patient_id}'"
        return self.get_records("Prescriptions", formula)
    
    def log_interaction(self, data: Dict) -> Dict:
        """log a patient interaction"""
        return self.create_record("Interactions", data)


# singleton
airtable = AirtableClient()
