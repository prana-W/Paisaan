"""
SqliteSaver checkpointer — module-level singleton.

This is the cornerstone of Phase 0. The checkpointer persists LangGraph
graph state to a SQLite file under a thread_id key. Because state lives
here (not in server memory), the graph can pause via interrupt(), the
FastAPI request can end, and a completely new HTTP connection can resume
the exact same graph execution.

Usage:
    from app.agent.checkpointer import get_checkpointer, graph_lock
    checkpointer = get_checkpointer()
"""
import sqlite3
import threading
from langgraph.checkpoint.sqlite import SqliteSaver
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_checkpointer: SqliteSaver | None = None
_conn: sqlite3.Connection | None = None

# Single-writer lock: SQLite can handle concurrent reads in WAL mode, but
# graph.stream() / graph.invoke() always writes to the checkpoint DB.
# FastAPI runs handlers in a thread pool, so two simultaneous requests can
# both call graph.stream() at the same time → "database is locked".
# This lock serialises all graph operations so only one writes at a time.
graph_lock = threading.Lock()


def get_checkpointer() -> SqliteSaver:
    """
    Return the module-level SqliteSaver singleton.
    Must be called after init_checkpointer() has run (in app lifespan).
    """
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialised. Call init_checkpointer() at app startup."
        )
    return _checkpointer


def init_checkpointer() -> SqliteSaver:
    """
    Create (or open) the SqliteSaver. Call once in FastAPI lifespan startup.
    Returns the checkpointer so callers can store a reference if needed.

    We open the connection manually and pass it to SqliteSaver() so the
    connection stays open for the lifetime of the process (not used as a
    context manager, which would close it on exit).
    """
    global _checkpointer, _conn
    settings = get_settings()

    logger.info("Initialising SqliteSaver checkpointer at %s", settings.checkpoint_db_path)

    # Open a persistent connection. timeout=30 makes sqlite3 wait up to 30s
    # for a write lock before raising OperationalError (last-resort safety net
    # on top of the graph_lock above).
    _conn = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False,
        timeout=30,
    )
    _conn.execute("PRAGMA journal_mode=WAL;")
    _conn.execute("PRAGMA busy_timeout=10000;")  # 10s at the SQLite level
    _conn.commit()
    _checkpointer = SqliteSaver(_conn)

    return _checkpointer
