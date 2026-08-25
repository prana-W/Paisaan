import uuid
import razorpay
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, PaymentOrder
from app.db.crud import get_or_create_user
from app.core.config import get_settings
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

# Initialize razorpay client
client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

class CreateOrderRequest(BaseModel):
    user_id: str | None = None
    amount: float  # Amount in INR

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: float
    currency: str
    id: str
    key_id: str
    user_id: str

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str


@router.post("/wallet/create-order", response_model=CreateOrderResponse)
def create_order(request: CreateOrderRequest, db: Session = Depends(get_db)):
    user = get_or_create_user(db, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Could not create or find user")

    amount_in_paise = int(request.amount * 100)
    
    try:
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_order = PaymentOrder(
        id=str(uuid.uuid4()),
        user_id=user.id,
        razorpay_order_id=order["id"],
        amount=request.amount,
        status="created"
    )
    db.add(db_order)
    db.commit()

    return CreateOrderResponse(
        order_id=order["id"],
        amount=request.amount,
        currency="INR",
        id=db_order.id,
        key_id=settings.razorpay_key_id,
        user_id=user.id
    )


@router.post("/wallet/verify-payment")
def verify_payment(request: VerifyPaymentRequest, db: Session = Depends(get_db)):
    db_order = db.query(PaymentOrder).filter(PaymentOrder.razorpay_order_id == request.razorpay_order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    if db_order.status == "success":
        return {"status": "success", "message": "Already verified"}

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': request.razorpay_order_id,
            'razorpay_payment_id': request.razorpay_payment_id,
            'razorpay_signature': request.razorpay_signature
        })
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Verification successful
    db_order.status = "success"
    
    user = db.query(User).filter(User.id == db_order.user_id).first()
    if user:
        user.wallet_balance += db_order.amount
        
    db.commit()

    return {"status": "success", "wallet_balance": user.wallet_balance}
