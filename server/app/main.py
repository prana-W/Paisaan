"""
FastAPI application entry point.

Startup sequence (lifespan):
  1. setup_logging()
  2. init_db()           — creates SQLite tables
  3. init_checkpointer() — opens SqliteSaver connection
  4. init_graph()        — compiles LangGraph graph with checkpointer

All four steps must complete before any request is served.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import init_db
from app.agent.checkpointer import init_checkpointer
from app.agent.graph import init_graph
from app.api.routes.session import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    setup_logging()
    logger = get_logger(__name__)

    logger.info("═══ Paisaan server starting ═══")

    # 1. DB tables
    logger.info("Initialising database...")
    init_db()

    # 2. Checkpointer (state persistence across requests)
    logger.info("Initialising LangGraph checkpointer...")
    checkpointer = init_checkpointer()

    # 3. Compile agent graph
    logger.info("Compiling agent graph...")
    init_graph(checkpointer)

    logger.info("═══ Paisaan server ready on port %s ═══", get_settings().port)

    yield  # ← application runs here

    logger.info("═══ Paisaan server shutting down ═══")


# ── App ───────────────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Paisaan API",
    description="Personal Investment Agent — simulation only, no real money.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        settings.frontend_url.replace("localhost", "127.0.0.1"),
        settings.frontend_url.replace("127.0.0.1", "localhost")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(session_router, prefix="/api/v1", tags=["session"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "paisaan-api", "version": "0.1.0"}
