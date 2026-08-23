from datetime import datetime
from pydantic import BaseModel, field_validator


class CreateSessionRequest(BaseModel):
    user_id: str | None = None
    thread_id: str | None = None

    @field_validator("thread_id")
    @classmethod
    def no_spaces(cls, v):
        if v and " " in v:
            raise ValueError("thread_id must not contain spaces")
        return v


class MessageRequest(BaseModel):
    content: str


class ResumeRequest(BaseModel):
    answer: str


class SessionResponse(BaseModel):
    thread_id: str
    user_id: str
    status: str
    message: str | None = None
    payload: dict | None = None


class ToolCallInfo(BaseModel):
    name: str
    status: str = "success"   # "success" | "error"
    result_preview: str | None = None


class ResumeResponse(BaseModel):
    thread_id: str
    status: str
    message: str | None = None
    payload: dict | None = None
    tool_calls: list[ToolCallInfo] = []


class SessionStateResponse(BaseModel):
    exists: bool
    thread_id: str
    user_id: str | None = None
    status: str | None = None
    messages: list = []
    profile: dict = {}
    pending_question: dict | None = None
    tool_calls: list[ToolCallInfo] = []


class SessionSummary(BaseModel):
    thread_id: str
    user_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
