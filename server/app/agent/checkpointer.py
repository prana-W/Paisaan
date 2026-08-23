"""
PostgresSaver checkpointer — module-level singleton.

This checkpointer persists LangGraph graph state to a PostgreSQL database
under a thread_id key. Because state lives here (not in server memory),
the graph can pause via interrupt(), the FastAPI request can end, and a
completely new HTTP connection can resume the exact same graph execution.

Usage:
    from app.agent.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()
"""
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_checkpointer: PostgresSaver | None = None
_pool: ConnectionPool | None = None


def get_checkpointer() -> PostgresSaver:
    """
    Return the module-level PostgresSaver singleton.
    Must be called after init_checkpointer() has run (in app lifespan).
    """
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialised. Call init_checkpointer() at app startup."
        )
    return _checkpointer


def init_checkpointer() -> PostgresSaver:
    """
    Create (or open) the PostgresSaver. Call once in FastAPI lifespan startup.
    Returns the checkpointer so callers can store a reference if needed.

    We open a connection pool and pass it to PostgresSaver. The pool stays
    open for the lifetime of the process.
    """
    global _checkpointer, _pool
    settings = get_settings()

    logger.info("Initialising PostgresSaver checkpointer at %s", settings.checkpoint_db_url)

    _pool = ConnectionPool(
        conninfo=settings.checkpoint_db_url,
        max_size=20,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
        }
    )
    _pool.open()
    
    _checkpointer = PostgresSaver(_pool)
    _checkpointer.setup()  # Creates the necessary tables automatically if they don't exist

    return _checkpointer
