import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.agent.graph import get_graph
from app.db.session import get_db
from app.db.crud import (
    get_or_create_user, create_session, get_session, update_session_status,
    get_sessions, delete_session, get_all_investments, get_wallet_balance,
)
from app.schemas.profile import (
    CreateSessionRequest, MessageRequest, ResumeRequest,
    SessionResponse, ResumeResponse, SessionStateResponse, SessionSummary, ToolCallInfo,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


TOOL_LABELS = {
    "get_mutual_fund_nav":   "📊 Fetching Mutual Fund NAVs",
    "get_stock_price":       "📈 Fetching Stock Prices",
    "get_gold_silver_price": "🥇 Fetching Bullion Prices",
    "get_fd_rates":          "🏦 Fetching FD Rates",
    "search_market_news":    "📰 Scanning Market News",
    "split_investment":      "🧮 Calculating Investment Gains",
}


def _extract_tool_calls(state) -> list[ToolCallInfo]:
    """
    Walk all message lists in state to extract tool invocations and their results.
    Scans both `messages` (main chat) and `research_messages` (market subgraph) so
    any future subgraph whose tools land in either list is captured automatically.
    Returns a deduplicated list of ToolCallInfo for the frontend to display.
    """
    all_messages = (
        list(state.values.get("messages", []))
        + list(state.values.get("research_messages", []))
        + list(state.values.get("gains_messages", []))
    )
    tool_calls: list[ToolCallInfo] = []
    seen_ids: set[str] = set()

    # Map tool_call_id → name from AIMessage tool_calls
    id_to_name: dict[str, str] = {}
    for msg in all_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                id_to_name[tc["id"]] = tc["name"]

    # Collect results from ToolMessages, deduplicating by tool_call_id
    for msg in all_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and call_id in seen_ids:
                continue
            if call_id:
                seen_ids.add(call_id)

            name = id_to_name.get(call_id, getattr(msg, "name", None) or "tool")
            label = TOOL_LABELS.get(name, f"🔧 {name.replace('_', ' ').title()}")
            content = msg.content
            if isinstance(content, list):
                content = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
            tool_calls.append(ToolCallInfo(name=label, status="success", result_preview=str(content)))

    return tool_calls


def _stream_until_interrupt(graph, thread_id: str, input_payload):
    config = {"configurable": {"thread_id": thread_id}}
    for event in graph.stream(input_payload, config=config, stream_mode="values"):
        logger.debug("[graph] event keys: %s", list(event.keys()))

    state = graph.get_state(config)
    interrupt_payload = None
    status = "complete"

    for task in (state.tasks or []):
        if hasattr(task, "interrupts") and task.interrupts:
            interrupt_payload = task.interrupts[0].value
            status = "interrupted"
            break

    if state.next and not interrupt_payload:
        status = "running"

    return status, interrupt_payload, state


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(user_id: str | None = None, db: DBSession = Depends(get_db)):
    return get_sessions(db, user_id)


@router.get("/session/{session_id}", response_model=SessionStateResponse)
def get_session_state(session_id: str, db: DBSession = Depends(get_db)):
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    state = graph.get_state(config)

    if not state.values:
        return SessionStateResponse(exists=False, thread_id=session_id)

    interrupt_payload = None
    status = "complete"
    for task in (state.tasks or []):
        if hasattr(task, "interrupts") and task.interrupts:
            interrupt_payload = task.interrupts[0].value
            status = "interrupted"
            break

    if state.next and not interrupt_payload:
        status = "running"

    db_session = get_session(db, session_id)
    user_id = db_session.user_id if db_session else None

    if not db_session:
        user = get_or_create_user(db)
        create_session(db, user_id=user.id, thread_id=session_id)
        user_id = user.id

    return SessionStateResponse(
        exists=True,
        thread_id=session_id,
        user_id=user_id,
        status=status,
        messages=state.values.get("messages", []),
        profile=state.values.get("profile", {}),
        pending_question=interrupt_payload,
        tool_calls=_extract_tool_calls(state),
    )


import psycopg
from app.core.config import get_settings

def _delete_checkpoints(thread_id: str):
    settings = get_settings()
    try:
        with psycopg.connect(settings.checkpoint_db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
            conn.commit()
    except Exception as e:
        logger.warning("Failed to clear checkpoints for thread_id=%s: %s", thread_id, e)


@router.delete("/session/{session_id}")
def delete_session_endpoint(session_id: str, db: DBSession = Depends(get_db)):
    success = delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    _delete_checkpoints(session_id)
    return {"status": "success", "message": "Session deleted"}


@router.post("/session", response_model=SessionResponse)
def create_new_session(body: CreateSessionRequest, db: DBSession = Depends(get_db)):
    graph = get_graph()
    thread_id = body.thread_id or str(uuid.uuid4())

    user = get_or_create_user(db, body.user_id)
    create_session(db, user_id=user.id, thread_id=thread_id)

    logger.info("New session thread_id=%s user_id=%s", thread_id, user.id)

    initial_state = {
        "thread_id": thread_id,
        "messages": [],
        "profile": {},
        "market": {},
        "investment_plan": {},
        "research_consent": None,
        "gains_consent": None,
        "payment_consent": None,
        "draft_allocation": [],
        "confirmed": False,
        "transaction_id": None,
        "investment_executed": False,
        "research_messages": [],
        "gains_messages": [],
    }

    status, payload, _ = _stream_until_interrupt(graph, thread_id, initial_state)
    update_session_status(db, thread_id, status)

    message = payload.get("text") if isinstance(payload, dict) else None

    return SessionResponse(
        thread_id=thread_id,
        user_id=user.id,
        status=status,
        message=message,
        payload=payload,
    )


@router.post("/session/{session_id}/message", response_model=ResumeResponse)
def send_message(session_id: str, body: MessageRequest, db: DBSession = Depends(get_db)):
    return _resume_session(session_id, body.content, db)


@router.post("/session/{session_id}/resume", response_model=ResumeResponse)
def resume_session(session_id: str, body: ResumeRequest, db: DBSession = Depends(get_db)):
    return _resume_session(session_id, body.answer, db)


def _coerce_content(content) -> str:
    """Normalize LangChain/Gemini message content to a plain string.
    Gemini can return content as a list of blocks: [{'type': 'text', 'text': '...'}]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


def _resume_session(session_id: str, answer: str, db: DBSession) -> ResumeResponse:
    graph = get_graph()
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info("Resuming session thread_id=%s answer=%r", session_id, answer)

    from langgraph.types import Command
    status, payload, state = _stream_until_interrupt(graph, session_id, Command(resume=answer))
    update_session_status(db, session_id, status)

    if payload:
        # Graph paused on an interrupt — return the interrupt question
        raw_text = payload.get("text") if isinstance(payload, dict) else payload
        message = _coerce_content(raw_text)
    else:
        # Graph ran to completion — return the last assistant message from state
        messages = state.values.get("messages", [])
        last_ai = next(
            (m for m in reversed(messages) if (
                (isinstance(m, dict) and m.get("role") == "assistant") or
                (hasattr(m, "type") and m.type == "ai")
            )),
            None,
        )
        if last_ai:
            raw = last_ai.get("content") if isinstance(last_ai, dict) else last_ai.content
            message = _coerce_content(raw)
        else:
            market = state.values.get("market", {})
            message = (
                market.get("research_summary") if isinstance(market, dict)
                else getattr(market, "research_summary", None)
            ) or "Research complete. ✅"

    return ResumeResponse(
        thread_id=session_id,
        status=status,
        message=message,
        payload=payload,
        tool_calls=_extract_tool_calls(state),
    )



@router.get("/portfolio/investments")
def get_investments_endpoint(db: DBSession = Depends(get_db)):
    """Return all investments with live-computed current value."""
    from datetime import datetime
    import math
    investments = get_all_investments(db)
    result = []
    now = datetime.utcnow()
    for inv in investments:
        # Compound interest: P * (1 + r)^t  where t is years since purchase
        years_elapsed = (now - inv.bought_at).days / 365.25
        current_value = round(inv.principal * ((1 + inv.annual_rate_pct / 100) ** years_elapsed), 2)
        gain = round(current_value - inv.principal, 2)
        gain_pct = round((gain / inv.principal) * 100, 2) if inv.principal > 0 else 0.0
        result.append({
            "id": inv.id,
            "thread_id": inv.thread_id,
            "source": inv.source,
            "asset_type": inv.asset_type,
            "principal": inv.principal,
            "holding": inv.holding,
            "annual_rate_pct": inv.annual_rate_pct,
            "years": inv.years,
            "current_value": current_value,
            "gain": gain,
            "gain_pct": gain_pct,
            "bought_at": inv.bought_at.isoformat(),
            "last_updated": inv.last_updated.isoformat(),
            "notes": inv.notes,
        })
    return result


@router.get("/portfolio/summary")
def get_portfolio_summary(db: DBSession = Depends(get_db)):
    """Return aggregate portfolio stats + wallet balance."""
    from datetime import datetime
    investments = get_all_investments(db)
    now = datetime.utcnow()
    total_invested = 0.0
    total_current = 0.0
    for inv in investments:
        years_elapsed = (now - inv.bought_at).days / 365.25
        current_value = inv.principal * ((1 + inv.annual_rate_pct / 100) ** years_elapsed)
        total_invested += inv.principal
        total_current += current_value
    gain = round(total_current - total_invested, 2)
    gain_pct = round((gain / total_invested) * 100, 2) if total_invested > 0 else 0.0
    wallet_balance = get_wallet_balance(db)
    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "gain_loss": gain,
        "gain_loss_pct": gain_pct,
        "wallet_balance": wallet_balance,
        "investment_count": len(investments),
    }
