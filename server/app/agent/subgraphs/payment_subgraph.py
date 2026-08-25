import logging
from typing import Annotated, TypedDict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def initiate_payment_node(state: dict) -> dict:
    import json
    messages = list(state.get("messages", []))
    
    gains_messages = state.get("gains_messages", [])
    total_amount = 10000.0
    for msg in gains_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                raw = msg.content
                data = json.loads(raw) if isinstance(raw, str) else raw
                if "total_principal" in data:
                    total_amount = data["total_principal"]
            except Exception:
                pass
                
    prompt_msg = f"I'm ready to execute your personalized investment plan! We need to fund your virtual wallet with exactly ₹{total_amount:,.2f}."
    
    payment_response = interrupt({
        "type": "payment_required", 
        "text": prompt_msg,
        "action": "trigger_razorpay",
        "amount": total_amount
    })
    
    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": prompt_msg},
            {"role": "user", "content": str(payment_response)}
        ]
    }


def verify_payment_node(state: dict) -> dict:
    messages = list(state.get("messages", []))
    user_response = messages[-1].get("content", "") if messages else ""
    
    if "success" in user_response.lower() or "pay_" in user_response.lower():
        txn_id = user_response if "pay_" in user_response else "success"
        status_msg = f"✅ Payment received successfully! Transaction ID: **{txn_id}**\n\nYour virtual wallet has been funded and your investments have been executed. Please view your **Portfolio** tab for a detailed breakdown."
        payment_status = "success"
    else:
        status_msg = "❌ Payment declined or failed. The execution flow has been safely aborted."
        payment_status = "failed"
        
    return {
        **state,
        "payment_status": payment_status,
        "messages": messages + [{"role": "assistant", "content": status_msg}]
    }


def build_payment_subgraph():
    # Define a scoped schema if needed, but we can just use dict
    builder = StateGraph(dict)
    
    builder.add_node("initiate_payment", initiate_payment_node)
    builder.add_node("verify_payment", verify_payment_node)
    
    builder.add_edge(START, "initiate_payment")
    builder.add_edge("initiate_payment", "verify_payment")
    builder.add_edge("verify_payment", END)
    
    compiled = builder.compile()
    logger.debug("Payment Subgraph compiled")
    return compiled
