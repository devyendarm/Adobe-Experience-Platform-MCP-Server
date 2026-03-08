import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .rag.json_provider import JsonRagProvider
from .audit_logger import AuditLogger
from .adobe_auth import AdobeAuthenticator

# Load environment variables (Reserved for Authentication Secrets: Client ID, Secret, etc.)
load_dotenv()

# Load Security Blocklist from dedicated config file
BLOCKED_XDM_PATHS = []
try:
    with open("security_config.json", "r") as f:
        security_config = json.load(f)
        BLOCKED_XDM_PATHS = security_config.get("blocked_xdm_prefixes", [])
except Exception as e:
    logger.error(f"Failed to load security_config.json. Defaulting to empty blocklist. Error: {e}")

# Set up logging for the MCP server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aep-mcp-server")

# Initialize Audit Logging
auditor = AuditLogger()

# Initialize Adobe Authenticator
adobe_auth = AdobeAuthenticator()

# Initialize the FastMCP server
mcp = FastMCP("Adobe Experience Platform (AEP) Enterprise Server")

# Initialize the Pluggable RAG Provider (Defaulting to JSON MVP)
# In production, an enterprise would swap this with: AzureSearchRagProvider()
rag_provider = JsonRagProvider(file_path="aep_data_dictionary.json")

@mcp.tool()
def discover_xdm_schema(search_term: str) -> str:
    """
    RAG-enabled tool. ALWAYS call this tool first before querying AEP if you are unsure of the exact XDM JSON path required.
    Queries the enterprise Business Data Dictionary (BDD) to discover custom XDM schema paths and their business contexts.
    
    Args:
        search_term: A keyword to search for in the enterprise schema (e.g., "loyalty", "churn", "email", "name").
        
    Returns:
        JSON string containing the relevant XDM paths and their business validation rules.
    """
    logger.info(f"LLM Tool Call: discover_xdm_schema(search_term='{search_term}')")
    
    try:
        results = rag_provider.search_schema(search_term)
        auditor.log_tool_access("discover_xdm_schema", requested_paths=[search_term], status="SUCCESS")
        
        if not results:
            return json.dumps({"message": f"No relevant schema paths found for '{search_term}'. Try a broader keyword."})
        return json.dumps({"schema_paths": results}, indent=2)
    except Exception as e:
        auditor.log_tool_access("discover_xdm_schema", requested_paths=[search_term], status="ERROR", error_message=str(e))
        logger.error(f"Error in discover_xdm_schema: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_customer_profile(email: str, requested_xdm_paths: List[str]) -> str:
    """
    Retrieves a customer profile from AEP via email namespace and PRUNES the massive payload down to ONLY the paths requested.
    
    Args:
        email: The customer's exact email address.
        requested_xdm_paths: An array of fully-qualified XDM paths you need (e.g., ["_customTenant.loyalty.tier", "person.name.firstName"]).
                             You must discover these paths using discover_xdm_schema BEFORE calling this tool.
    
    Returns:
        JSON string containing the pruned profile data.
    """
    logger.info(f"LLM Tool Call: get_customer_profile(email='{email}')")
    
    try:
        # ---------------------------------------------------------
        # 1. Hard Enforcement Security Check
        # Check requested paths against the externalized BLOCKED_XDM_PATHS
        # ---------------------------------------------------------
        for requested_path in requested_xdm_paths:
            for blocked_prefix in BLOCKED_XDM_PATHS:
                if requested_path.startswith(blocked_prefix):
                    auditor.log_tool_access(
                        "get_customer_profile", target_identifier=email, status="BLOCKED_VIOLATION", 
                        error_message=f"Attempted to access restricted path: {requested_path}")
                    return json.dumps({
                        "error": f"SEC-001: Access Denied. The path '{requested_path}' contains strictly prohibited PII and is blocked by enterprise policy."
                    })

        # ---------------------------------------------------------
        # 2. Authenticate & Query AEP API
        # ---------------------------------------------------------
        # Retrieve the Adobe OAuth headers dynamically
        # headers = adobe_auth.get_auth_headers()
        # aep_endpoint = f"https://platform.adobe.io/data/core/ups/access/entities?entityId={email}&entityIdNS=email"
        # response = requests.get(aep_endpoint, headers=headers)
        
        # Default mock payload for testing setup without live AEP connection
        mock_aep_payload = {
            "person": {
                "name": {"firstName": "Jane", "lastName": "Doe"},
                "loyaltytier": "Gold_Legacy"
            },
            "personalEmail": {"address": "jane.doe@example.com"},
            "_customTenant": {
                "loyalty": {"tier": "Platinum"},
                "churnProbabilityScore": 0.15
            }
        }
        
        # ---------------------------------------------------------
        # 3. Apply JSONPath Pruning
        # ---------------------------------------------------------
        pruned_result = {}
        
        def extract_path(payload_dict, path_str):
            keys = path_str.split('.')
            current = payload_dict
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        for path in requested_xdm_paths:
            value = extract_path(mock_aep_payload, path)
            if value is not None:
                pruned_result[path] = value
            else:
                pruned_result[path] = "Path not found in returned profile payload."
                
        # Audit log the successful access and the exact fields pruned
        auditor.log_tool_access("get_customer_profile", target_identifier=email, requested_paths=requested_xdm_paths, status="SUCCESS")
        
        return json.dumps({"pruned_profile": pruned_result}, indent=2)
        
    except Exception as e:
        auditor.log_tool_access("get_customer_profile", target_identifier=email, status="ERROR", error_message=str(e))
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Start the FastMCP server utilizing stdio transport
    logger.info("Starting AEP Enterprise MCP Server via stdio...")
    mcp.run()
