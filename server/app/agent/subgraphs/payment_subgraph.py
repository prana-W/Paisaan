import logging
from typing import Annotated, TypedDict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def initiate_payment_node(state: dict) -> dict:
    """
    Interrupts the graph to prompt the frontend to display the Razorpay payment UI.
    """
    messages = list(state.get("messages", []))
    
    # In a real scenario, we would calculate the total investment amount from the plan
    # For now, we just prompt the UI. The frontend is expected to intercept this.
    prompt_msg = "Please complete the payment using the Razorpay interface to fund your virtual wallet."
    
    # We use interrupt to pause execution and signal the frontend
    payment_response = interrupt({
        "type": "payment_required", 
        "text": prompt_msg,
        "action": "trigger_razorpay"
    })
    
    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": prompt_msg},
            # We record whatever the frontend sends back when it resumes the graph
            {"role": "user", "content": str(payment_response)}
        ]
    }


def verify_payment_node(state: dict) -> dict:
    """
    Evaluates the response from the frontend Razorpay flow.
    """
    messages = list(state.get("messages", []))
    
    # The last message is what the user (frontend) sent back when resuming
    user_response = messages[-1].get("content", "") if messages else ""
    
    if "success" in user_response.lower() or "pay_" in user_response.lower():
        status_msg = "Payment received successfully! Your virtual wallet has been funded."
        payment_status = "success"
    else:
        status_msg = "Payment failed or was cancelled. No funds were added."
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
