"""
Phase 0 graph — skeleton only.

The ONLY purpose of this graph is to prove the interrupt/resume round-trip:
  1. POST /session        → graph starts → intake_node hits interrupt() → state
                            saved to SqliteSaver → FastAPI returns the question
  2. POST /session/{id}/resume → graph resumes from checkpointer → complete_node
                            runs → session done

No real LLM calls, no market data, no allocation in this phase.
"""
from langgraph.graph import StateGraph, START, END
from app.agent.nodes.placeholder import intake_node, complete_node
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Graph definition ──────────────────────────────────────────────────────────

def build_graph(checkpointer):
    """
    Build and compile the Phase 0 graph with the given checkpointer.
    Called once at startup; the compiled graph is stored as a module-level var.

    The checkpointer is injected (not imported here) so this function stays
    testable in isolation.
    """
    builder = StateGraph(dict)   # Phase 0 uses plain dict state

    builder.add_node("intake", intake_node)
    builder.add_node("complete", complete_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "complete")
    builder.add_edge("complete", END)

    compiled = builder.compile(checkpointer=checkpointer, interrupt_before=["complete"])

    logger.info("Phase 0 graph compiled with %d nodes", len(builder.nodes))
    return compiled


# ── Module-level compiled graph (initialised in app lifespan) ─────────────────

_graph = None


def get_graph():
    """Return the compiled graph. Must be called after init_graph()."""
    if _graph is None:
        raise RuntimeError("Graph not initialised. Call init_graph() at app startup.")
    return _graph


def init_graph(checkpointer) -> None:
    """Compile and store the graph. Called once in FastAPI lifespan."""
    global _graph
    _graph = build_graph(checkpointer)
    logger.info("Agent graph initialised")
