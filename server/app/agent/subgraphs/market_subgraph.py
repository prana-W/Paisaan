import json
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages
from app.core.config import get_settings
from app.core.logging import get_logger
from app.agent.state import AgentState

from app.agent.tools.mutual_fund import get_mutual_fund_nav
from app.agent.tools.stocks import get_stock_price
from app.agent.tools.bullion import get_gold_silver_price
from app.agent.tools.fd_rates import get_fd_rates
from app.agent.tools.news import search_market_news

logger = get_logger(__name__)

tools = [
    get_mutual_fund_nav,
    get_stock_price,
    get_gold_silver_price,
    get_fd_rates,
    search_market_news
]


def _get_llm():
    settings = get_settings()
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
    )


def _serialize_profile(profile) -> str:
    """Safely serialize profile whether it's a dict or a Pydantic model."""
    if hasattr(profile, "model_dump"):
        return json.dumps(profile.model_dump(), indent=2)
    return json.dumps(profile if isinstance(profile, dict) else {}, indent=2)


def researcher_node(state: dict) -> dict:
    """
    LLM node that decides which tools to call based on the user's profile.
    Uses AgentState.research_messages (isolated from intake chat history)
    so the ToolNode can cleanly find the last AIMessage with tool_calls.
    """
    profile = state.get("profile", {})
    preferences = (
        profile.get("investment_preferences", "None specified")
        if isinstance(profile, dict)
        else getattr(profile, "investment_preferences", "None specified") or "None specified"
    )

    research_messages: list[BaseMessage] = list(state.get("research_messages", []))

    system_prompt = (
        "You are a diligent Financial Researcher for Paisaan. Your job is to fetch live market data.\n"
        f"User Profile:\n{_serialize_profile(profile)}\n"
        f"User Preferences: {preferences}\n\n"
        "Instructions:\n"
        "1. You have access to tools for stocks, mutual funds, bullion, FD rates, and news.\n"
        "2. Call the appropriate tools to gather data relevant to the user's profile and preferences. "
        "For example, if they like 'Tata', fetch Tata stock prices. If they are conservative, fetch "
        "FD rates and bullion. You MUST call at least 1 tool.\n"
        "3. Once the tools return their data, synthesize a beautiful, concise markdown summary of "
        "the findings and present it to the user. Do not call tools again after summarizing."
    )

    llm_with_tools = _get_llm().bind_tools(tools)

    # Gemini requires at least one user-turn in contents (SystemMessage alone is not enough).
    trigger = HumanMessage(content="Please research the live market now based on the user profile above.")
    messages_to_send = [SystemMessage(content=system_prompt), trigger] + research_messages

    response = llm_with_tools.invoke(messages_to_send)

    # Return only the new message — add_messages reducer will append it to research_messages
    return {"research_messages": [response]}


def should_continue(state: dict) -> str:
    """Determines whether to call tools or move to the compiler."""
    research_messages = state.get("research_messages", [])
    if not research_messages:
        return "compiler"
    last_message = research_messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "compiler"


def compiler_node(state: dict) -> dict:
    """
    Takes the final LLM summary from research_messages and:
    1. Stores it in market.research_summary
    2. Appends it to the shared `messages` list so the frontend can display it
    """
    research_messages = state.get("research_messages", [])
    main_messages = list(state.get("messages", []))
    market = dict(state.get("market", {}))

    summary = ""
    if research_messages:
        last = research_messages[-1]
        content = last.content
        if isinstance(content, str):
            summary = content
        elif isinstance(content, list):
            # Gemini sometimes returns content as a list of blocks: [{'type': 'text', 'text': '...'}]
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(block.get("text", ""))
            summary = "".join(parts)
        else:
            summary = str(content)

    market["research_summary"] = summary
    main_messages.append({"role": "assistant", "content": summary})

    return {
        "market": market,
        "messages": main_messages,
    }


def build_market_subgraph():
    """
    Build the market research subgraph.
    Uses AgentState as the schema so research_messages gets the add_messages reducer
    and all state keys are unified under state.py — no local TypedDicts needed.
    """
    # We need the add_messages reducer on research_messages.
    # Since AgentState is a Pydantic BaseModel (not a TypedDict), we pass it as a
    # TypedDict-compatible schema by using its __annotations__ with Annotated overrides.
    # The cleanest LangGraph way: use a small TypedDict that re-declares only what needs
    # a reducer, keeping everything else as a plain pass-through.
    from typing import TypedDict, Any

    class _Schema(TypedDict, total=False):
        research_messages: Annotated[list, add_messages]
        profile: Any
        market: Any
        messages: list

    builder = StateGraph(_Schema)

    builder.add_node("researcher", researcher_node)
    builder.add_node("tools", ToolNode(tools, messages_key="research_messages"))
    builder.add_node("compiler", compiler_node)

    builder.add_edge(START, "researcher")
    builder.add_conditional_edges("researcher", should_continue, {
        "tools": "tools",
        "compiler": "compiler"
    })
    builder.add_edge("tools", "researcher")
    builder.add_edge("compiler", END)

    compiled = builder.compile()
    logger.debug("Market Subgraph compiled (%d nodes)", len(builder.nodes))
    return compiled
