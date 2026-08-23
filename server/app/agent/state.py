"""
AgentState and all sub-models. This is the single source of truth for
graph state across ALL phases. API schemas import from here — never the
other way around.
"""
from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class Profile(BaseModel):
    """Built progressively during the Intake subgraph (Phase 1)."""
    income: float | None = None
    expenses: float | None = None
    existing_savings: float | None = None
    dependents: int | None = None
    goal: str | None = None
    risk_signals: list[str] = Field(default_factory=list)
    intake_complete: bool = False


class MarketSnapshot(BaseModel):
    """Populated during the Market Data subgraph (Phase 2)."""
    mutual_funds: dict = Field(default_factory=dict)
    stocks: dict = Field(default_factory=dict)
    gold_silver: dict = Field(default_factory=dict)
    fd_rates: dict = Field(default_factory=dict)
    # Bounded risk signal — NOT a crash prediction
    news_signal: str | None = None   # "elevated" | "normal" | "low"


class AllocationLine(BaseModel):
    """One line in the draft investment allocation (Phase 4)."""
    asset_class: str
    percent: float
    amount: float
    reasoning: str   # mandatory — tied to planner and audit trail


class AgentState(BaseModel):
    """
    Complete graph state. Persisted to SqliteSaver checkpointer under thread_id.
    Survives closed browser tabs and new HTTP connections.
    """
    thread_id: str
    profile: Profile = Field(default_factory=Profile)
    horizon: str | None = None          # "short" | "medium" | "long"
    market: MarketSnapshot = Field(default_factory=MarketSnapshot)
    draft_allocation: list[AllocationLine] = Field(default_factory=list)
    confirmed: bool = False
    transaction_id: str | None = None

    # Chat message history (uses LangGraph's add_messages reducer)
    # Type annotation here is for documentation; the actual reducer is
    # configured in graph.py via Annotated.
    messages: list = Field(default_factory=list)
