import uuid
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.db.models import User, Session as SessionModel, Investment, Transaction, Wallet


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
        db.delete(session)
        db.commit()
        return True
    return False


def update_session_status(db: DBSession, thread_id: str, status: str) -> None:
    session = get_session(db, thread_id)
    if session:
        session.status = status
        db.commit()


# ── Wallet ────────────────────────────────────────────────────────────────────

def _get_or_create_wallet(db: DBSession) -> Wallet:
    """Always returns the single wallet row (id=1), creating it if absent."""
    wallet = db.query(Wallet).filter(Wallet.id == 1).first()
    if not wallet:
        wallet = Wallet(id=1, balance=0.0, last_updated=datetime.utcnow())
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def get_wallet_balance(db: DBSession) -> float:
    """Return current wallet balance in ₹."""
    return _get_or_create_wallet(db).balance


def add_to_wallet(db: DBSession, amount: float) -> float:
    """Credit `amount` to wallet, return new balance."""
    wallet = _get_or_create_wallet(db)
    wallet.balance = round(wallet.balance + amount, 2)
    wallet.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(wallet)
    return wallet.balance


def deduct_from_wallet(db: DBSession, amount: float) -> float:
    """
    Debit `amount` from wallet, return new balance.
    Raises ValueError if insufficient funds.
    """
    wallet = _get_or_create_wallet(db)
    if wallet.balance < amount:
        raise ValueError(
            f"Insufficient wallet balance: have ₹{wallet.balance:.2f}, need ₹{amount:.2f}"
        )
    wallet.balance = round(wallet.balance - amount, 2)
    wallet.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(wallet)
    return wallet.balance


# ── Investments ───────────────────────────────────────────────────────────────

def create_investment(
    db: DBSession,
    user_id: str,
    thread_id: str,
    source: str,
    asset_type: str,
    principal: float,
    annual_rate_pct: float,
    years: int,
    notes: str | None = None,
) -> Investment:
    """Persist a new investment made by the AI agent."""
    investment = Investment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        thread_id=thread_id,
        source=source,
        asset_type=asset_type,
        principal=round(principal, 2),
        annual_rate_pct=annual_rate_pct,
        years=years,
        current_value=round(principal, 2),  # starts equal to principal
        last_updated=datetime.utcnow(),
        bought_at=datetime.utcnow(),
        notes=notes,
    )
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


def get_all_investments(db: DBSession) -> list[Investment]:
    """Return all investments ordered by purchase date descending."""
    return db.query(Investment).order_by(Investment.bought_at.desc()).all()


# ── Transactions ──────────────────────────────────────────────────────────────

def log_transaction(
    db: DBSession,
    user_id: str,
    action: str,
    amount: float,
    status: str,
    reasoning: str,
) -> Transaction:
    """Append a row to the immutable audit log."""
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
