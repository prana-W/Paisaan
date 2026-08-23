from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """A Paisaan user. Created on first session."""
    __tablename__ = "users"

    id = Column(String, primary_key=True)          # UUID
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sessions = relationship("Session", back_populates="user")
    holdings = relationship("Holding", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


class Session(Base):
    """One investment planning session. Maps 1:1 with a LangGraph thread_id."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)           # UUID — same as thread_id
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")       # active | interrupted | complete
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")


class Holding(Base):
    """A mock asset 'purchased' by the agent for the user."""
    __tablename__ = "holdings"

    id = Column(String, primary_key=True)           # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, nullable=False)      # which session bought this
    asset_type = Column(String, nullable=False)     # equity | mutual_fund | gold | fd
    symbol = Column(String, nullable=False)         # ticker / fund code / "GOLD" etc.
    amount_invested = Column(Float, nullable=False) # ₹ amount (mock)
    price_at_purchase = Column(Float, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="holdings")


class Transaction(Base):
    """Append-only audit log. Every mock buy/sell gets a row, even failed ones."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)           # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)         # buy | sell | failed
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)         # success | failed | pending
    reasoning = Column(Text, nullable=False)        # mandatory — ties to planner reasoning
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")
