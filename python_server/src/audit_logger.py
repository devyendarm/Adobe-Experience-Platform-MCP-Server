import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import uuid

class AuditLogger:
    """
    Enterprise Audit Logger for the MCP Server.
    Logs every LLM tool invocation, including the target identifiers and exact XDM paths accessed.
    Writes structured JSON logs to a secure file for compliance (GDPR/CCPA).
    """

    def __init__(self, log_path: str = "logs/mcp_audit.log"):
        self.log_path = Path(log_path)
        # Ensure the logs directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure a dedicated python logger for simultaneous console/file output if needed
        self.logger = logging.getLogger("mcp_auditor")
        self.logger.setLevel(logging.INFO)

    def log_tool_access(self, tool_name: str, target_identifier: str = None, requested_paths: list = None, status: str = "SUCCESS", error_message: str = None):
        """
        Records a structured audit event.
        """
        audit_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "status": status,
        }
        
        if target_identifier:
            audit_event["target_identifier"] = target_identifier
            
        if requested_paths:
            audit_event["requested_paths"] = requested_paths
            
        if error_message:
            audit_event["error"] = error_message

        # Append strictly formatted JSON line (JSONL format) to the audit log file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_event) + "\n")
        except Exception as e:
            # Fallback to standard logging if file write fails (e.g. permission issues)
            self.logger.error(f"FAILED TO WRITE AUDIT LOG: {str(e)} | Event: {json.dumps(audit_event)}")

        # Also output to the standard server log stream for debugging
        self.logger.info(f"AUDIT EVENT: {json.dumps(audit_event)}")
