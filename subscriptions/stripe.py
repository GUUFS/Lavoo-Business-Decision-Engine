from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os
import secrets

from db.pg_connections import get_db
from db.pg_models import PaymentIntentCreate, PaymentIntentResponse, PaymentVerify, SubscriptionResponse

from .stripe_service import StripeService
from db.pg_models import User, Subscriptions
from api.routes.login import get_current_user
import json
import traceback

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
        # Handle different types of current_user
        if isinstance(current_user, dict):
            # Extract user_id from nested structure
            if "user" in current_user:
                user_data = current_user["user"]
                if isinstance(user_data, dict):
                    user_id = user_data.get("id") or user_data.get("user_id")
                elif hasattr(user_data, 'id'):
                    # user_data is a User object
                    user_id = user_data.id
                else:
                    # user_data is directly the user_id
                    user_id = user_data
            else:
                # Try common key names
                user_id = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Could not extract user_id from token"
                )
        else:
            # current_user is a User object
            user_id = current_user.id
        
        print(f"DEBUG: Extracted user_id: {user_id}")
        print(f"DEBUG: Requested user_id: {payment_data.user_id}")
        
        # Verify the user_id matches the authenticated user (convert to int for comparison)
        if int(payment_data.user_id) != int(user_id):
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized: user_id {payment_data.user_id} does not match authenticated user {user_id}"
            )
        
        # Generate unique transaction reference
        tx_ref = generate_tx_ref("STRIPE")
        
        # Create payment intent with Stripe (subscription will be created AFTER payment succeeds)
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
        
        # NOTE: We no longer create subscription here.
        # Subscription is created ONLY after payment succeeds (in verify_payment or webhook)
        # This prevents duplicate entries for failed/abandoned payments
        
        return intent
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in create_payment_intent: {str(e)}")  # Debug logging
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-payment", response_model=SubscriptionResponse)
async def verify_payment(
    payment_verify: PaymentVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify payment and CREATE subscription on success with commission calculation.
    Subscription is only created here - not when payment intent is created.
    """
    try:
        # Extract user_id (your existing logic)
        if isinstance(current_user, dict):
            if "user" in current_user:
                user_data = current_user["user"]
                if isinstance(user_data, dict):
                    user_id = user_data.get("id") or user_data.get("user_id")
                elif hasattr(user_data, 'id'):
                    user_id = user_data.id
                else:
                    user_id = user_data
            else:
                user_id = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
            
            if user_id is None:
                raise HTTPException(status_code=500, detail="Could not extract user_id from token")
        else:
            user_id = current_user.id
        
        if int(payment_verify.user_id) != int(user_id):
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Verify with Stripe
        verification = StripeService.verify_payment(payment_verify.payment_intent_id)
        
        if verification["status"] != "succeeded":
            raise HTTPException(
                status_code=400, 
                detail=f"Payment not successful. Status: {verification['status']}"
            )
        
        # Check for duplicate (already processed)
        existing_sub = db.query(Subscriptions).filter(
            Subscriptions.transaction_id == payment_verify.payment_intent_id
        ).first()
        
        if existing_sub:
            print(f"⚠️ Payment {payment_verify.payment_intent_id} already processed")
            return existing_sub
        
        # Extract metadata from payment intent
        metadata = verification.get("metadata", {})
        plan_type = metadata.get("plan_type", "monthly")
        tx_ref = metadata.get("tx_ref", generate_tx_ref("STRIPE"))
        
        # Calculate subscription dates
        start_date, end_date = calculate_subscription_dates(plan_type)
        
        # CREATE subscription record (only on success)
        subscription = Subscriptions(
            user_id=payment_verify.user_id,
            subscription_plan=plan_type,
            transaction_id=payment_verify.payment_intent_id,
            tx_ref=tx_ref,
            amount=Decimal(str(verification.get("amount", 0))),  # Already in dollars from Service
            currency=verification.get("currency", "USD").upper(),
            status="completed",  # Already succeeded
            payment_provider="stripe",
            start_date=start_date,
            end_date=end_date
        )
        
        db.add(subscription)
        db.flush()  # Get subscription ID for commission
        
        # Update user's subscription status
        user = db.query(User).filter(User.id == payment_verify.user_id).first()
        if user:
            if hasattr(user, 'subscription_status'):
                user.subscription_status = "active"
            if hasattr(user, 'subscription_plan'):
                user.subscription_plan = plan_type
            if hasattr(user, 'subscription_expires_at'):
                user.subscription_expires_at = end_date
        
        # Calculate commission
        from subscriptions.commission_service import CommissionService
        
        commission = CommissionService.calculate_commission(
            subscription=subscription,
            db=db
        )
        
        if commission:
            print(f"✅ Commission created: ${commission.amount} for referrer {commission.user_id}")
        else:
            print(f"ℹ️  No commission created (user not referred)")
        
        db.commit()
        db.refresh(subscription)
        
        return subscription
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
   

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None, alias="stripe-signature"), db: Session = Depends(get_db)):
    """
    Handle Stripe webhooks with commission calculation.
    This is a fallback - subscription may already be created by verify_payment.
    Also handles Payout events for Connect transfers.
    """
    try:
        payload = await request.body()
        event = StripeService.verify_webhook_signature(payload, stripe_signature)
        
        # --- IDEMPOTENCY CHECK ---
        # Although handled by logic checks, good to log the event ID
        
        if event.type == "payment_intent.succeeded":
            payment_intent = event.data.object
            
            # Check if subscription already exists
            subscription = db.query(Subscriptions).filter(
                Subscriptions.transaction_id == payment_intent.id
            ).first()
            
            if subscription:
                # Already processed (by verify_payment) - just ensure status is correct
                if subscription.status != "completed":
                    subscription.status = "completed"
                    db.commit()
                print(f"✅ Webhook: Subscription {subscription.id} already exists")
            else:
                # Create new subscription (fallback if verify_payment wasn't called)
                metadata = payment_intent.metadata or {}
                user_id = int(metadata.get("user_id", 0))
                plan_type = metadata.get("plan_type", "monthly")
                tx_ref = metadata.get("tx_ref", generate_tx_ref("STRIPE"))
                
                if user_id:
                    start_date, end_date = calculate_subscription_dates(plan_type)
                    
                    subscription = Subscriptions(
                        user_id=user_id,
                        subscription_plan=plan_type,
                        transaction_id=payment_intent.id,
                        tx_ref=tx_ref,
                        amount=Decimal(str(payment_intent.amount / 100)),
                        currency=payment_intent.currency.upper(),
                        status="completed",
                        payment_provider="stripe",
                        start_date=start_date,
                        end_date=end_date
                    )
                    db.add(subscription)
                    db.flush()
                    
                    # Update user
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        if hasattr(user, 'subscription_status'):
                            user.subscription_status = "active"
                        if hasattr(user, 'subscription_plan'):
                            user.subscription_plan = plan_type
                        if hasattr(user, 'subscription_expires_at'):
                            user.subscription_expires_at = end_date
                    
                    # Calculate commission
                    from subscriptions.commission_service import CommissionService
                    commission = CommissionService.calculate_commission(subscription=subscription, db=db)
                    if commission:
                        print(f"✅ Webhook: Commission created ${commission.amount}")
                    
                    db.commit()
                    print(f"✅ Webhook: Created subscription {subscription.id}")
        
        elif event.type == "payment_intent.payment_failed":
            # No subscription to update if we don't create on failure
            print(f"⚠️ Webhook: Payment failed for {event.data.object.id}")
            
        elif event.type == "payout.paid":
            handle_payout_paid(event, db)
            
        elif event.type == "payout.failed" or event.type == "payout.canceled":
            handle_payout_failed(event, db)
        
        return {"status": "success"}
        
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Webhook signature verification failed: {str(e)}")
        # Log specific details about headers if needed (careful with PII)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        print(f"❌ Webhook error [{event.type if 'event' in locals() else 'unknown'}]: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


def handle_payout_paid(event: dict, db: Session):
    """
    Handle successful Stripe Connect payout.
    Updates Payout status to 'completed' and Commissions to 'paid'.
    """
    # event is an object from stripe library (in StripeService.verify_webhook_signature) 
    # OR a dict if we didn't wrap it. 
    # StripeService returns stripe.Event object, event.data.object is the payload
    # Let's assume standard Stripe Python library behavior
    
    stripe_payout = event.data.object
    metadata = stripe_payout.get("metadata", {})
    internal_payout_id = metadata.get("stripe_connect_payout_id")

    if not internal_payout_id:
        # Might be a platform payout not related to commissions
        return

    from db.pg_models import Payout, Commission
    from subscriptions.payout_service import PayoutService 

    payout = db.query(Payout).get(internal_payout_id)
    if not payout:
        print(f"⚠️ Webhook: Payout {internal_payout_id} not found")
        return

    if payout.status == "completed":
        return

    payout.status = "completed"  # Consistent with Flutterwave
    payout.completed_at = datetime.utcnow()

    # Update commissions
    commissions = db.query(Commission).filter(
        Commission.payout_id == payout.id
    ).all()

    for commission in commissions:
        commission.status = "paid"
        commission.paid_at = datetime.utcnow()

    # Update monthly summary
    PayoutService._update_summary_on_payout(payout, db)

    db.commit()

    print(f"✅ Webhook: Stripe payout {payout.id} finalized successfully")


def handle_payout_failed(event: dict, db: Session):
    """
    Handle failed Stripe Connect payout.
    Updates Payout status to 'failed' and reverts Commissions.
    """
    stripe_payout = event.data.object
    metadata = stripe_payout.get("metadata", {})
    internal_payout_id = metadata.get("stripe_connect_payout_id")

    if not internal_payout_id:
        return

    from db.pg_models import Payout, Commission
    
    payout = db.query(Payout).get(internal_payout_id)
    if not payout:
        return

    payout.status = "failed"
    payout.failure_reason = stripe_payout.get("failure_message") or "Stripe payout failed"
    
    # Revert commissions to 'pending' so they can be retried
    commissions = db.query(Commission).filter(
        Commission.payout_id == payout.id
    ).all()
    
    for commission in commissions:
        commission.payout_id = None
        commission.status = 'pending'
        commission.approved_at = None

    db.commit()

    print(f"❌ Webhook: Stripe payout {payout.id} failed: {payout.failure_reason}")


@router.get("/subscription/{user_id}")
async def get_user_subscription(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's active subscription
    """
    # Handle different types of current_user
    if isinstance(current_user, dict):
        # Extract user_id from nested structure
        if "user" in current_user:
            user_data = current_user["user"]
            if isinstance(user_data, dict):
                current_user_id = user_data.get("id") or user_data.get("user_id")
            elif hasattr(user_data, 'id'):
                current_user_id = user_data.id
            else:
                current_user_id = user_data
        else:
            current_user_id = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
        
        if current_user_id is None:
            raise HTTPException(status_code=500, detail="Could not extract user_id from token")
    else:
        current_user_id = current_user.id
    
    # Verify the user_id matches (convert to int for comparison)
    if int(user_id) != int(current_user_id):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    subscription = db.query(Subscriptions).filter(
        Subscriptions.user_id == user_id,
        Subscriptions.status == "completed",
        Subscriptions.end_date > datetime.utcnow()
    ).order_by(Subscriptions.created_at.desc()).first()
    
    if not subscription:
        return {"message": "No active subscription found"}
    
    return subscription