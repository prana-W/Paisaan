import yfinance as yf
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def get_gold_silver_price() -> Optional[Dict[str, Any]]:
    """
    Fetch the current market prices for Gold and Silver in India (INR).
    This tool uses the highly correlated domestic ETF proxies (Nippon India Gold/Silver BeES)
    traded on the NSE to get real-time actionable market prices.
    
    Returns a dictionary with:
    - gold_price_inr
    - silver_price_inr
    """
    try:
        # GOLDBEES.NS tracks domestic gold prices, SILVERBEES.NS tracks domestic silver
        gold_ticker = yf.Ticker("GOLDBEES.NS")
        silver_ticker = yf.Ticker("SILVERBEES.NS")
        
        gold_price = gold_ticker.fast_info.get("last_price")
        if not gold_price:
            hist = gold_ticker.history(period="1d")
            gold_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
        silver_price = silver_ticker.fast_info.get("last_price")
        if not silver_price:
            hist = silver_ticker.history(period="1d")
            silver_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
        return {
            "gold_price_inr": round(float(gold_price), 2),
            "silver_price_inr": round(float(silver_price), 2),
            "source": "NSE ETFs (GOLDBEES/SILVERBEES)"
        }
    except Exception as e:
        logger.error(f"Error fetching bullion prices: {e}")
        return None
