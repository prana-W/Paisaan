"""
API routes for session management.

Endpoints (§7 of agent.md):
  POST /session                  — create session, start graph, return first interrupt
  POST /session/{id}/message     — send a chat message during intake
  POST /session/{id}/resume      — resume a paused (interrupted) graph
  GET  /portfolio/{user_id}      — portfolio valuation (stubbed in Phase 0)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.agent.graph import get_graph
from app.db.session import get_db
from app.db.crud import get_or_create_user, create_session, get_session, update_session_status
from app.schemas.profile import (
    CreateSessionRequest, MessageRequest, ResumeRequest,
    SessionResponse, ResumeResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _run_graph_until_interrupt(graph, thread_id: str, initial_state: dict | None = None):
    """
    Invoke the graph from the start and collect events until it pauses or finishes.
    Returns (status, interrupt_payload_or_none).
    """
    config = {"configurable": {"thread_id": thread_id}}

    for event in graph.stream(initial_state, config=config, stream_mode="values"):
        logger.debug("[graph] event keys: %s", list(event.keys()))

    state = graph.get_state(config)
    interrupt_payload = None
    final_status = "running"

    if state.tasks:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_payload = task.interrupts[0].value
                final_status = "interrupted"
                break
        if not interrupt_payload:
            final_status = "interrupted"
    elif not state.next:
        final_status = "complete"

    return final_status, interrupt_payload


# ── POST /session ─────────────────────────────────────────────────────────────

@router.post("/session", response_model=SessionResponse)
def create_new_session(
    body: CreateSessionRequest,
    db: DBSession = Depends(get_db),
):
    """
    Start a new investment planning session.
    Creates user + session row, starts graph, returns first interrupt payload.
    """
    graph = get_graph()
    thread_id = str(uuid.uuid4())

    user = get_or_create_user(db, body.user_id)
    create_session(db, user_id=user.id, thread_id=thread_id)

    logger.info("New session thread_id=%s user_id=%s", thread_id, user.id)

    initial_state = {
        "thread_id": thread_id,
        "messages": [],
        "profile": {},
        "horizon": None,
        "market": {},
        "draft_allocation": [],
        "confirmed": False,
        "transaction_id": None,
    }

    status, payload = _run_graph_until_interrupt(graph, thread_id, initial_state)
    update_session_status(db, thread_id, status)

    message = payload.get("text") if isinstance(payload, dict) else None

    return SessionResponse(
        thread_id=thread_id,
        user_id=user.id,
        status=status,
        message=message,
        payload=payload,
    )


# ── POST /session/{id}/message ────────────────────────────────────────────────

@router.post("/session/{session_id}/message", response_model=ResumeResponse)
def send_message(
    session_id: str,
    body: MessageRequest,
    db: DBSession = Depends(get_db),
):
    """
    Send a chat message. Phase 0: thin wrapper around resume.
    Phase 1: will handle multi-turn dynamic Q&A.
    """
    return _resume_session(session_id, body.content, db)


# ── POST /session/{id}/resume ─────────────────────────────────────────────────

@router.post("/session/{session_id}/resume", response_model=ResumeResponse)
def resume_session(
    session_id: str,
    body: ResumeRequest,
    db: DBSession = Depends(get_db),
):
    """
    Resume a paused graph with the user's answer.
    CRITICAL: state is loaded from SqliteSaver checkpointer — NOT server memory.
    Works across tab closes and new HTTP connections.
    """
    return _resume_session(session_id, body.answer, db)


def _resume_session(session_id: str, answer: str, db: DBSession) -> ResumeResponse:
    """Shared logic for message and resume endpoints."""
    graph = get_graph()

    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    config = {"configurable": {"thread_id": session_id}}
    logger.info("Resuming session thread_id=%s answer=%r", session_id, answer)

    from langgraph.types import Command
    for event in graph.stream(Command(resume=answer), config=config, stream_mode="values"):
        logger.debug("[graph] resume event keys: %s", list(event.keys()))

    state = graph.get_state(config)
    interrupt_payload = None
    status = "complete"

    # Check for active interrupts in pending tasks
    if state.tasks:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_payload = task.interrupts[0].value
                status = "interrupted"
                break

    # If there are next nodes but no interrupt payload, graph is still running
    if state.next and not interrupt_payload:
        status = "running"

    update_session_status(db, session_id, status)

    message = interrupt_payload.get("text") if isinstance(interrupt_payload, dict) else "Session complete. ✅"

    return ResumeResponse(
        thread_id=session_id,
        status=status,
        message=message,
        payload=interrupt_payload,
    )


# ── GET /portfolio/{user_id} ──────────────────────────────────────────────────

@router.get("/portfolio/{user_id}")
def get_portfolio(user_id: str, db: DBSession = Depends(get_db)):
    """
    Phase 7: live portfolio valuation.
    Phase 0: stub so the frontend route doesn't 404.
    """
    logger.info("Portfolio requested for user_id=%s (Phase 0 stub)", user_id)
    return {
        "user_id": user_id,
        "holdings": [],
        "total_invested": 0,
        "current_value": 0,
        "gain_loss": 0,
        "gain_loss_pct": 0,
        "note": "Portfolio tracking is implemented in Phase 7.",
    }
