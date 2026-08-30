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
    user_answer = _extract_content(messages[-1]) if messages else ""
    return {**state, "research_consent": _parse_user_consent(user_answer)}


def _check_research_consent(state: dict) -> str:
    if state.get("research_consent") is True:
        return "market_subgraph"
    return END


# ── Gains consent (after showing research, before gains calculation) ─────────


def ask_gains_consent_node(state: dict) -> dict:
    messages = list(state.get("messages", []))
    market = state.get("market", {})

    summary = (
        market.get("research_summary") if isinstance(market, dict)
        else getattr(market, "research_summary", None)
    ) or "Market research complete (no details provided)."

    question = (
        f"{summary}\n\n"
        "---\n"
        "**Now I can calculate projected gains on your investment based on this market data.**\n"
        "**Shall I crunch the numbers and show you a detailed investment plan?**"
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
    messages = state.get("messages", [])[:]
    user_answer = _extract_content(messages[-1]) if messages else ""
    return {**state, "gains_consent": _parse_user_consent(user_answer)}


def _check_gains_consent(state: dict) -> str:
    if state.get("gains_consent") is True:
        return "gains_subgraph"
    return END


# ── Payment consent (after gains subgraph stores the plan) ───────────────────

def _build_plan_markdown(investment_plan: dict) -> str:
    """Build a rich markdown representation of the stored investment plan."""
    if not investment_plan or not investment_plan.get("allocations"):
        return "_No investment plan available._"

    lines = [
        "## 📊 Your Investment Plan\n",
        f"**Total Investment:** ₹{investment_plan['total_principal']:,.2f}",
        f"**Investment Duration:** {investment_plan['years']} years",
        f"**Projected Final Value:** ₹{investment_plan['total_final_value']:,.2f}",
        f"**Total Projected Gain:** ₹{investment_plan['total_gain']:,.2f}\n",
        "### Allocation Breakdown\n",
        "| Source | Investment (₹) | Holding | Final Value (₹) | Gain (₹) |",
        "|--------|---------------|---------|-----------------|----------|",
    ]

    for alloc in investment_plan["allocations"]:
        holding_display = alloc.get("holding") or f"{alloc.get('annual_rate_pct', 0)}% p.a."
        lines.append(
            f"| {alloc['source']} "
            f"| {alloc['principal']:,.2f} "
            f"| {holding_display} "
            f"| {alloc['final_value']:,.2f} "
            f"| {alloc['total_gain']:,.2f} |"
        )

    return "\n".join(lines)


def show_plan_and_ask_payment_consent_node(state: dict) -> dict:
    """
    Displays the investment plan (stored in state by gains_subgraph) and
    asks the user for consent to proceed with the actual purchase.
    Single interrupt — plan + question in one message.
    """
    messages = list(state.get("messages", []))
    investment_plan = state.get("investment_plan", {})

    # Handle both dict and Pydantic object
    if hasattr(investment_plan, "model_dump"):
        investment_plan = investment_plan.model_dump()

    plan_md = _build_plan_markdown(investment_plan)

    question = (
        f"{plan_md}\n\n"
        "---\n"
        "**I'm ready to execute this investment plan on your behalf using your wallet balance.**\n\n"
        "Shall I go ahead and make these investments? "
        "*(Your wallet will be debited by ₹"
        f"{investment_plan.get('total_principal', 0):,.2f})*"
    )

    answer = interrupt({"type": "question", "text": question})

    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": question},
            {"role": "user", "content": str(answer)},
        ],
    }


def parse_payment_consent_node(state: dict) -> dict:
    messages = state.get("messages", [])
    user_answer = _extract_content(messages[-1]) if messages else ""
    return {**state, "payment_consent": _parse_user_consent(user_answer)}


def _check_payment_consent(state: dict) -> str:
    if state.get("payment_consent") is True:
        return "payment_subgraph"
    return "conclusion_node"


# ── Conclusion node (final message after investment OR after declined consent) ─

def conclusion_node(state: dict) -> dict:
    """Sends the final message to the user and ends the workflow."""
    messages = list(state.get("messages", []))
    investment_executed = state.get("investment_executed", False)
    investment_plan = state.get("investment_plan", {})

    if hasattr(investment_plan, "model_dump"):
        investment_plan = investment_plan.model_dump()

    if investment_executed and investment_plan.get("allocations"):
        # Build success message
        lines = [
            "## ✅ Investments Successfully Made!\n",
            "Your investment plan has been executed. Here's what was purchased:\n",
        ]
        for alloc in investment_plan["allocations"]:
            holding_display = alloc.get("holding") or f"{alloc.get('annual_rate_pct', 0)}% p.a."
            lines.append(f"- **{alloc['source']}** — ₹{alloc['principal']:,.2f} ({holding_display})")
        lines.extend([
            f"\n**Total Invested:** ₹{investment_plan['total_principal']:,.2f}",
            f"**Projected Value in {investment_plan['years']} years:** ₹{investment_plan['total_final_value']:,.2f}",
            f"**Projected Gain:** ₹{investment_plan['total_gain']:,.2f}\n",
            "You can track all your investments in the **Portfolio** tab. "
            "Your wallet has been debited accordingly. 🎉",
        ])
        final_msg = "\n".join(lines)
    else:
        # User declined payment
        final_msg = (
            "No problem! Your investment plan has been saved for reference but no funds have been moved. "
            "Whenever you're ready to invest, feel free to start a new session. "
            "Your wallet balance remains unchanged. 😊"
        )

    messages.append({"role": "assistant", "content": final_msg})
    return {**state, "messages": messages}


from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class MainState(TypedDict, total=False):
    thread_id: str
    profile: Any
    market: Any
    investment_plan: Any
    research_consent: bool | None
    gains_consent: bool | None
    payment_consent: bool | None
    draft_allocation: list
    confirmed: bool
    transaction_id: str | None
    investment_executed: bool
    messages: Annotated[list, add_messages]
    research_messages: Annotated[list, add_messages]
    gains_messages: Annotated[list, add_messages]


# ── Graph builder ───────────────────────────────────────────────────────────


def build_graph(checkpointer):
    from app.agent.subgraphs.payment_subgraph import build_payment_subgraph

    builder = StateGraph(MainState)

    # Nodes
    builder.add_node("intake_subgraph", build_intake_subgraph())
    builder.add_node("ask_research_consent", ask_research_consent_node)
    builder.add_node("parse_research_consent", parse_research_consent_node)
    builder.add_node("market_subgraph", build_market_subgraph())
    builder.add_node("ask_gains_consent", ask_gains_consent_node)
    builder.add_node("parse_gains_consent", parse_gains_consent_node)
    builder.add_node("gains_subgraph", build_gains_subgraph())
    builder.add_node("show_plan_and_ask_payment_consent", show_plan_and_ask_payment_consent_node)
    builder.add_node("parse_payment_consent", parse_payment_consent_node)
    builder.add_node("payment_subgraph", build_payment_subgraph())
    builder.add_node("conclusion_node", conclusion_node)

    # Wiring
    builder.add_edge(START, "intake_subgraph")
    builder.add_edge("intake_subgraph", "ask_research_consent")
    builder.add_edge("ask_research_consent", "parse_research_consent")

    builder.add_conditional_edges("parse_research_consent", _check_research_consent, {
        "market_subgraph": "market_subgraph",
        END: END,
    })

    builder.add_edge("market_subgraph", "ask_gains_consent")
    builder.add_edge("ask_gains_consent", "parse_gains_consent")

    builder.add_conditional_edges("parse_gains_consent", _check_gains_consent, {
        "gains_subgraph": "gains_subgraph",
        END: END,
    })

    builder.add_edge("gains_subgraph", "show_plan_and_ask_payment_consent")
    builder.add_edge("show_plan_and_ask_payment_consent", "parse_payment_consent")

    builder.add_conditional_edges("parse_payment_consent", _check_payment_consent, {
        "payment_subgraph": "payment_subgraph",
        "conclusion_node": "conclusion_node",
    })

    builder.add_edge("payment_subgraph", "conclusion_node")
    builder.add_edge("conclusion_node", END)

    compiled = builder.compile(checkpointer=checkpointer)
    try:
        with open("paisaan_agent_mermaid.mmd", "w") as f:
            f.write(compiled.get_graph(xray=True).draw_mermaid())
    except Exception as e:
        logger.warning("Could not generate mermaid diagram: %s", e)

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
