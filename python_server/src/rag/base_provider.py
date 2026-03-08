from abc import ABC, abstractmethod
from typing import List, Dict, Any

class RagProvider(ABC):
    """
    Abstract Base Class for the AEP Schema RAG Provider.
    Enterprises can implement this interface to connect their own Vector Databases
    or robust retrieval systems instead of using the local JSON data dictionary.
    """

    @abstractmethod
    def search_schema(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches the enterprise data dictionary for relevant XDM paths.
        
        Args:
            query (str): The search term provided by the LLM (e.g., 'loyalty points').
            
        Returns:
            List[Dict]: A list of relevant XDM schema objects, typically including:
                - 'path': The fully qualified XDM JSON path (e.g., 'person.name.firstName')
                - 'description': Plain English business definition of the field.
                - 'type': The data type (string, integer, etc.)
        """
        pass
