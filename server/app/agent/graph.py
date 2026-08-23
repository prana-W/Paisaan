from langgraph.graph import StateGraph, START, END
from app.agent.subgraphs.intake_subgraph import build_intake_subgraph
from app.core.logging import get_logger

logger = get_logger(__name__)

_graph = None


def build_graph(checkpointer):
    builder = StateGraph(dict)

    intake_subgraph = build_intake_subgraph()
    
    # Register the subgraph as a single node in the main graph
    builder.add_node("intake_subgraph", intake_subgraph)

    builder.add_edge(START, "intake_subgraph")
    builder.add_edge("intake_subgraph", END)

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
