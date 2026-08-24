import json
from langgraph.graph import StateGraph, START, END
from app.agent.subgraphs.intake_subgraph import build_intake_subgraph
from app.agent.subgraphs.market_subgraph import build_market_subgraph
from app.agent.subgraphs.gains_subgraph import build_gains_subgraph
from app.core.logging import get_logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from app.core.config import get_settings

logger = get_logger(__name__)

_graph = None


class ConsentResult(BaseModel):
    consent: bool = Field(description="True if the user agreed/consented, False otherwise.")


def _get_llm(structured: bool = False, output_schema=None):
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
    )
    if structured and output_schema:
        return llm.with_structured_output(output_schema)
    return llm


def _parse_user_consent(user_answer: str) -> bool:
    """Shared helper — uses LLM to parse natural language yes/no into a boolean."""
    system = SystemMessage(content=(
        "Determine if the user's response indicates consent to proceed. "
        "Responses like 'yes', 'yep', 'go for it', 'sure', 'yeah' should be True. "
        "Responses like 'no', 'stop', 'wait' should be False."
    ))
    human = HumanMessage(content=f"User response: '{user_answer}'")
    llm = _get_llm(structured=True, output_schema=ConsentResult)
    result = llm.invoke([system, human])
    logger.info(f"Parsed consent as: {result.consent} from answer: '{user_answer}'")
    return result.consent


def _extract_content(msg) -> str:
    """Extract text content from a LangChain message (handles str and list-of-blocks)."""
    content = msg.content if hasattr(msg, "content") else str(msg)
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


# ── Research consent (after intake, before market research) ──────────────────

def ask_research_consent_node(state: dict) -> dict:
    messages = list(state.get("messages", []))

    question = (
        "I've got a great picture of your financial profile and preferences! "
        "Shall I proceed with scanning the live markets to fetch relevant data for you?"
    )

    answer = interrupt({"type": "question", "text": question})

    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": question},
            {"role": "user", "content": str(answer)},
        ],
    }


def parse_research_consent_node(state: dict) -> dict:
    messages = state.get("messages", [])
    user_answer = messages[-1]["content"] if messages else ""
    return {**state, "research_consent": _parse_user_consent(user_answer)}


def _check_research_consent(state: dict) -> str:
    if state.get("research_consent") is True:
        return "market_subgraph"
    return END


# ── Show market research to user ────────────────────────────────────────────

def show_research_node(state: dict) -> dict:
    """Extracts market.research_summary and adds it to messages for the frontend."""
    market = state.get("market", {})
    messages = list(state.get("messages", []))

    summary = (
        market.get("research_summary") if isinstance(market, dict)
        else getattr(market, "research_summary", None)
    ) or "Market research complete."

    messages.append({"role": "assistant", "content": summary})

    return {**state, "messages": messages}


# ── Gains consent (after showing research, before gains calculation) ─────────

def ask_gains_consent_node(state: dict) -> dict:
    messages = list(state.get("messages", []))

    question = (
        "Now I can calculate projected gains on your investment based on this market data. "
        "Shall I crunch the numbers and show you a detailed investment plan?"
    )

    answer = interrupt({"type": "question", "text": question})

    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": question},
            {"role": "user", "content": str(answer)},
        ],
    }


def parse_gains_consent_node(state: dict) -> dict:
    messages = state.get("messages", [])
    user_answer = messages[-1]["content"] if messages else ""
    return {**state, "gains_consent": _parse_user_consent(user_answer)}


def _check_gains_consent(state: dict) -> str:
    if state.get("gains_consent") is True:
        return "gains_subgraph"
    return END


# ── Show gains results to user ──────────────────────────────────────────────

def show_gains_node(state: dict) -> dict:
    """
    Extracts the detailed gains results from gains_messages (tool call results + LLM summary)
    and adds a comprehensive message to the chat for the frontend.
    """
    gains_messages = state.get("gains_messages", [])
    messages = list(state.get("messages", []))

    # Extract the split_investment tool result for detailed data
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

    # Extract the LLM's final conversational summary
    llm_summary = ""
    for msg in reversed(gains_messages):
        if hasattr(msg, "type") and msg.type == "ai":
            if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                llm_summary = _extract_content(msg)
                break

    # Build a detailed markdown message
    parts = []

    if tool_result and "allocations" in tool_result:
        parts.append("## 📊 Your Investment Plan\n")
        parts.append(f"**Total Investment:** ₹{tool_result['total_principal']:,.2f}")
        parts.append(f"**Investment Duration:** {tool_result['years']} years")
        parts.append(f"**Projected Final Value:** ₹{tool_result['total_final_value']:,.2f}")
        parts.append(f"**Total Projected Gain:** ₹{tool_result['total_gain']:,.2f} "
                      f"({tool_result.get('total_gain_pct', 0):.1f}%)\n")

        parts.append("### Allocation Breakdown\n")
        parts.append("| Source | Investment (₹) | Annual Rate | Final Value (₹) | Gain (₹) | Gain % |")
        parts.append("|--------|---------------|-------------|-----------------|----------|--------|")
        for alloc in tool_result["allocations"]:
            parts.append(
                f"| {alloc['source']} "
                f"| {alloc['principal']:,.2f} "
                f"| {alloc['annual_rate_pct']}% "
                f"| {alloc['final_value']:,.2f} "
                f"| {alloc['total_gain']:,.2f} "
                f"| {alloc['gain_pct']}% |"
            )
        parts.append("")

    if llm_summary:
        parts.append("### Analysis\n")
        parts.append(llm_summary)

    detailed_message = "\n".join(parts) if parts else "Investment plan calculation complete."
    messages.append({"role": "assistant", "content": detailed_message})

    return {**state, "messages": messages}


# ── Graph builder ───────────────────────────────────────────────────────────

def build_graph(checkpointer):
    builder = StateGraph(dict)

    # Nodes
    builder.add_node("intake_subgraph", build_intake_subgraph())
    builder.add_node("ask_research_consent", ask_research_consent_node)
    builder.add_node("parse_research_consent", parse_research_consent_node)
    builder.add_node("market_subgraph", build_market_subgraph())
    builder.add_node("show_research", show_research_node)
    builder.add_node("ask_gains_consent", ask_gains_consent_node)
    builder.add_node("parse_gains_consent", parse_gains_consent_node)
    builder.add_node("gains_subgraph", build_gains_subgraph())
    builder.add_node("show_gains", show_gains_node)

    # Wiring
    builder.add_edge(START, "intake_subgraph")
    builder.add_edge("intake_subgraph", "ask_research_consent")
    builder.add_edge("ask_research_consent", "parse_research_consent")

    builder.add_conditional_edges("parse_research_consent", _check_research_consent, {
        "market_subgraph": "market_subgraph",
        END: END,
    })

    builder.add_edge("market_subgraph", "show_research")
    builder.add_edge("show_research", "ask_gains_consent")
    builder.add_edge("ask_gains_consent", "parse_gains_consent")

    builder.add_conditional_edges("parse_gains_consent", _check_gains_consent, {
        "gains_subgraph": "gains_subgraph",
        END: END,
    })

    builder.add_edge("gains_subgraph", "show_gains")
    builder.add_edge("show_gains", END)

    compiled = builder.compile(checkpointer=checkpointer)
    print(compiled.get_graph().draw_mermaid())

    logger.info("Graph compiled (%d nodes)", len(builder.nodes))
    return compiled


def get_graph():
    if _graph is None:
        raise RuntimeError("Graph not initialised. Call init_graph() at app startup.")
    return _graph


def init_graph(checkpointer) -> None:
    global _graph
    _graph = build_graph(checkpointer)
    logger.info("Agent graph initialised")
