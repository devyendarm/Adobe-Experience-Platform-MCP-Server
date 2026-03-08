import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from .base_provider import RagProvider

# Set up logging for the MCP server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aep-mcp-rag")

class JsonRagProvider(RagProvider):
    """
    Default MVP implementation for the AEP Schema RAG.
    Reads business context and schema paths from a local JSON file.
    """

    def __init__(self, file_path: str = "aep_data_dictionary.json"):
        self.file_path = Path(file_path)
        self.dictionary: List[Dict[str, Any]] = []
        self._load_dictionary()

    def _load_dictionary(self):
        """Loads the JSON file into memory on startup."""
        if not self.file_path.exists():
            logger.warning(f"Data Dictionary file not found at {self.file_path}. RAG searches will return empty.")
            return

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                self.dictionary = data.get("schemas", [])
                logger.info(f"Loaded {len(self.dictionary)} schema definitions from {self.file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {self.file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading {self.file_path}: {e}")

    def search_schema(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches the loaded dictionary for the query string.
        Performs a basic substring match against the schema path, description, and keywords.
        """
        if not query:
            return []

        query = query.lower()
        results = []

        for schema_item in self.dictionary:
            path = schema_item.get("path", "").lower()
            desc = schema_item.get("business_description", "").lower()
            keywords = [k.lower() for k in schema_item.get("keywords", [])]

            if query in path or query in desc or any(query in k for k in keywords):
                results.append(schema_item)

        logger.info(f"RAG Search for '{query}' returned {len(results)} matches.")
        return results
