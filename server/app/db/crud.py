import uuid
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.db.models import User, Session as SessionModel, Holding, Transaction


# ── Users ────────────────────────────────────────────────────────────────────

def get_or_create_user(db: DBSession, user_id: str | None = None) -> User:
    """Return existing user by id, or create an anonymous one."""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    user = User(id=user_id or str(uuid.uuid4()), created_at=datetime.utcnow())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(db: DBSession, user_id: str, thread_id: str) -> SessionModel:
    """Create a new planning session linked to a LangGraph thread_id."""
    existing = get_session(db, thread_id)
    if existing:
        return existing
    session = SessionModel(
        id=thread_id,           # use thread_id as session pk for simplicity
        user_id=user_id,
        thread_id=thread_id,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, thread_id: str) -> SessionModel | None:
    return db.query(SessionModel).filter(SessionModel.thread_id == thread_id).first()


def get_sessions(db: DBSession, user_id: str | None = None) -> list[SessionModel]:
    query = db.query(SessionModel)
    if user_id:
        query = query.filter(SessionModel.user_id == user_id)
    return query.order_by(SessionModel.created_at.desc()).all()


def delete_session(db: DBSession, thread_id: str) -> bool:
    session = db.query(SessionModel).filter(SessionModel.thread_id == thread_id).first()
    if session:
        # Delete associated holdings
        db.query(Holding).filter(Holding.thread_id == thread_id).delete()
        db.delete(session)
        db.commit()
        return True
    return False


def update_session_status(db: DBSession, thread_id: str, status: str) -> None:
    session = get_session(db, thread_id)
    if session:
        session.status = status
        db.commit()


# ── Holdings ─────────────────────────────────────────────────────────────────
# Phase 6 — stubbed

def create_holding(db: DBSession, **kwargs) -> Holding:
    """Phase 6: persist a mock asset purchase."""
    raise NotImplementedError("Holdings persistence is implemented in Phase 6")


def get_holdings(db: DBSession, user_id: str) -> list[Holding]:
    """Phase 7: return all holdings for a user."""
    return db.query(Holding).filter(Holding.user_id == user_id).all()


# ── Transactions ──────────────────────────────────────────────────────────────
# Append-only audit log — Phase 6

def log_transaction(
    db: DBSession,
    user_id: str,
    action: str,
    amount: float,
    status: str,
    reasoning: str,
) -> Transaction:
    """Phase 6: append a row to the immutable audit log."""
    txn = Transaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        amount=amount,
        status=status,
        reasoning=reasoning,
        created_at=datetime.utcnow(),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
