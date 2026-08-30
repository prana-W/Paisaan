"""
Wallet routes — Razorpay order creation, payment verification, and balance query.
All amounts are in Indian Rupees (₹). Razorpay uses paise (1 ₹ = 100 paise).
"""
import hmac
import hashlib
import logging

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.db.session import get_db
from app.db.crud import get_wallet_balance, add_to_wallet, log_transaction, get_or_create_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Single shared user id — single-user app
_SINGLE_USER_ID = "default"


def _get_razorpay_client():
    settings = get_settings()
    return razorpay.Client(
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
    )


# ── Request / Response schemas ────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in ₹ (must be > 0)")


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: float          # in ₹
    amount_paise: int      # what Razorpay actually used
    currency: str
    razorpay_key_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    amount: float          # in ₹ — we use this to credit the wallet


class VerifyPaymentResponse(BaseModel):
    success: bool
    new_balance: float
    message: str


class WalletBalanceResponse(BaseModel):
    balance: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/wallet/order", response_model=CreateOrderResponse)
def create_wallet_order(body: CreateOrderRequest, db: DBSession = Depends(get_db)):
    """Create a Razorpay order for topping up the wallet."""
    settings = get_settings()
    client = _get_razorpay_client()

    amount_paise = int(round(body.amount * 100))  # Razorpay expects paise

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,   # auto-capture
        })
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Razorpay error: {e}")

    logger.info("Razorpay order created: %s for ₹%.2f", order["id"], body.amount)

    return CreateOrderResponse(
        order_id=order["id"],
        amount=body.amount,
        amount_paise=amount_paise,
        currency="INR",
        razorpay_key_id=settings.razorpay_key_id,
    )


@router.post("/wallet/verify", response_model=VerifyPaymentResponse)
def verify_wallet_payment(body: VerifyPaymentRequest, db: DBSession = Depends(get_db)):
    """
    Verify Razorpay payment signature and credit amount to wallet.
    Razorpay signature = HMAC-SHA256(order_id + '|' + payment_id, key_secret).
    """
    settings = get_settings()

    # HMAC verification
    expected_sig = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, body.razorpay_signature):
        logger.warning(
            "Razorpay signature mismatch for order=%s payment=%s",
            body.razorpay_order_id, body.razorpay_payment_id,
        )
        raise HTTPException(status_code=400, detail="Payment verification failed: signature mismatch")

    # Credit the wallet
    new_balance = add_to_wallet(db, body.amount)

    # Ensure default user exists for audit log
    user = get_or_create_user(db, _SINGLE_USER_ID)
    log_transaction(
        db,
        user_id=user.id,
        action="wallet_topup",
        amount=body.amount,
        status="success",
        reasoning=f"Razorpay payment {body.razorpay_payment_id} verified for order {body.razorpay_order_id}",
    )

    logger.info(
        "Wallet credited ₹%.2f via Razorpay. New balance: ₹%.2f",
        body.amount, new_balance,
    )

    return VerifyPaymentResponse(
        success=True,
        new_balance=new_balance,
        message=f"₹{body.amount:,.2f} added to your wallet. New balance: ₹{new_balance:,.2f}",
    )


@router.get("/wallet/balance", response_model=WalletBalanceResponse)
def get_balance(db: DBSession = Depends(get_db)):
    """Return the current wallet balance."""
    balance = get_wallet_balance(db)
    return WalletBalanceResponse(balance=balance)
