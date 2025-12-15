"""
config.py - app settings
loads from .env file
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # openai stuff
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # ghl config
    GHL_API_KEY = os.getenv("GHL_API_KEY", "")
    GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "")
    GHL_BASE_URL = "https://rest.gohighlevel.com/v1"
    
    # airtable
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
    AIRTABLE_BASE_URL = "https://api.airtable.com/v0"
    
    # vapi voice
    VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
    
    # app config
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # mock mode - for testing without real APIs
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
    
    # phi settings - how long to keep re-id mappings (hours)
    PHI_MAPPING_TTL = 24


settings = Settings()
