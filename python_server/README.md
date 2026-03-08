# Adobe Experience Platform (AEP) Enterprise MCP Server

This repository contains a highly secure, Enterprise-grade **Model Context Protocol (MCP)** server for interacting with Adobe Experience Platform (AEP).

Unlike basic MCP proof-of-concepts, this server is designed for zero-data leakage, utilizing strict LLM payload pruning, field-level security blocklists, and an intelligent Retrieval-Augmented Generation (RAG) schema discovery layer.

## Architecture

This MCP Server bridges the gap between an Enterprise LLM (like Azure OpenAI or Claude) and your specific AEP Sandbox.

### Key Enterprise Features
1. **Intelligent Schema RAG:** AEP schemas are massive and highly customized. The LLM cannot guess your exact JSONPaths. The `discover_xdm_schema` tool queries a local Business Data Dictionary (`aep_data_dictionary.json`) to dynamically map business logic to raw XDM paths.
2. **Pluggable Vector DB Support:** The RAG layer is built on the `RagProvider` interface. The MVP uses an in-memory JSON dictionary, but enterprise developers can easily swap this out for an Azure AI Search or AWS OpenSearch vector connector.
3. **Hardware-Side Data Pruning:** The MCP server never returns raw 10,000-line AEP payloads to the LLM. It forces the LLM to explicitly request specific schema paths (e.g., `_custom.loyalty.tier`), then extracts ONLY those paths before responding.
4. **Field-Level Security:** Highly sensitive fields (like SSNs or physical addresses) are guarded by a Hard Enforcement Check defined in `security_config.json`. If an LLM hallucinates an attempt to access a blocked path, the server instantly drops the request.
5. **Immutable Audit Logging:** Every LLM data request is structured and securely audited in `logs/mcp_audit.log` for GDPR/CCPA compliance.

---

## 1. Setup & Installation

### Prerequisites
- Python 3.10+
- `uvicorn` installed globally (optional, for non-stdio hosting)
- Access to an Adobe Developer Console project with Server-to-Server OAuth credentials.

### Installation
1. Clone this repository.
2. Install the Python dependencies:
   ```bash
   cd python_server
   pip install -r requirements.txt
   ```

---

## 2. Configuration (Authentication & Security)

### A. Adobe I/O Credentials (The `.env` file)
You must configure the server to authenticate securely with your AEP Sandbox. 
1. In the `python_server` directory, create or edit the `.env` file.
2. Do **NOT** commit this file to GitHub!
3. Add your Adobe API credentials:
   ```env
   AEP_CLIENT_ID=your_client_id_here
   AEP_CLIENT_SECRET=your_client_secret_here
   AEP_ORG_ID=your_org_id_here
   AEP_SANDBOX_NAME=prod
   AEP_SCOPES=openid,AdobeID,read_organizations
   ```

### B. Field-Level Security (The `security_config.json` file)
InfoSec teams use this file to explicitly block the LLM from accessing dangerous paths, even if they exist in the sandbox.
1. Open `security_config.json`.
2. Add prefixes you wish to ban outright (e.g., `"person.ssn"`).

---

## 3. Configuring the Business Data Dictionary (RAG Layer)

The true power of this MCP Server is the **Business Data Dictionary (BDD)**. This is how the LLM understands your messy enterprise data.

1. Open `aep_data_dictionary.json`.
2. Map your custom AEP XDM paths to plain English descriptions.
   
```json
{
  "path": "_yourCompany.loyalty.points",
  "type": "integer",
  "business_description": "The active loyalty points balance for the customer. DO NOT use person.loyaltytier.",
  "keywords": ["loyalty", "points", "rewards"]
}
```
When a user asks: *"What are John's rewards?"*, the LLM will query the RAG tool, find this description, and instantly know to query `_yourCompany.loyalty.points`.

*Note for Architects:* To replace this JSON file with a live Vector DB connection, build a new class implementing the `RagProvider` abstract base class (located in `src/rag/base_provider.py`) and plug it into `server.py`.

---

## 4. Connecting to Claude Desktop (Local Demo)

To run this Enterprise Server locally via `stdio` using Claude Desktop:

1. Ensure you have Claude Desktop installed.
2. Locate the Claude Desktop configuration file:
   - **MacOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
3. Edit the file to point to your `python_server` directory. Be sure to use **absolute paths**:

```json
{
  "mcpServers": {
    "aep-enterprise-server": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\Absolute\\Path\\To\\AEP_MCP\\python_server"
    }
  }
}
```

4. **Restart Claude Desktop.**
5. Look for the small "plug" (MCP) icon in the chat interface. If it is active, the server is running natively in the background!
6. Try asking Claude: *"Discover the schema for loyalty data, then get the customer profile for jane.doe@example.com."*

---

## 5. Connecting to an Enterprise LLM (Production)
For live production environments (e.g., Azure OpenAI in a VPC), you cannot use Claude Desktop and `stdio`. 
Instead, you must deploy this Python codebase as a Web Server (FastAPI):
```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000
```
Then, point your internal Enterprise Chat UI to connect via Server-Sent Events (SSE).
