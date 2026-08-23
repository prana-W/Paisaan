"""
Phase 0 placeholder nodes. These have no real business logic — they exist
solely to prove the interrupt() → FastAPI response → /resume → continued
execution round-trip. Real nodes replace these in later phases.
"""
from langgraph.types import interrupt
from app.core.logging import get_logger

logger = get_logger(__name__)


def intake_node(state: dict) -> dict:
    """
    Phase 0 stub: asks the first question via interrupt().

    In Phase 1 this becomes the self-looping dynamic Q&A node that inspects
    the Profile and decides what to ask next.
    """
    logger.debug("[intake_node] thread_id=%s entering", state.get("thread_id"))

    # interrupt() pauses graph execution here. FastAPI returns this payload to
    # the frontend. The graph is serialised to the checkpointer DB. The HTTP
    # request ends normally.
    answer = interrupt({
        "type": "question",
        "node": "intake",
        "text": "Welcome to Paisaan! To get started, what is your approximate monthly income (in ₹)?",
    })

    logger.debug("[intake_node] resumed with answer=%r", answer)

    # Store the answer on state (Phase 1 will parse this properly into Profile)
    messages = state.get("messages", [])
    messages = messages + [{"role": "user", "content": str(answer)}]

    return {
        **state,
        "messages": messages,
    }


def complete_node(state: dict) -> dict:
    """
    Phase 0 stub: marks the session done and returns a confirmation message.

    In Phase 4 this becomes the planner node that produces draft_allocation.
    """
    logger.debug("[complete_node] thread_id=%s completing session", state.get("thread_id"))

    messages = state.get("messages", [])
    messages = messages + [{
        "role": "assistant",
        "content": (
            "✅ Phase 0 round-trip verified! Your answer was received and the graph "
            "resumed successfully from the checkpointer. Session complete."
        ),
    }]

    return {
        **state,
        "messages": messages,
        "confirmed": True,
    }
