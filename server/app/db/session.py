from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from collections.abc import Generator
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    # SQLite needs this for multi-threaded use (FastAPI runs in a thread pool)
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.is_dev,  # Log SQL in dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once at app startup."""
    from app.db.models import Base  # noqa: F401 — import needed to register models
    Base.metadata.create_all(bind=engine)
