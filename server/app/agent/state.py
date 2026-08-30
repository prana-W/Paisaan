"""
AgentState and all sub-models. This is the single source of truth for
graph state across ALL phases. API schemas import from here — never the
other way around.
"""
from typing import Annotated, Literal, Any
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class Profile(BaseModel):
    age: int | None = Field(default=None, description="Age in years", json_schema_extra={"intake_required": True})
    income: float | None = Field(default=None, description="Monthly income in ₹", json_schema_extra={"intake_required": True})
    expenses: float | None = Field(default=None, description="Monthly expenses in ₹", json_schema_extra={"intake_required": True})
    existing_savings: float | None = Field(default=None, description="Total existing savings/investments in ₹", json_schema_extra={"intake_required": True})
    dependents: int | None = Field(default=None, description="Number of financial dependents", json_schema_extra={"intake_required": True})
    investable_amount: float | None = Field(default=None, description="Lump sum amount available to invest now in ₹", json_schema_extra={"intake_required": True})
    risk_tolerance: Literal["low", "medium", "high"] | None = Field(default=None, description="Risk tolerance — low, medium, or high", json_schema_extra={"intake_required": True})
    goal: str | None = Field(default=None, description="Primary investment goal", json_schema_extra={"intake_required": True})
    investment_preferences: str | None = Field(default=None, description="User's specific investment preferences, favorite stocks, sectors, or mutual funds", json_schema_extra={"intake_required": True})
    horizon: Literal["short", "medium", "long"] | None = Field(default=None, description="Investment horizon — short (< 1 year), medium (1-5 years), or long (5+ years)", json_schema_extra={"intake_required": True})
    risk_signals: list[str] = Field(default_factory=list, description="Raw risk concerns noted during intake")
    questions_asked: list[str] = Field(default_factory=list, description="Questions already asked, to avoid repetition")
    intake_complete: bool = False


class MarketSnapshot(BaseModel):
    """Populated during the Market Data subgraph (Phase 2)."""
    mutual_funds: dict = Field(default_factory=dict)
    stocks: dict = Field(default_factory=dict)
    gold_silver: dict = Field(default_factory=dict)
    fd_rates: dict = Field(default_factory=dict)
    # Bounded risk signal — NOT a crash prediction
    news_signal: str | None = None   # "elevated" | "normal" | "low"
    research_summary: str | None = None


class GainProjection(BaseModel):
    """Projected gain for a single investment source."""
    source: str
    principal: float
    holding: str = ""
    annual_rate_pct: float = 0.0
    years: int
    final_value: float
    total_gain: float


class InvestmentPlan(BaseModel):
    """Complete investment plan with gains from all sources."""
    allocations: list[GainProjection] = Field(default_factory=list)
    total_principal: float = 0.0
    total_final_value: float = 0.0
    total_gain: float = 0.0
    years: int = 0
    summary: str | None = None


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
    user_id: str | None = None
    profile: Profile = Field(default_factory=Profile)
    market: MarketSnapshot = Field(default_factory=MarketSnapshot)
    investment_plan: InvestmentPlan = Field(default_factory=InvestmentPlan)
    research_consent: bool | None = None
    gains_consent: bool | None = None
    payment_consent: bool | None = None
    draft_allocation: list[AllocationLine] = Field(default_factory=list)
    confirmed: bool = False
    transaction_id: str | None = None
    investment_executed: bool = False

    # Chat message history (uses LangGraph's add_messages reducer)
    # Type annotation here is for documentation; the actual reducer is
    # configured in graph.py via Annotated.
    messages: list = Field(default_factory=list)

    # Isolated tool-calling history used exclusively by the market_subgraph researcher.
    # Kept separate from `messages` so the ToolNode never has to search through
    # the intake conversation to find the last AIMessage with tool_calls.
    research_messages: list[Any] = Field(default_factory=list)

    # Isolated tool-calling history for the gains calculation subgraph.
    gains_messages: list[Any] = Field(default_factory=list)

