import json
import uuid
import logging
from typing import Annotated, TypedDict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.agent.state import AgentState
from app.db.session import SessionLocal
from app.db.models import User, Transaction

logger = logging.getLogger(__name__)


def initiate_payment_node(state: dict) -> dict:
    messages = list(state.get("messages", []))
    gains_messages = state.get("gains_messages", [])
    user_id = state.get("user_id")
    
    total_amount = 0.0
    for msg in gains_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                raw = msg.content
                data = json.loads(raw) if isinstance(raw, str) else raw
                if "total_principal" in data:
                    total_amount = data["total_principal"]
            except Exception:
                pass
                
    wallet_balance = 0.0
    if user_id:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                wallet_balance = user.wallet_balance

    if wallet_balance >= total_amount:
        return {
            **state,
            "payment_status": "funded"
        }
        
    shortfall = total_amount - wallet_balance
    prompt_msg = f"I'm ready to execute your personalized investment plan! Your wallet balance is ₹{wallet_balance:,.2f}, which is short of the required ₹{total_amount:,.2f}. Please add ₹{shortfall:,.2f} to proceed."
    
    payment_response = interrupt({
        "type": "payment_required", 
        "text": prompt_msg,
        "action": "trigger_razorpay",
        "shortfall": shortfall
    })
    
    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": prompt_msg},
            {"role": "user", "content": str(payment_response)}
        ]
    }


def verify_payment_node(state: dict) -> dict:
    user_id = state.get("user_id")
    gains_messages = state.get("gains_messages", [])
    messages = list(state.get("messages", []))
    
    total_amount = 0.0
    for msg in gains_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                raw = msg.content
                data = json.loads(raw) if isinstance(raw, str) else raw
                if "total_principal" in data:
                    total_amount = data["total_principal"]
            except Exception:
                pass

    wallet_balance = 0.0
    if user_id:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                wallet_balance = user.wallet_balance

    if wallet_balance >= total_amount:
        return {
            **state,
            "payment_status": "funded",
            "messages": messages + [{"role": "assistant", "content": "Funds verified! Proceeding with investment..."}]
        }
    else:
        return {
            **state,
            "payment_status": "shortfall",
            "messages": messages + [{"role": "assistant", "content": "Payment flow cancelled or insufficient funds added."}]
        }


def execute_investment_node(state: dict) -> dict:
    user_id = state.get("user_id")
    thread_id = state.get("thread_id")
    gains_messages = state.get("gains_messages", [])
    messages = list(state.get("messages", []))
    
    if not user_id:
        return state

    tool_result = None
    for msg in gains_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                raw = msg.content
                tool_result = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                pass

    if tool_result and "allocations" in tool_result:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return state
                
            total_amount = tool_result.get("total_principal", 0.0)
            
            # Deduct from wallet
            user.wallet_balance -= total_amount
            
            # Insert transactions
            for alloc in tool_result["allocations"]:
                txn = Transaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    thread_id=thread_id,
                    action="buy",
                    source=alloc.get("source", "Unknown"),
                    amount=alloc.get("principal", 0.0),
                    percent_allocation=alloc.get("percent", 0.0),
                    status="success",
                    reasoning="Allocated as part of the Paisaan virtual investment plan."
                )
                db.add(txn)
            
            db.commit()

    status_msg = f"✅ Portfolio Executed! Your investments have been securely logged. Please view your **Portfolio** tab for a detailed breakdown."
    
    return {
        **state,
        "payment_status": "success",
        "confirmed": True,
        "messages": messages + [{"role": "assistant", "content": status_msg}]
    }


def route_payment(state: dict) -> str:
    status = state.get("payment_status")
    if status == "funded":
        return "execute_investment"
    # If shortfall, we loop back to ask again (or exit if the frontend ends it)
    # Since we need to interrupt again, we route back to initiate_payment
    return "initiate_payment"


def build_payment_subgraph():
    builder = StateGraph(dict)
    
    builder.add_node("initiate_payment", initiate_payment_node)
    builder.add_node("verify_payment", verify_payment_node)
    builder.add_node("execute_investment", execute_investment_node)
    
    builder.add_edge(START, "initiate_payment")
    builder.add_conditional_edges("initiate_payment", route_payment)
    builder.add_conditional_edges("verify_payment", route_payment)
    builder.add_edge("execute_investment", END)
    
    compiled = builder.compile()
    logger.debug("Payment Subgraph compiled")
    return compiled

