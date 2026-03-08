import os
import time
import requests
import logging
from dotenv import load_dotenv

# Set up dedicated logger for Authentication
logger = logging.getLogger("aep_auth")
logger.setLevel(logging.INFO)

load_dotenv()

class AdobeAuthenticator:
    """
    Handles Adobe I/O Server-to-Server OAuth (Client Credentials flow).
    Securely fetches and caches the JWT/Access Token required for hitting AEP Sandbox APIs.
    """
    
    def __init__(self):
        self.client_id = os.getenv("AEP_CLIENT_ID")
        self.client_secret = os.getenv("AEP_CLIENT_SECRET")
        self.org_id = os.getenv("AEP_ORG_ID")
        self.sandbox_name = os.getenv("AEP_SANDBOX_NAME", "prod")
        
        # Scopes must match what was selected in the Adobe Developer Console
        self.scopes = os.getenv("AEP_SCOPES", "openid,AdobeID,read_organizations")
        
        # Standard Adobe IMS endpoint for Server-to-Server OAuth
        self.ims_url = "https://ims-na1.adobelogin.com/ims/token/v3"
        
        self._access_token = None
        self._token_expires_at = 0

    def get_access_token(self) -> str:
        """Returns a valid access token, fetching a new one from Adobe if necessary."""
        if not self.client_id or not self.client_secret:
            raise ValueError("Adobe credentials (AEP_CLIENT_ID or AEP_CLIENT_SECRET) are missing from the .env file.")

        # Return cached token if it's still valid (with a 5-minute safety buffer)
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        logger.info("Cache expired. Fetching new Adobe I/O Server-to-Server Access Token...")
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": self.scopes
        }
        
        try:
            response = requests.post(self.ims_url, data=payload)
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data.get("access_token")
            
            # The token usually expires in 86400 seconds (24 hours). We buffer by 300 seconds (5 minutes).
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in - 300
            
            logger.info("Successfully retrieved and cached new Adobe Access Token.")
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Adobe token: {e}")
            if e.response is not None:
                logger.error(f"Adobe IMS Error Response: {e.response.text}")
            raise

    def get_auth_headers(self) -> dict:
        """Returns the fully constructed HTTP headers required to make any AEP API call."""
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self.client_id,
            "x-gw-ims-org-id": self.org_id,
            "x-sandbox-name": self.sandbox_name,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
