from langgraph.graph import StateGraph, START, END
from app.agent.nodes.intake import intake_node
from app.core.logging import get_logger

logger = get_logger(__name__)

_graph = None


def _check_intake_done(state: dict) -> str:
    return "done" if state.get("profile", {}).get("intake_complete") else "continue"


def build_graph(checkpointer):
    builder = StateGraph(dict)

    builder.add_node("intake", intake_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", _check_intake_done, {
        "continue": "intake",
        "done": END,
    })

    compiled = builder.compile(checkpointer=checkpointer)
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
