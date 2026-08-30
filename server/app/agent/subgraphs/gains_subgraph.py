import json
from typing import Annotated, TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages
from app.core.config import get_settings
from app.core.logging import get_logger

from app.agent.tools.calculator import split_investment
from app.agent.state import InvestmentPlan, GainProjection

logger = get_logger(__name__)

tools = [split_investment]

HORIZON_YEARS = {
    "short": 1,
    "medium": 3,
    "long": 7,
}


def _get_llm():
    settings = get_settings()
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
    )


def _serialize_profile(profile) -> str:
    if hasattr(profile, "model_dump"):
        return json.dumps(profile.model_dump(), indent=2)
    return json.dumps(profile if isinstance(profile, dict) else {}, indent=2)


def gains_planner_node(state: dict) -> dict:
    """
    LLM node that reads the user's profile + market research summary,
    then calls split_investment to calculate projected gains across sources.
    """
    profile = state.get("profile", {})
    market = state.get("market", {})
    gains_messages: list[BaseMessage] = list(state.get("gains_messages", []))

    horizon = (
        profile.get("horizon") if isinstance(profile, dict)
        else getattr(profile, "horizon", None)
    ) or "medium"
    years = HORIZON_YEARS.get(horizon, 3)

    investable = (
        profile.get("investable_amount") if isinstance(profile, dict)
        else getattr(profile, "investable_amount", None)
    ) or 0

    risk_tolerance = (
        profile.get("risk_tolerance") if isinstance(profile, dict)
        else getattr(profile, "risk_tolerance", None)
    ) or "medium"

    research_summary = (
        market.get("research_summary") if isinstance(market, dict)
        else getattr(market, "research_summary", None)
    ) or "No market research available."

    system_prompt = (
        "You are Paisaan's Investment Calculator. Your job is to create a concrete investment "
        "allocation plan and calculate projected gains.\n\n"
        f"User Profile:\n{_serialize_profile(profile)}\n\n"
        f"Market Research Summary:\n{research_summary}\n\n"
        f"Investment Horizon: {horizon} term ({years} years)\n"
        f"Total Investable Amount: ₹{investable:,.2f}\n"
        f"Risk Tolerance: {risk_tolerance}\n\n"
        "Instructions:\n"
        "1. Based on the market research data, user's risk tolerance, and preferences, "
        "decide how to split the total investable amount across different investment sources "
        "(stocks, mutual funds, gold/silver, FDs, etc.).\n"
        "2. For each source, determine a realistic annual return rate based on the market "
        "research data. Use actual data from the research — don't make up rates.\n"
        "3. The allocation percentages MUST sum to exactly 100.\n"
        f"4. Call the split_investment tool with total_amount={investable}, years={years}, "
        "and your chosen allocations.\n"
        "5. After receiving the tool result, DO NOT call the tool again. Instead, provide "
        "a clear, conversational summary of the projected gains.\n"
        "6. Include specific sources with realistic expected returns based on the market data."
    )

    llm_with_tools = _get_llm().bind_tools(tools)

    trigger = HumanMessage(
        content="Based on the market research above, create an investment plan and calculate the projected gains."
    )
    messages_to_send = [SystemMessage(content=system_prompt), trigger] + gains_messages

    response = llm_with_tools.invoke(messages_to_send)

    return {"gains_messages": [response]}


def should_continue(state: dict) -> str:
    gains_messages = state.get("gains_messages", [])
    if not gains_messages:
        return END
    last_message = gains_messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "store_plan"


def store_plan_node(state: dict) -> dict:
    """
    Parses the split_investment tool result from gains_messages and stores it
    as a structured InvestmentPlan in state. Does NOT add any chat messages —
    the main graph's consent node will display the plan.
    """
    gains_messages = state.get("gains_messages", [])

    tool_result = None
    for msg in gains_messages:
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                raw = msg.content
                if isinstance(raw, str):
                    tool_result = json.loads(raw)
                elif isinstance(raw, dict):
                    tool_result = raw
            except (json.JSONDecodeError, TypeError):
                pass

    if not tool_result or "allocations" not in tool_result:
        logger.warning("store_plan_node: no valid tool result found in gains_messages")
        return {}

    allocations = [
        GainProjection(
            source=alloc["source"],
            principal=alloc["principal"],
            annual_rate_pct=alloc["annual_rate_pct"],
            years=alloc["years"],
            final_value=alloc["final_value"],
            total_gain=alloc["total_gain"],
        )
        for alloc in tool_result["allocations"]
    ]

    plan = InvestmentPlan(
        allocations=allocations,
        total_principal=tool_result["total_principal"],
        total_final_value=tool_result["total_final_value"],
        total_gain=tool_result["total_gain"],
        years=tool_result["years"],
        summary=None,  # will be filled by consent node from gains_messages LLM text
    )

    logger.info(
        "Investment plan stored: ₹%.2f across %d allocations, %d years",
        plan.total_principal, len(allocations), plan.years,
    )

    return {"investment_plan": plan.model_dump()}


def build_gains_subgraph():
    class _Schema(TypedDict, total=False):
        gains_messages: Annotated[list, add_messages]
        profile: Any
        market: Any
        investment_plan: Any
        messages: list

    builder = StateGraph(_Schema)

    builder.add_node("gains_planner", gains_planner_node)
    builder.add_node("tools", ToolNode(tools, messages_key="gains_messages"))
    builder.add_node("store_plan", store_plan_node)

    builder.add_edge(START, "gains_planner")
    builder.add_conditional_edges("gains_planner", should_continue, {
        "tools": "tools",
        "store_plan": "store_plan",
    })
    builder.add_edge("tools", "gains_planner")
    builder.add_edge("store_plan", END)

    compiled = builder.compile()
    logger.debug("Gains Subgraph compiled (%d nodes)", len(builder.nodes))
    return compiled
