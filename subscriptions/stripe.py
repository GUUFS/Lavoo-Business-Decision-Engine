from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os
import secrets
import stripe

from db.pg_connections import get_db
from db.pg_models import PaymentIntentCreate, PaymentIntentResponse, PaymentVerify, SubscriptionResponse, CreateSubscriptionRequest, UpdatePaymentMethodRequest

from .stripe_service import StripeService
from db.pg_models import User, Subscriptions
from api.routes.login import get_current_user
import json
import traceback

from fastapi import BackgroundTasks
from emailing.email_service import email_service

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


# Price IDs - Set these in your environment variables or directly
STRIPE_PRICE_IDS = {
    "monthly": os.getenv("STRIPE_MONTHLY_PRICE_ID", ""),
    "yearly": os.getenv("STRIPE_YEARLY_PRICE_ID", ""),
}


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
    background_tasks: BackgroundTasks,
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
            # Fetch user for email notification
            user = db.query(User).filter(User.id == payment_verify.user_id).first()
            if user:
                background_tasks.add_task(
                    email_service.send_payment_failed_email,
                    user.email,
                    user.name,
                    float(verification.get("amount", 0)),
                    f"Stripe Payment Status: {verification['status']}"
                )
            
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
            subscription_status="active",
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
        background_tasks.add_task(
            email_service.send_payment_success_email,
            user.email,
            user.name,
            float(verification.get("amount", 0)),
            plan_type,
            end_date.strftime("%B %d, %Y")
        )
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
        
        # Allow bypass for manual testing with curl if not in production
        is_production = os.getenv("ENVIRONMENT", "development") == "production"
        if not stripe_signature and not is_production:
            print("⚠️ Webhook: Manual test detected (no signature). Bypassing verification.")
            try:
                event_data = json.loads(payload)
                event = stripe.Event.construct_from(event_data, stripe.api_key)
            except Exception as e:
                print(f"❌ Webhook: Failed to parse manual payload: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
        else:
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
                        subscription_status="active",
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
    Standardized to handle both sync and async flows.
    """
    stripe_payout = event.data.object
    metadata = stripe_payout.get("metadata", {})
    internal_payout_id = metadata.get("stripe_connect_payout_id")

    if not internal_payout_id:
        return

    from db.pg_models import Payout
    from subscriptions.payout_service import PayoutService 

    payout = db.query(Payout).get(internal_payout_id)
    if not payout:
        print(f"⚠️ Webhook: Payout {internal_payout_id} not found")
        return

    # If already completed (e.g. via sync flow), do nothing
    if payout.status == "completed":
        print(f"ℹ️ Webhook: Stripe payout {payout.id} already completed (idempotent)")
        return

    # Use specialized service method for completion
    # Pass background_tasks=None as we already sent the success email during initiation
    from fastapi import BackgroundTasks
    bg = BackgroundTasks() # Empty bg tasks to avoid double emails
    PayoutService.complete_stripe_payout(payout.id, bg, "paid", db)

    print(f"✅ Webhook: Stripe payout {payout.id} finalized successfully")


def handle_payout_failed(event: dict, db: Session):
    """
    Handle failed Stripe Connect payout.
    Reverses accounting using PayoutService logic.
    """
    stripe_payout = event.data.object
    metadata = stripe_payout.get("metadata", {})
    internal_payout_id = metadata.get("stripe_connect_payout_id")

    if not internal_payout_id:
        return

    from subscriptions.payout_service import PayoutService
    
    failure_reason = stripe_payout.get("failure_message") or "Stripe payout failed / Bank rejection"
    
    # Use centralized reversal logic
    PayoutService.reverse_payout(internal_payout_id, failure_reason, db)

    print(f"❌ Webhook: Stripe payout {internal_payout_id} reversed/failed: {failure_reason}")


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


@router.post("/create-subscription-with-saved-card")
async def create_subscription_with_saved_card(
    request: CreateSubscriptionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    NEW ENDPOINT: Create subscription with saved payment method
    This replaces the old create-payment-intent flow for subscriptions
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
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate plan type
        if request.plan_type not in STRIPE_PRICE_IDS:
            raise HTTPException(status_code=400, detail="Invalid plan type")
        
        price_id = STRIPE_PRICE_IDS[request.plan_type]
        if not price_id:
            raise HTTPException(
                status_code=500, 
                detail=f"Price ID not configured for {request.plan_type} plan. Please set STRIPE_{request.plan_type.upper()}_PRICE_ID in environment."
            )
        
        # Get or create Stripe customer
        stripe_customer_id = user.stripe_customer_id if hasattr(user, 'stripe_customer_id') else None
        customer_id = StripeService.get_or_create_customer(
            user_id=user_id,
            email=user.email,
            name=user.name,
            stripe_customer_id=stripe_customer_id
        )
        
        # Update user with customer ID if new
        if not stripe_customer_id and hasattr(user, 'stripe_customer_id'):
            user.stripe_customer_id = customer_id
            db.commit()
        
        # Attach payment method to customer
        StripeService.attach_payment_method(
            payment_method_id=request.payment_method_id,
            customer_id=customer_id,
            set_as_default=True
        )
        
        # Check for existing active subscription
        if hasattr(user, 'stripe_subscription_id') and user.stripe_subscription_id:
            try:
                existing_sub = StripeService.retrieve_subscription(user.stripe_subscription_id)
                if existing_sub["status"] == "active":
                    # Update existing subscription to new plan
                    updated_sub = StripeService.update_subscription_price(
                        subscription_id=user.stripe_subscription_id,
                        new_price_id=price_id,
                        prorate=True
                    )
                    
                    # Update database
                    subscription = db.query(Subscriptions).filter(
                        Subscriptions.user_id == user_id,
                        Subscriptions.subscription_status == "active"
                    ).first()
                    
                    if subscription:
                        subscription.subscription_plan = request.plan_type
                        subscription.end_date = datetime.fromtimestamp(updated_sub["current_period_end"])
                        db.commit()
                    
                    return {
                        "status": "success",
                        "subscription_id": updated_sub["id"],
                        "message": "Subscription updated successfully"
                    }
            except:
                # Subscription doesn't exist or is invalid, create new one
                pass
        
        # Generate transaction reference
        tx_ref = generate_tx_ref("STRIPE-SUB")
        
        # Create new subscription
        subscription_result = StripeService.create_subscription_with_saved_card(
            customer_id=customer_id,
            price_id=price_id,
            payment_method_id=request.payment_method_id,
            metadata={
                "user_id": str(user_id),
                "plan_type": request.plan_type,
                "tx_ref": tx_ref
            }
        )
        
        # Handle subscription status
        if subscription_result["status"] == "active":
            # Subscription is active, create database record
            start_date, end_date = calculate_subscription_dates(request.plan_type)
            
            # Get pricing from settings
            from api.routes.control import get_settings
            settings = get_settings(db)
            amount = settings.monthly_price if request.plan_type == "monthly" else settings.yearly_price
            
            subscription = Subscriptions(
                user_id=user_id,
                subscription_plan=request.plan_type,
                transaction_id=subscription_result["payment_intent_id"] or subscription_result["subscription_id"],
                tx_ref=tx_ref,
                amount=Decimal(str(amount)),
                currency="USD",
                status="completed",
                subscription_status="active",
                payment_provider="stripe",
                start_date=start_date,
                end_date=end_date
            )
            
            db.add(subscription)
            db.flush()
            
            # Update user
            if hasattr(user, 'subscription_status'):
                user.subscription_status = "active"
            if hasattr(user, 'subscription_plan'):
                user.subscription_plan = request.plan_type
            if hasattr(user, 'subscription_expires_at'):
                user.subscription_expires_at = end_date
            if hasattr(user, 'stripe_subscription_id'):
                user.stripe_subscription_id = subscription_result["subscription_id"]
            
            # Calculate commission
            from subscriptions.commission_service import CommissionService
            commission = CommissionService.calculate_commission(subscription=subscription, db=db)
            
            db.commit()
            db.refresh(subscription)
            
            # Send success email
            background_tasks.add_task(
                email_service.send_payment_success_email,
                user.email,
                user.name,
                float(amount),
                request.plan_type,
                end_date.strftime("%B %d, %Y")
            )
            
            return {
                "status": "active",
                "subscription_id": subscription_result["subscription_id"],
                "subscription": subscription
            }
            
        elif subscription_result["status"] == "incomplete":
            # Requires additional authentication (3D Secure)
            return {
                "status": "requires_action",
                "subscription_id": subscription_result["subscription_id"],
                "client_secret": subscription_result["client_secret"],
                "message": "Additional authentication required"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Subscription creation failed with status: {subscription_result['status']}"
            )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Subscription creation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm-subscription")
async def confirm_subscription(
    subscription_id: str,
    payment_intent_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm subscription after 3D Secure authentication
    """
    try:
        # Extract user_id
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
        else:
            user_id = current_user.id
        
        # Verify payment intent
        verification = StripeService.verify_payment(payment_intent_id)
        
        if verification["status"] != "succeeded":
            raise HTTPException(
                status_code=400,
                detail=f"Payment not successful. Status: {verification['status']}"
            )
        
        # Get subscription details
        subscription_details = StripeService.retrieve_subscription(subscription_id)
        
        if subscription_details["status"] == "active":
            # Create database record
            metadata = verification.get("metadata", {})
            plan_type = metadata.get("plan_type", "monthly")
            tx_ref = metadata.get("tx_ref", generate_tx_ref("STRIPE-SUB"))
            
            start_date, end_date = calculate_subscription_dates(plan_type)
            
            # Get pricing
            from api.routes.control import get_settings
            settings = get_settings(db)
            amount = settings.monthly_price if plan_type == "monthly" else settings.yearly_price
            
            subscription = Subscriptions(
                user_id=user_id,
                subscription_plan=plan_type,
                transaction_id=payment_intent_id,
                tx_ref=tx_ref,
                amount=Decimal(str(amount)),
                currency="USD",
                status="completed",
                subscription_status="active",
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
                if hasattr(user, 'stripe_subscription_id'):
                    user.stripe_subscription_id = subscription_id
            
            # Calculate commission
            from subscriptions.commission_service import CommissionService
            commission = CommissionService.calculate_commission(subscription=subscription, db=db)
            
            db.commit()
            db.refresh(subscription)
            
            # Send success email
            if user:
                background_tasks.add_task(
                    email_service.send_payment_success_email,
                    user.email,
                    user.name,
                    float(amount),
                    plan_type,
                    end_date.strftime("%B %d, %Y")
                )
            
            return {
                "status": "success",
                "subscription": subscription
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Subscription status: {subscription_details['status']}"
            )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel-subscription")
async def cancel_subscription_endpoint(
    at_period_end: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel user's subscription
    """
    try:
        # Extract user_id
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
        else:
            user_id = current_user.id
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not hasattr(user, 'stripe_subscription_id') or not user.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Cancel in Stripe
        result = StripeService.cancel_subscription(
            subscription_id=user.stripe_subscription_id,
            at_period_end=at_period_end
        )
        
        # Update database
        subscription = db.query(Subscriptions).filter(
            Subscriptions.user_id == user_id,
            Subscriptions.subscription_status == "active"
        ).first()
        
        if subscription:
            if at_period_end:
                subscription.subscription_status = "canceling"
            else:
                subscription.subscription_status = "cancelled"
                subscription.status = "cancelled"
        
        if hasattr(user, 'subscription_status'):
            user.subscription_status = "canceling" if at_period_end else "cancelled"
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Subscription cancelled" + (" at period end" if at_period_end else " immediately"),
            "cancel_at_period_end": result["cancel_at_period_end"]
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/update-payment-method")
async def update_payment_method(
    request: UpdatePaymentMethodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update default payment method for subscriptions
    """
    try:
        # Extract user_id
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
        else:
            user_id = current_user.id
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No Stripe customer found")
        
        # Attach new payment method
        StripeService.attach_payment_method(
            payment_method_id=request.payment_method_id,
            customer_id=user.stripe_customer_id,
            set_as_default=True
        )
        
        return {
            "status": "success",
            "message": "Payment method updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment-methods")
async def get_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's saved payment methods
    """
    try:
        # Extract user_id
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
        else:
            user_id = current_user.id
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            return {"payment_methods": []}
        
        payment_methods = StripeService.get_customer_payment_methods(user.stripe_customer_id)
        
        return {"payment_methods": payment_methods}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))