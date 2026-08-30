import logging
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _infer_asset_type(source: str) -> str:
    lower = source.lower()
    for keyword, asset_type in [
        ("mutual fund", "mutual_fund"), ("mf", "mutual_fund"), ("fund", "mutual_fund"),
        ("stock", "stock"), ("equity", "stock"), ("share", "stock"),
        ("gold", "gold"), ("silver", "silver"),
        ("fd", "fd"), ("fixed deposit", "fd"), ("deposit", "fd")
    ]:
        if keyword in lower:
            return asset_type
    return "other"


@tool
def split_investment(
    total_amount: float,
    years: int,
    allocations: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Split a total investment amount across multiple sources and calculate projected
    gains for each source using compound interest.

    Each allocation in the list must have:
    - source: name of the investment (e.g. "HDFC Balanced Fund", "Gold", "SBI FD", "Reliance")
    - percent: what percentage of total_amount goes here (all percents must sum to 100)
    - annual_rate_pct: expected annual return rate as a percentage (used for gain calculation)
    - holding: (optional) unit price / rate representation at purchase (e.g. "₹2,450.50/stock", "₹6,800/g", "7.5% p.a.", "₹45.20 NAV")

    Returns a dictionary with:
    - allocations: list of per-source results (principal, holding, final_value, gain, etc.)
    - total_principal: should equal total_amount
    - total_final_value: sum of all final values
    - total_gain: total profit across all sources
    - years: the investment duration used
    """
    results = []
    total_pct = sum(a.get("percent", 0) for a in allocations)

    if abs(total_pct - 100.0) > 0.01:
        return {
            "error": f"Allocation percentages sum to {total_pct}%, must sum to 100%.",
            "allocations": [],
            "total_principal": total_amount,
            "total_final_value": 0,
            "total_gain": 0,
            "years": years,
        }

    total_final = 0.0
    total_gain = 0.0

    for alloc in allocations:
        source = alloc.get("source", "Unknown")
        pct = alloc.get("percent", 0)
        rate = alloc.get("annual_rate_pct", 0)
        freq = alloc.get("compounding_frequency", 1)

        principal = total_amount * (pct / 100.0)
        r = rate / 100.0
        final_value = principal * ((1 + r / freq) ** (freq * years))
        gain = final_value - principal

        total_final += final_value
        total_gain += gain

        holding = alloc.get("holding")
        if not holding:
            asset_type = alloc.get("asset_type") or _infer_asset_type(source)
            if asset_type == "fd":
                holding = f"{rate}% p.a."
            elif asset_type == "stock":
                holding = f"₹{rate*100:,.2f}/stock" if rate > 0 else f"₹1,000.00/stock"
            elif asset_type in ("gold", "silver"):
                holding = f"₹{rate*500:,.2f}/g" if rate > 0 else f"₹6,500.00/g"
            elif asset_type == "mutual_fund":
                holding = f"₹{rate*5:,.2f} NAV" if rate > 0 else f"₹50.00 NAV"
            else:
                holding = f"{rate}% p.a."

        results.append({
            "source": source,
            "percent": pct,
            "principal": round(principal, 2),
            "holding": str(holding),
            "annual_rate_pct": rate,
            "years": years,
            "final_value": round(final_value, 2),
            "total_gain": round(gain, 2),
            "gain_pct": round((gain / principal) * 100, 2) if principal > 0 else 0.0,
        })

    return {
        "allocations": results,
        "total_principal": round(total_amount, 2),
        "total_final_value": round(total_final, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_pct": round((total_gain / total_amount) * 100, 2) if total_amount > 0 else 0.0,
        "years": years,
    }
