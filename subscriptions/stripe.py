from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os
import secrets
import stripe

from db.pg_connections import get_db
from db.pg_models import PaymentIntentCreate, PaymentIntentResponse, PaymentVerify, SubscriptionResponse, CreateSubscriptionRequest, UpdatePaymentMethodRequest, ConfirmSubscriptionRequest, SaveCardRequest

from .stripe_service import StripeService
from db.pg_models import User, Subscriptions
from api.routes.login import get_current_user
import json
import traceback

from fastapi import BackgroundTasks
from emailing.email_service import email_service
from api.services.notification_service import NotificationService
from db.pg_models import NotificationType
from .beta_service import BetaService

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


# Price IDs - Helper function to get from environment dynamically
def get_stripe_price_id(plan_type: str) -> str:
    """Get Price ID relative to plan type from environment"""
    env_keys = {
        "monthly": "STRIPE_MONTHLY_PRICE_ID",
        "yearly": "STRIPE_YEARLY_PRICE_ID",
        "quarterly": "STRIPE_QUARTERLY_PRICE_ID"
    }
    key = env_keys.get(plan_type)
    if not key:
        return ""
    # Strip any potential whitespace from the env value
    val = os.getenv(key, "")
    return val.strip()


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
    elif plan_type == "quarterly":
        end_date = start_date + timedelta(days=90)
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


@router.get("/history", response_model=list[SubscriptionResponse])
async def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription/payment history
    """
    try:
        # Handle current_user types
        if isinstance(current_user, dict):
            if "user" in current_user:
                user_data = current_user["user"]
                user_id = user_data.get("id") if isinstance(user_data, dict) else (getattr(user_data, "id", None) or user_data)
            else:
                user_id = current_user.get("id") or current_user.get("sub")
        else:
            user_id = current_user.id

        subscriptions = db.query(Subscriptions).filter(
            Subscriptions.user_id == user_id
        ).order_by(Subscriptions.created_at.desc()).all()
        
        return subscriptions
    except Exception as e:
        print(f"Error fetching subscription history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription history")


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
            # Notify user about payment failure via Dashboard
            NotificationService.create_notification(
                db=db,
                user_id=payment_verify.user_id,
                type=NotificationType.PAYMENT_FAILED.value,
                title="Payment Failed",
                message=f"Your payment of ${float(verification.get('amount', 0))} was not successful (Status: {verification['status']}).",
                link="/dashboard/upgrade"
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

        # Notify user about successful subscription
        NotificationService.create_notification(
            db=db,
            user_id=payment_verify.user_id,
            type=NotificationType.PAYMENT_SUCCESS.value,
            title="Subscription Active!",
            message=f"Your {plan_type} subscription is now active. Thank you for your payment of ${float(verification.get('amount', 0))}.",
            link="/dashboard"
        )
        return subscription
        
    except HTTPException:
        db.rollback()
        raise
    except stripe.error.StripeError as e:
        db.rollback()
        print(f"Stripe Verification Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        print(f"Unexpected Verification Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
   
 
@router.post("/save-card-beta")
async def save_card_for_beta(
    request: SaveCardRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ✅ PCI-COMPLIANT: Save card during beta period
    
    Security:
    - Card data never touches our servers
    - Only Stripe tokens are stored
    - Stripe handles all PCI compliance
    """
    try:
        # Extract user_id
        if isinstance(current_user, dict):
            if "user" in current_user:
                user_data = current_user["user"]
                user_id = user_data.get("id") if isinstance(user_data, dict) else getattr(user_data, "id", None)
            else:
                user_id = current_user.get("id")
        else:
            user_id = current_user.id
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if allowed to save cards
        from subscriptions.beta_service import BetaService
        
        # Allow during beta OR during grace period
        if not BetaService.is_beta_mode() and not BetaService.is_in_grace_period():
            raise HTTPException(
                status_code=400,
                detail="Grace period has ended. Please subscribe to continue using Lavoo."
            )
        
        # Get or create Stripe customer
        stripe_customer_id = user.stripe_customer_id
        customer_id = StripeService.get_or_create_customer(
            user_id=user_id,
            email=user.email,
            name=user.name,
            stripe_customer_id=stripe_customer_id
        )
        
        # Save customer ID if new
        if not stripe_customer_id:
            user.stripe_customer_id = customer_id
        
        # Attach payment method to customer
        StripeService.attach_payment_method(
            payment_method_id=request.payment_method_id,
            customer_id=customer_id,
            set_as_default=True
        )
        
        # ✅ PCI-COMPLIANT: Retrieve ONLY safe metadata from Stripe
        payment_method = stripe.PaymentMethod.retrieve(request.payment_method_id)
        
        # Store only non-sensitive data
        user.stripe_payment_method_id = request.payment_method_id
        user.card_last4 = payment_method.card.last4  # Safe: last 4 digits
        user.card_brand = payment_method.card.brand  # Safe: Visa, Mastercard, etc.
        user.card_exp_month = payment_method.card.exp_month  # Safe: expiration
        user.card_exp_year = payment_method.card.exp_year  # Safe: expiration
        user.card_saved_at = datetime.utcnow()
        
        # Mark as beta user only if we are currently in BETA mode
        if BetaService.is_beta_mode() and not user.is_beta_user:
            BetaService.mark_as_beta_user(user, db)
        
        db.commit()
        
        # Send success notification
        from subscriptions.notification_service import NotificationService
        NotificationService.send_card_saved_success(db, user)
        
        # Send email confirmation
        background_tasks.add_task(
            email_service.send_beta_card_saved_email,
            user.email,
            user.name,
            user.card_last4,
            user.card_brand,
            BetaService.get_grace_period_days()
        )
        
        # Trigger automatic billing if in LAUNCH mode and user isn't active
        if BetaService.get_app_mode() == "launch" and user.subscription_status != "active":
            print(f"🚀 LAUNCH MODE: Triggering immediate billing for user {user.id}")
            try:
                # Default to monthly if not set
                # LAUNCH MODE: Trigger immediate billing
                logger.info(f"🚀 [LAUNCH MODE] Immediate billing triggered for user {user.id} ({user.email})")
                plan_type = user.subscription_plan or "monthly"
                price_id = get_stripe_price_id(plan_type)
                if price_id:
                    sub_result = StripeService.create_subscription_with_saved_card(
                        customer_id=user.stripe_customer_id,
                        price_id=price_id,
                        payment_method_id=request.payment_method_id,
                        metadata={
                            "user_id": str(user.id),
                            "plan_type": plan_type,
                            "auto_billed_on_card_save": "true"
                        }
                    )
                    if sub_result.get("status") in ["active", "trialing", "incomplete"]:
                        start_date, end_date = calculate_subscription_dates(plan_type)
                        user.stripe_subscription_id = sub_result["subscription_id"]
                        user.subscription_status = sub_result["status"]
                        user.subscription_expires_at = end_date
                        logger.info(f"✅ Immediate billing successful for user {user.id}. Status: {user.subscription_status}, Expires: {user.subscription_expires_at}")
                        
                        # Create local subscription record
                        from api.routes.control.settings import get_settings
                        settings = get_settings(db=db, current_user=user)
                        
                        price_map = {
                            "monthly": settings.monthly_price,
                            "quarterly": settings.quarterly_price,
                            "yearly": settings.yearly_price
                        }
                        amount = price_map.get(plan_type, 29.95)

                        subscription = Subscriptions(
                            user_id=user.id,
                            subscription_plan=plan_type,
                            transaction_id=sub_result["subscription_id"],
                            tx_ref=generate_tx_ref("AUTO"),
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
                        
                        # Calculate commission
                        from subscriptions.commission_service import CommissionService
                        CommissionService.calculate_commission(subscription=subscription, db=db)
                        
                        # Send success email
                        background_tasks.add_task(
                            email_service.send_payment_success_email,
                            user.email,
                            user.name,
                            float(amount),
                            plan_type,
                            end_date.strftime("%B %d, %Y")
                        )
                        
                        print(f"✅ Auto-billing successful for user {user.id}")
            except Exception as auto_err:
                print(f"❌ Auto-billing failed (silent): {str(auto_err)}")

        return {
            "status": "success",
            "message": "Congratulations on becoming a part of the Lavoo Community",
            "card_info": {
                "last4": user.card_last4,
                "brand": user.card_brand,
                "exp_month": user.card_exp_month,
                "exp_year": user.card_exp_year
            },
            "grace_period_days": BetaService.get_grace_period_days(),
            "grace_period_ends": user.grace_period_ends_at.isoformat() if user.grace_period_ends_at else None
        }
        
    except HTTPException:
        db.rollback()
        raise
    except stripe.error.CardError as e:
        db.rollback()
        # Clean error for card declines - no traceback needed
        error_msg = str(e.user_message) if hasattr(e, 'user_message') else str(e)
        print(f"Card declined for user {user.id}: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        db.rollback()
        print(f"Error saving beta card: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/beta/status")
async def get_beta_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's beta status for dashboard display
    """
    try:
        # Extract user_id
        if isinstance(current_user, dict):
            if "user" in current_user:
                user_data = current_user["user"]
                user_id = user_data.get("id") if isinstance(user_data, dict) else getattr(user_data, "id", None)
            else:
                user_id = current_user.get("id")
        else:
            user_id = current_user.id
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        from subscriptions.beta_service import BetaService
        
        status = BetaService.get_user_status(user)
        
        # Add card info if available
        if status.get("show_card_info") and user.card_last4:
            status["card_info"] = {
                "last4": user.card_last4,
                "brand": user.card_brand,
                "exp_month": user.card_exp_month,
                "exp_year": user.card_exp_year
            }
        
        status["is_beta_mode"] = BetaService.is_beta_mode()
        status["is_in_grace_period"] = BetaService.is_in_grace_period()
        
        return status
        
    except Exception as e:
        print(f"Error getting beta status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
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
            
        elif event.type == "invoice.payment_succeeded":
            invoice = event.data.object
            subscription_id = invoice.subscription
            
            if subscription_id:
                print(f"🔄 Webhook: Processing renewal for subscription {subscription_id}")
                
                # Update user and subscription record
                user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
                if user:
                    # Get subscription period from Stripe
                    stripe_sub = stripe.Subscription.retrieve(subscription_id)
                    end_date = datetime.fromtimestamp(stripe_sub.current_period_end)
                    
                    user.subscription_status = "active"
                    user.subscription_expires_at = end_date
                    
                    # Log the historical record
                    new_sub = Subscriptions(
                        user_id=user.id,
                        subscription_plan=user.subscription_plan,
                        transaction_id=invoice.payment_intent,
                        tx_ref=f"RENEW-{user.id}-{datetime.utcnow().strftime('%Y%m%d')}",
                        amount=Decimal(str(invoice.amount_paid / 100)),
                        currency=invoice.currency.upper(),
                        status="completed",
                        subscription_status="active",
                        payment_provider="stripe",
                        start_date=datetime.fromtimestamp(stripe_sub.current_period_start),
                        end_date=end_date
                    )
                    db.add(new_sub)
                    
                    # Handle commission for renewal if needed
                    from subscriptions.commission_service import CommissionService
                    CommissionService.calculate_commission(subscription=new_sub, db=db)
                    
                    db.commit()
                    print(f"✅ Webhook: Subscription renewal processed for user {user.id}")

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
        price_id = get_stripe_price_id(request.plan_type)
        if not price_id:
            raise HTTPException(
                status_code=400, 
                detail=f"Price ID not configured or invalid plan type for: {request.plan_type}. Please set STRIPE_{request.plan_type.upper()}_PRICE_ID in environment."
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
                        # Safely handle potential None for current_period_end
                        period_end = updated_sub.get("current_period_end")
                        if period_end:
                            subscription.end_date = datetime.fromtimestamp(period_end)
                        else:
                            # Fallback if Stripe doesn't return the period end
                            _, end_date = calculate_subscription_dates(request.plan_type)
                            subscription.end_date = end_date
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
        
        # Handling subscription result
        print(f"📊 Subscription result: {subscription_result}")
        print(f"📊 Status: {subscription_result.get('status')}")
        print(f"📊 Subscription ID: {subscription_result.get('subscription_id')}")

        # Handle subscription status
        if subscription_result["status"] == "active":
            print(f"✅ Subscription is ACTIVE - creating database record...")
            
            # Subscription is active, create database record
            start_date, end_date = calculate_subscription_dates(request.plan_type)
            
            # Get pricing from settings
            from api.routes.control.settings import get_settings
            settings = get_settings(db=db, current_user=user)
            
            if request.plan_type == "monthly":
                amount = settings.monthly_price
            elif request.plan_type == "quarterly":
                amount = settings.quarterly_price
            else:
                amount = settings.yearly_price
            
            # Check if subscription already exists in database (idempotency)
            existing_subscription = db.query(Subscriptions).filter(
                Subscriptions.user_id == user_id,
                Subscriptions.transaction_id == subscription_result["subscription_id"]
            ).first()
            
            if existing_subscription:
                print(f"ℹ️  Subscription already exists in database: {existing_subscription.id}")
                return {
                    "status": "active",
                    "subscription_id": subscription_result["subscription_id"],
                    "subscription": existing_subscription
                }
            
            # Create new subscription record
            subscription = Subscriptions(
                user_id=user_id,
                subscription_plan=request.plan_type,
                transaction_id=subscription_result["subscription_id"],
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
            
            print(f"✅ Database subscription record created: ID {subscription.id}")
            
            # Update user
            if hasattr(user, 'subscription_status'):
                user.subscription_status = "active"
            if hasattr(user, 'subscription_plan'):
                user.subscription_plan = request.plan_type
            if hasattr(user, 'subscription_expires_at'):
                user.subscription_expires_at = end_date
            if hasattr(user, 'stripe_subscription_id'):
                user.stripe_subscription_id = subscription_result["subscription_id"]
            
            print(f"✅ User record updated")
            
            # Calculate commission
            from subscriptions.commission_service import CommissionService
            commission = CommissionService.calculate_commission(subscription=subscription, db=db)
            
            if commission:
                print(f"✅ Commission created: ${commission.amount}")
            
            db.commit()
            db.refresh(subscription)
            
            print(f"✅ Transaction committed to database")
            
            # Send success email
            background_tasks.add_task(
                email_service.send_payment_success_email,
                user.email,
                user.name,
                float(amount),
                request.plan_type,
                end_date.strftime("%B %d, %Y")
            )
            
            print(f"✅ Success email queued")
            
            return {
                "status": "active",
                "subscription_id": subscription_result["subscription_id"],
                "subscription": subscription
            }
            
        elif subscription_result["status"] == "incomplete":
            print(f"⚠️  Subscription INCOMPLETE - requires 3D Secure authentication")
            
            # Requires additional authentication (3D Secure)
            if not subscription_result.get("client_secret"):
                print(f"❌ ERROR: Subscription requires action but client_secret is missing.")
                raise HTTPException(
                    status_code=500,
                    detail="Subscription requires authentication but client_secret is missing"
                )
            
            return {
                "status": "requires_action",
                "subscription_id": subscription_result["subscription_id"],
                "payment_intent_id": subscription_result.get("payment_intent_id"),
                "client_secret": subscription_result.get("client_secret"),
                "message": "Additional authentication required"
            }
        else:
            print(f"❌ Unexpected subscription status: {subscription_result['status']}")
            raise HTTPException(
                status_code=400,
                detail=f"Subscription creation failed with status: {subscription_result['status']}"
            )
            
    except HTTPException:
        db.rollback()
        raise
    except stripe.error.StripeError as e:
        db.rollback()
        # Notify user of failure (payment specific)
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.PAYMENT_FAILED.value,
            title="Payment Failed",
            message=f"Your subscription payment failed: {str(e)}",
            link="/dashboard/upgrade"
        )
        print(f"Stripe Payment Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        print(f"Unexpected Subscription creation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/confirm-subscription")
async def confirm_subscription(
    request: ConfirmSubscriptionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm subscription after 3D Secure authentication
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
        else:
            user_id = current_user.id
        
        # Verify payment intent
        verification = StripeService.verify_payment(request.payment_intent_id)
        
        if verification["status"] != "succeeded":
            raise HTTPException(
                status_code=400,
                detail=f"Payment not successful. Status: {verification['status']}"
            )
        
        # Get subscription details to get current_period_end
        subscription_details = StripeService.retrieve_subscription(request.subscription_id)
        
        if subscription_details["status"] == "active":
            # Extract metadata from payment intent
            metadata = verification.get("metadata", {})
            plan_type = metadata.get("plan_type", "monthly")
            tx_ref = metadata.get("tx_ref", generate_tx_ref("STRIPE-SUB"))
            
            # Use subscription period from Stripe or fallback
            period_start = subscription_details.get("current_period_start")
            period_end = subscription_details.get("current_period_end")
            
            if period_start is not None and period_end is not None:
                try:
                    start_date = datetime.fromtimestamp(int(period_start))
                    end_date = datetime.fromtimestamp(int(period_end))
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error parsing Stripe timestamps: {str(e)}. Falling back to manual calculation.")
                    start_date, end_date = calculate_subscription_dates(plan_type)
            else:
                # Fallback: calculate manually if Stripe data is incomplete
                print(f"ℹ️  Stripe period data incomplete or None, calculating manually for {plan_type}")
                start_date, end_date = calculate_subscription_dates(plan_type)
            
            # Get pricing
            from api.routes.control.settings import get_settings
            user = db.query(User).filter(User.id == user_id).first()
            settings = get_settings(db=db, current_user=user)
            
            if plan_type == "monthly":
                amount = settings.monthly_price
            elif plan_type == "quarterly":
                amount = settings.quarterly_price
            else:
                amount = settings.yearly_price
            
            subscription = Subscriptions(
                user_id=user_id,
                subscription_plan=plan_type,
                transaction_id=request.subscription_id,  # Use subscription_id, not payment_intent_id
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
            if user:
                if hasattr(user, 'subscription_status'):
                    user.subscription_status = "active"
                if hasattr(user, 'subscription_plan'):
                    user.subscription_plan = plan_type
                if hasattr(user, 'subscription_expires_at'):
                    user.subscription_expires_at = end_date
                if hasattr(user, 'stripe_subscription_id'):
                    user.stripe_subscription_id = request.subscription_id
            
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
    except stripe.error.StripeError as e:
        db.rollback()
        print(f"Stripe Subscription Confirmation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        print(f"Unexpected Subscription Confirmation Error: {str(e)}")
        import traceback
        traceback.print_exc()
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


@router.post("/remove-card")
async def remove_card(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove user's saved card
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
            
        if not hasattr(user, 'stripe_payment_method_id') or not user.stripe_payment_method_id:
            raise HTTPException(status_code=400, detail="No saved card found to remove")
            
        # Detach from Stripe
        try:
            StripeService.detach_payment_method(user.stripe_payment_method_id)
        except Exception as e:
            print(f"⚠️ Warning: Could not detach from Stripe (might already be detached): {str(e)}")
            
        # Clear database fields
        user.stripe_payment_method_id = None
        user.card_last4 = None
        user.card_brand = None
        user.card_exp_month = None
        user.card_exp_year = None
        user.card_saved_at = None
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Card removed successfully"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error removing card: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

