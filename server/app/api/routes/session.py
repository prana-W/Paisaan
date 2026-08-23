import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.agent.graph import get_graph
from app.db.session import get_db
from app.db.crud import get_or_create_user, create_session, get_session, update_session_status, get_sessions, delete_session
from app.schemas.profile import (
    CreateSessionRequest, MessageRequest, ResumeRequest,
    SessionResponse, ResumeResponse, SessionStateResponse, SessionSummary,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


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
    )


import sqlite3
from app.core.config import get_settings

def _delete_checkpoints(thread_id: str):
    settings = get_settings()
    try:
        conn = sqlite3.connect(settings.checkpoint_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM checkpoint_reads WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
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
        "horizon": None,
        "market": {},
        "draft_allocation": [],
        "confirmed": False,
        "transaction_id": None,
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


def _resume_session(session_id: str, answer: str, db: DBSession) -> ResumeResponse:
    graph = get_graph()
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info("Resuming session thread_id=%s answer=%r", session_id, answer)

    from langgraph.types import Command
    status, payload, _ = _stream_until_interrupt(graph, session_id, Command(resume=answer))
    update_session_status(db, session_id, status)

    message = payload.get("text") if isinstance(payload, dict) else "Session complete. ✅"

    return ResumeResponse(thread_id=session_id, status=status, message=message, payload=payload)


@router.get("/portfolio/{user_id}")
def get_portfolio(user_id: str, db: DBSession = Depends(get_db)):
    return {
        "user_id": user_id,
        "holdings": [],
        "total_invested": 0,
        "current_value": 0,
        "gain_loss": 0,
        "gain_loss_pct": 0,
    }
