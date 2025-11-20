from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os
import secrets

from db.pg_connections import get_db
from db.pg_models import PaymentIntentCreate, PaymentIntentResponse, PaymentVerify,SubscriptionResponse

from .stripe_service import StripeService
from db.pg_models import User, Subscriptions  # Adjust import based on your structure
from api.routes.login import get_current_user  # Adjust based on your auth setup

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

def generate_tx_ref(prefix: str = "STRIPE") -> str:
    """Generate a unique transaction reference"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_str = secrets.token_hex(4).upper()
    return f"{prefix}-{timestamp}-{random_str}"

def calculate_subscription_dates(plan_type: str):
    """Calculate subscription start and end dates"""
    start_date = datetime.utcnow()
    
    if plan_type == "monthly":
        end_date = start_date + timedelta(days=30)
    elif plan_type == "yearly":
        end_date = start_date + timedelta(days=365)
    else:
        raise ValueError(f"Invalid plan type: {plan_type}")
    
    return start_date, end_date

@router.get("/config")
async def get_stripe_config():
    """
    Get Stripe publishable key for frontend
    """
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    if not publishable_key:
        raise HTTPException(status_code=500, detail="Stripe configuration not found")
    
    return {
        "publishableKey": publishable_key
    }

@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Payment Intent
    """
    try:
        # Verify the user_id matches the authenticated user
        if payment_data.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Generate unique transaction reference
        tx_ref = generate_tx_ref("STRIPE")
        
        # Create payment intent with Stripe
        intent = StripeService.create_payment_intent(
            amount=payment_data.amount,
            currency="usd",
            customer_email=payment_data.email,
            metadata={
                "user_id": str(payment_data.user_id),
                "plan_type": payment_data.plan_type,
                "customer_name": payment_data.name,
                "tx_ref": tx_ref
            }
        )
        
        # Calculate subscription dates
        start_date, end_date = calculate_subscription_dates(payment_data.plan_type)
        
        # Save pending subscription to database
        subscription = Subscriptions(
            user_id=payment_data.user_id,
            subscription_plan=payment_data.plan_type,
            transaction_id=intent["paymentIntentId"],
            tx_ref=tx_ref,
            amount=Decimal(str(payment_data.amount)),
            currency=intent["currency"].upper(),
            status="pending",
            payment_provider="stripe",
            start_date=start_date,
            end_date=end_date
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        return intent
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-payment", response_model=SubscriptionResponse)
async def verify_payment(
    payment_verify: PaymentVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify payment and update subscription status
    """
    try:
        # Verify the user_id matches
        if payment_verify.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Verify with Stripe
        verification = StripeService.verify_payment(payment_verify.payment_intent_id)
        
        # Find subscription in database
        subscription = db.query(Subscriptions).filter(
            Subscriptions.transaction_id == payment_verify.payment_intent_id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Update subscription status based on Stripe verification
        if verification["status"] == "succeeded":
            subscription.status = "completed"
            
            # Update user's subscription status (if you have these fields in User model)
            user = db.query(User).filter(User.id == payment_verify.user_id).first()
            if user:
                # Update user subscription fields if they exist
                if hasattr(user, 'subscription_status'):
                    user.subscription_status = "active"
                if hasattr(user, 'subscription_plan'):
                    user.subscription_plan = subscription.subscription_plan
                if hasattr(user, 'subscription_expires_at'):
                    user.subscription_expires_at = subscription.end_date
        else:
            subscription.status = "failed"
        
        db.commit()
        db.refresh(subscription)
        
        return subscription
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhooks for payment events
    """
    try:
        payload = await request.body()
        
        # Verify webhook signature
        event = StripeService.verify_webhook_signature(payload, stripe_signature)
        
        # Handle different event types
        if event.type == "payment_intent.succeeded":
            payment_intent = event.data.object
            
            # Update subscription status
            subscription = db.query(Subscriptions).filter(
                Subscriptions.transaction_id == payment_intent.id
            ).first()
            
            if subscription:
                subscription.status = "completed"
                subscription.updated_at = datetime.utcnow()
                
                # Update user subscription if user fields exist
                user = db.query(User).filter(User.id == subscription.user_id).first()
                if user:
                    if hasattr(user, 'subscription_status'):
                        user.subscription_status = "active"
                    if hasattr(user, 'subscription_plan'):
                        user.subscription_plan = subscription.subscription_plan
                    if hasattr(user, 'subscription_expires_at'):
                        user.subscription_expires_at = subscription.end_date
                    
                db.commit()
        
        elif event.type == "payment_intent.payment_failed":
            payment_intent = event.data.object
            
            subscription = db.query(Subscriptions).filter(
                Subscriptions.transaction_id == payment_intent.id
            ).first()
            
            if subscription:
                subscription.status = "failed"
                subscription.updated_at = datetime.utcnow()
                db.commit()
        
        elif event.type == "payment_intent.canceled":
            payment_intent = event.data.object
            
            subscription = db.query(Subscriptions).filter(
                Subscriptions.transaction_id == payment_intent.id
            ).first()
            
            if subscription:
                subscription.status = "cancelled"
                subscription.updated_at = datetime.utcnow()
                db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscription/{user_id}")
async def get_user_subscription(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's active subscription
    """
    # Verify the user_id matches
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    subscription = db.query(Subscriptions).filter(
        Subscriptions.user_id == user_id,
        Subscriptions.status == "completed",
        Subscriptions.end_date > datetime.utcnow()
    ).order_by(Subscriptions.created_at.desc()).first()
    
    if not subscription:
        return {"message": "No active subscription found"}
    
    return subscription