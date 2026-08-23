from langgraph.graph import StateGraph, START, END
from app.agent.nodes.intake import intake_node
from app.core.logging import get_logger

logger = get_logger(__name__)

def _check_intake_done(state: dict) -> str:
    """
    Conditional edge logic to determine if the intake subgraph should loop
    back to the intake node or finish and return to the parent graph.
    """
    return "done" if state.get("profile", {}).get("intake_complete") else "continue"

def build_intake_subgraph():
    """
    Builds and compiles the Intake Subgraph.
    This graph loops internally until the user's financial profile is fully gathered.
    """
    builder = StateGraph(dict)

    builder.add_node("intake", intake_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", _check_intake_done, {
        "continue": "intake",
        "done": END,
    })

    compiled = builder.compile()
    logger.debug("Intake Subgraph compiled (%d nodes)", len(builder.nodes))
    return compiled
