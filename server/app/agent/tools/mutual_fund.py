import httpx
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def get_mutual_fund_nav(scheme_code: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest Net Asset Value (NAV) for a given Indian mutual fund scheme code.
    Uses the free mfapi.in API.
    
    Returns a dictionary with:
    - scheme_code
    - scheme_name
    - nav (latest nav value)
    - date (date of the latest nav)
    """
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "SUCCESS" or not data.get("data"):
                logger.warning(f"MF API returned no data for scheme code: {scheme_code}")
                return None
                
            meta = data.get("meta", {})
            latest_nav_data = data["data"][0]
            
            return {
                "scheme_code": meta.get("scheme_code", str(scheme_code)),
                "scheme_name": meta.get("scheme_name", "Unknown Scheme"),
                "nav": float(latest_nav_data.get("nav", 0.0)),
                "date": latest_nav_data.get("date", "")
            }
            
    except Exception as e:
        logger.error(f"Error fetching NAV for mutual fund {scheme_code}: {e}")
        return None
