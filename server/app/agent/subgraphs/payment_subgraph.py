"""
Payment Subgraph — Steps 3–8

Flow:
    START
      └─→ verify_funds_node
            ├─ (enough balance) ──→ execute_investment_node ──→ END
            └─ (not enough)     ──→ [interrupt: ask user to top up]
                                      └─ (user resumes) ──→ verify_funds_node  [loop]
"""
import logging
from typing import Annotated, TypedDict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.crud import get_wallet_balance, deduct_from_wallet, create_investment, log_transaction, get_or_create_user

logger = logging.getLogger(__name__)

# Single shared user — single-user app
_SINGLE_USER_ID = "default"

# Maps source names to asset_type enum values (best-effort heuristic)
_ASSET_TYPE_MAP = {
    "mutual fund": "mutual_fund",
    "mf": "mutual_fund",
    "fund": "mutual_fund",
    "stock": "stock",
    "equity": "stock",
    "share": "stock",
    "gold": "gold",
    "silver": "silver",
    "fd": "fd",
    "fixed deposit": "fd",
    "deposit": "fd",
}


def _infer_asset_type(source: str) -> str:
    """Infer asset_type from the source name string."""
    lower = source.lower()
    for keyword, asset_type in _ASSET_TYPE_MAP.items():
        if keyword in lower:
            return asset_type
    return "other"


def _get_llm():
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
    )


# ── Nodes ──────────────────────────────────────────────────────────────────────

def verify_funds_node(state: dict) -> dict:
    """
    Checks if the wallet has enough balance for the total investment.
    - If yes → routes to execute_investment_node.
    - If no  → uses LLM to compose a friendly message telling the user exactly
               how much more they need, then interrupts and waits.
    On resume (user sends any message), it loops back here to check again.
    """
    messages = list(state.get("messages", []))
    investment_plan = state.get("investment_plan", {})

    if hasattr(investment_plan, "model_dump"):
        investment_plan = investment_plan.model_dump()

    total_required = investment_plan.get("total_principal", 0.0)

    db = SessionLocal()
    try:
        current_balance = get_wallet_balance(db)
    finally:
        db.close()

    logger.info(
        "verify_funds: required=₹%.2f, wallet=₹%.2f",
        total_required, current_balance,
    )

    if current_balance >= total_required:
        # Sufficient funds — proceed silently
        return {**state, "messages": messages}

    # Insufficient funds — compose a message via LLM
    shortfall = round(total_required - current_balance, 2)

    llm = _get_llm()
    system = SystemMessage(content=(
        "You are Paisaan, a friendly investment assistant. "
        "The user wants to invest but doesn't have enough wallet balance. "
        "Write a short, warm message (2-3 sentences max) telling them:\n"
        f"- Required: ₹{total_required:,.2f}\n"
        f"- Current wallet: ₹{current_balance:,.2f}\n"
        f"- Shortfall: ₹{shortfall:,.2f}\n"
        "Tell them to add the shortfall to their wallet via the Portfolio page, "
        "then come back and send any message to continue. "
        "Be concise and encouraging. Do NOT offer any other options."
    ))
    response = llm.invoke([system, HumanMessage(content="Generate the insufficient funds message.")])
    ai_message = response.content if hasattr(response, "content") else str(response)

    # Interrupt — the user must add money and then resume the chat
    answer = interrupt({"type": "question", "text": ai_message})

    # When user resumes, add their reply to messages and loop back
    updated_messages = messages + [
        {"role": "assistant", "content": ai_message},
        {"role": "user", "content": str(answer)},
    ]
    return {**state, "messages": updated_messages}


def _check_funds(state: dict) -> str:
    """Route: if wallet >= required → execute, else loop back to verify."""
    investment_plan = state.get("investment_plan", {})
    if hasattr(investment_plan, "model_dump"):
        investment_plan = investment_plan.model_dump()

    total_required = investment_plan.get("total_principal", 0.0)

    db = SessionLocal()
    try:
        current_balance = get_wallet_balance(db)
    finally:
        db.close()

    if current_balance >= total_required:
        return "execute_investment"
    return "verify_funds"


def execute_investment_node(state: dict) -> dict:
    """
    Executes all allocations in the investment plan:
    1. Creates an Investment DB row for each allocation.
    2. Debits total amount from wallet.
    3. Logs a transaction in the audit log.
    Sets investment_executed = True in state.
    """
    investment_plan = state.get("investment_plan", {})
    if hasattr(investment_plan, "model_dump"):
        investment_plan = investment_plan.model_dump()

    thread_id = state.get("thread_id", "unknown")
    allocations = investment_plan.get("allocations", [])
    total_principal = investment_plan.get("total_principal", 0.0)
    years = investment_plan.get("years", 1)

    db = SessionLocal()
    try:
        # Ensure the default user exists
        user = get_or_create_user(db, _SINGLE_USER_ID)

        # Create one Investment row per allocation
        for alloc in allocations:
            source = alloc["source"]
            asset_type = _infer_asset_type(source)
            holding = alloc.get("holding") or f"{alloc.get('annual_rate_pct', 0)}% p.a."
            create_investment(
                db=db,
                user_id=user.id,
                thread_id=thread_id,
                source=source,
                asset_type=asset_type,
                principal=alloc["principal"],
                holding=holding,
                annual_rate_pct=alloc.get("annual_rate_pct", 0.0),
                years=alloc.get("years", years),
                notes=f"Session {thread_id}",
            )
            logger.info("Investment created: %s ₹%.2f holding=%s", source, alloc["principal"], holding)

        # Deduct from wallet
        new_balance = deduct_from_wallet(db, total_principal)
        logger.info("Wallet debited ₹%.2f. New balance: ₹%.2f", total_principal, new_balance)

        # Audit log
        log_transaction(
            db=db,
            user_id=user.id,
            action="buy",
            amount=total_principal,
            status="success",
            reasoning=(
                f"AI executed investment plan for thread {thread_id}. "
                f"{len(allocations)} allocations totalling ₹{total_principal:,.2f} "
                f"over {years} years."
            ),
        )

    except Exception as e:
        logger.error("execute_investment_node failed: %s", e, exc_info=True)
        # Log a failed transaction
        try:
            log_transaction(
                db=db,
                user_id=_SINGLE_USER_ID,
                action="buy",
                amount=total_principal,
                status="failed",
                reasoning=f"Investment execution failed: {e}",
            )
        except Exception:
            pass
        raise
    finally:
        db.close()

    return {**state, "investment_executed": True}


# ── Subgraph builder ───────────────────────────────────────────────────────────

def build_payment_subgraph():
    class _Schema(TypedDict, total=False):
        messages: Annotated[list, add_messages]
        investment_plan: Any
        investment_executed: bool
        thread_id: str

    builder = StateGraph(_Schema)

    builder.add_node("verify_funds", verify_funds_node)
    builder.add_node("execute_investment", execute_investment_node)

    builder.add_edge(START, "verify_funds")
    builder.add_conditional_edges("verify_funds", _check_funds, {
        "execute_investment": "execute_investment",
        "verify_funds": "verify_funds",      # loop back if still insufficient
    })
    builder.add_edge("execute_investment", END)

    compiled = builder.compile()
    logger.debug("Payment Subgraph compiled (%d nodes)", len(builder.nodes))
    return compiled
