from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import session, wallet
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import init_db
from app.agent.checkpointer import init_checkpointer
from app.agent.graph import init_graph


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    setup_logging()

    logger.info("═══ Paisaan server starting ═══")

    logger.info("Initialising database...")
    init_db()

    logger.info("Initialising LangGraph checkpointer...")
    checkpointer = init_checkpointer()

    logger.info("Compiling agent graph...")
    init_graph(checkpointer)

    logger.info("═══ Paisaan server ready on port %s ═══", get_settings().port)

    yield

    logger.info("═══ Paisaan server shutting down ═══")

settings = get_settings()

app = FastAPI(
    title="Paisaan API",
    description="Personal Investment Agent — simulation only, no real money.",
    version="0.1.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception occurred during request: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

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


# Include routers
app.include_router(session.router, prefix="/api/v1", tags=["Session"])
app.include_router(wallet.router, prefix="/api/v1", tags=["Wallet"])


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "paisaan-api", "version": "0.1.0"}
