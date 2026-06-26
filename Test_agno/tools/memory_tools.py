import sys
import os
from pathlib import Path

# Add the parent folder to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.titan_model import TitanExternalMemory
except ImportError:
    # Fallback to a mock if the file is not available
    class TitanExternalMemory:
        def __init__(self, **kwargs): pass
        def store(self, text: str): return ("Mock stored", None, [])
        def retrieve(self, query: str, k=5, min_score=0.1): return []

def store_fact(fact: str) -> str:
    """Stores important information in the Titan long-term memory.
    
    Args:
        fact (str): The information or fact to memorize (e.g., 'The API port is 8080').
    """
    try:
        memory_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "titan_db"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_path = memory_dir / "memory.pt"
        titan = TitanExternalMemory(memory_path=memory_path)
        titan.load()
        result_msg, _, _ = titan.store(fact)
        titan.save()
        return f"Success: {result_msg}"
    except Exception as e:
        return f"Error saving to Titan: {e}"

def retrieve_fact(query: str) -> str:
    """Retrieves information from the Titan long-term memory.
    
    Args:
        query (str): The question or keyword to search for.
    """
    try:
        memory_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "titan_db"
        memory_path = memory_dir / "memory.pt"
        titan = TitanExternalMemory(memory_path=memory_path)
        titan.load()
        results = titan.retrieve(query, k=5, min_score=0.1)
        if not results:
            return "No information found in memory."
        
        # Format the results
        output = "Results found in Titan memory:\n"
        for score, breakdown, item in results:
            output += f"- {item.text} (relevance: {score:.2f})\n"
        return output
    except Exception as e:
        return f"Error reading from Titan: {e}"
