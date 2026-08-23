import yfinance as yf
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def get_stock_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest stock price and market data for a given symbol.
    Automatically appends '.NS' (National Stock Exchange of India) if no exchange suffix is provided,
    assuming Indian stocks by default.
    
    Returns a dictionary with:
    - symbol
    - current_price
    - previous_close
    - currency
    """
    # Auto-append .NS for Indian stocks if no suffix is present
    if "." not in symbol:
        symbol = f"{symbol}.NS"
        
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        
        # fast_info is much faster and more reliable than .info
        current_price = info.get("last_price")
        if current_price is None:
            # Fallback to history if fast_info fails
            hist = ticker.history(period="1d")
            if hist.empty:
                logger.warning(f"No price data found for {symbol}")
                return None
            current_price = hist['Close'].iloc[-1]
            
        return {
            "symbol": symbol,
            "current_price": round(float(current_price), 2),
            "previous_close": round(float(info.get("previous_close", 0)), 2),
            "currency": info.get("currency", "INR")
        }
    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {e}")
        return None
