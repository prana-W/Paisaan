import logging
from typing import List, Dict, Any
from duckduckgo_search import DDGS
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def search_market_news(query: str) -> List[Dict[str, str]]:
    """
    Search for recent financial market news based on a query.
    Uses DuckDuckGo news search.
    
    Returns a list of news items (dictionaries containing title, source, body, url, date).
    """
    try:
        results = DDGS().news(query, max_results=5)
        
        # Ensure we return a consistent format even if empty
        if not results:
            return []
            
        return list(results)
    except Exception as e:
        logger.error(f"Error fetching news for query '{query}': {e}")
        return []
