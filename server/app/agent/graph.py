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
    messages = state.get("messages", [])
    user_answer = messages[-1]["content"] if messages else ""
    return {**state, "gains_consent": _parse_user_consent(user_answer)}


def _check_gains_consent(state: dict) -> str:
    if state.get("gains_consent") is True:
        return "gains_subgraph"
    return END


# ── Graph builder ───────────────────────────────────────────────────────────


def build_graph(checkpointer):
    builder = StateGraph(dict)

    # Nodes
    builder.add_node("intake_subgraph", build_intake_subgraph())
    builder.add_node("ask_research_consent", ask_research_consent_node)
    builder.add_node("parse_research_consent", parse_research_consent_node)
    builder.add_node("market_subgraph", build_market_subgraph())
    builder.add_node("ask_gains_consent", ask_gains_consent_node)
    builder.add_node("parse_gains_consent", parse_gains_consent_node)
    builder.add_node("gains_subgraph", build_gains_subgraph())

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

    builder.add_edge("gains_subgraph", END)

    compiled = builder.compile(checkpointer=checkpointer)
    with open("paisaan_agent_mermaid.mmd", "w") as f:
        f.write(compiled.get_graph(xray=True).draw_mermaid())

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
