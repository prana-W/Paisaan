import logging
from duckduckgo_search import DDGS
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def get_fd_rates() -> str:
    """
    Fetch the latest Fixed Deposit (FD) interest rates in India.
    Uses DuckDuckGo web search to find current aggregate rates.
    
    Returns a textual summary of current FD rates from top banks.
    """
    try:
        results = DDGS().text("latest FD interest rates India SBI HDFC ICICI", max_results=3)
        if not results:
            return "Could not fetch latest FD rates at this time. Assume a rough average of 6.5% - 7.5% p.a. for major banks."
            
        summary = "Recent FD Rates snippets:\n"
        for idx, res in enumerate(results):
            summary += f"- {res.get('title')}: {res.get('body')}\n"
            
        return summary
    except Exception as e:
        logger.error(f"Error fetching FD rates: {e}")
        return "Could not fetch latest FD rates due to an error. Assume a rough average of 6.5% - 7.5% p.a. for major banks."
