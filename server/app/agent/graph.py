from langgraph.graph import StateGraph, START, END
from app.agent.subgraphs.intake_subgraph import build_intake_subgraph
from app.agent.subgraphs.market_subgraph import build_market_subgraph
from app.agent.nodes.consent import ask_research_consent_node, parse_research_consent_node
from app.core.logging import get_logger

logger = get_logger(__name__)

_graph = None


def _check_consent(state: dict) -> str:
    """Conditional edge from parse_consent."""
    if state.get("research_consent") is True:
        return "market_subgraph"
    return END


def build_graph(checkpointer):
    builder = StateGraph(dict)

    # 1. Intake Subgraph
    intake_subgraph = build_intake_subgraph()
    builder.add_node("intake_subgraph", intake_subgraph)

    # 2. Consent Nodes
    builder.add_node("ask_research_consent", ask_research_consent_node)
    builder.add_node("parse_research_consent", parse_research_consent_node)

    # 3. Market Subgraph
    market_subgraph = build_market_subgraph()
    builder.add_node("market_subgraph", market_subgraph)

    # Wiring
    builder.add_edge(START, "intake_subgraph")
    
    # After intake finishes, ask for consent
    builder.add_edge("intake_subgraph", "ask_research_consent")
    
    # After user answers the interrupt, parse it
    builder.add_edge("ask_research_consent", "parse_research_consent")
    
    # If consent=True -> market_subgraph, else -> END
    builder.add_conditional_edges("parse_research_consent", _check_consent, {
        "market_subgraph": "market_subgraph",
        END: END
    })
    
    # After market research, end for now (Phase 4 will attach here)
    builder.add_edge("market_subgraph", END)

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
