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
    wallet_balance = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sessions = relationship("Session", back_populates="user")
    investments = relationship("Investment", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    payment_orders = relationship("PaymentOrder", back_populates="user")


class PaymentOrder(Base):
    """Tracks Razorpay orders and mock funding"""
    __tablename__ = "payment_orders"

    id = Column(String, primary_key=True)           # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)          # Amount in INR
    status = Column(String, default="created")      # created | success | failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="payment_orders")


class Session(Base):
    """One investment planning session. Maps 1:1 with a LangGraph thread_id."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)           # UUID — same as thread_id
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")       # active | interrupted | complete
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")


class Wallet(Base):
    """Single-row wallet — stores the global app wallet balance."""
    __tablename__ = "wallet"

    id = Column(Integer, primary_key=True, default=1)   # Always row id=1
    balance = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Investment(Base):
    """
    A virtual investment purchased by the AI agent on the user's behalf.
    Tracks principal, projected returns, and current accumulated value.
    Persists across all sessions (thread_ids).
    """
    __tablename__ = "investments"

    id = Column(String, primary_key=True)                   # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String, nullable=False)              # session that made this investment

    # What was bought
    source = Column(String, nullable=False)                 # e.g. "HDFC Balanced Fund", "Gold", "Reliance"
    asset_type = Column(String, nullable=False)             # mutual_fund | stock | gold | silver | fd | other

    # Financial details
    principal = Column(Float, nullable=False)               # ₹ amount invested at purchase
    holding = Column(String, nullable=False)                 # holding metric (e.g. "₹2,450.50/stock", "7.5% p.a.", "₹6,800/g", "₹45.20 NAV")
    annual_rate_pct = Column(Float, nullable=False, default=0.0) # expected annual return % used in projection
    years = Column(Integer, nullable=False)                 # investment horizon in years

    # Tracking
    current_value = Column(Float, nullable=False)           # starts = principal; updated on refresh
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    bought_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Extra context
    notes = Column(Text, nullable=True)                     # AI reasoning or extra context

    user = relationship("User", back_populates="investments")


class Transaction(Base):
    """Append-only audit log. Every mock buy/sell gets a row, even failed ones."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)           # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)         # buy | sell | wallet_topup | failed
    amount = Column(Float, nullable=False)
    percent_allocation = Column(Float, nullable=True)
    status = Column(String, nullable=False)         # success | failed | pending
    reasoning = Column(Text, nullable=False)        # tied to planner reasoning
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")
