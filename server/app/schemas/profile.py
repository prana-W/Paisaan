"""
Pydantic schemas for the /session API surface.
These are the request/response shapes — NOT the internal graph state.
"""
from pydantic import BaseModel


# ── Request bodies ─────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Body for POST /session. user_id is optional for anonymous sessions."""
    user_id: str | None = None


class MessageRequest(BaseModel):
    """Body for POST /session/{id}/message (intake chat turn)."""
    content: str


class ResumeRequest(BaseModel):
    """
    Body for POST /session/{id}/resume.
    answer is the user's reply to whatever interrupt() asked.
    """
    answer: str


# ── Response bodies ────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    """Returned by POST /session after graph starts and hits first interrupt."""
    thread_id: str
    user_id: str
    status: str          # "interrupted" | "running" | "complete"
    message: str | None = None   # The question or message for the user
    payload: dict | None = None  # Full interrupt payload if needed by frontend


class ResumeResponse(BaseModel):
    """Returned by POST /session/{id}/resume after graph continues."""
    thread_id: str
    status: str
    message: str | None = None
    payload: dict | None = None
