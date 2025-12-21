
# api/routes/stripe_connect.py
"""
Stripe Connect integration for user payouts
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import stripe
import os
from datetime import datetime

from db.pg_connections import get_db
from db.pg_models import User, PayoutAccount
from api.routes.login import get_current_user

from dotenv import load_dotenv
import json
load_dotenv()
print("✅ Environment variables loaded for Stripe Connect")

router = APIRouter(prefix="/api/stripe/connect", tags=["stripe-connect"])

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000") # Remember to change this to the live URL in production   


def extract_user_from_token(current_user):
    """Extract user from token response"""
    if isinstance(current_user, dict):
        if "user" in current_user:
            user_data = current_user["user"]
            if isinstance(user_data, dict):
                return user_data
            elif hasattr(user_data, 'id'):
                return {
                    "id": user_data.id,
                    "email": user_data.email,
                    "name": user_data.name
                }
        return current_user
    else:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name
        }


@router.post("/onboard")
async def create_stripe_connect_account(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Connect account WITHOUT hardcoded bank details."""
    try:
        user_data = extract_user_from_token(current_user)
        user_id = user_data.get("id")
        user_email = user_data.get("email")

        print(f"[Stripe Connect] Creating account for user {user_id}")

        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()

        stripe_account_id = None

        # 1. Check for an existing account (Your existing logic)
        if payout_account and payout_account.stripe_account_id:
            stripe_account_id = payout_account.stripe_account_id
            print(f"[Stripe Connect] Existing account found: {stripe_account_id}")
            try:
                account = stripe.Account.retrieve(stripe_account_id)
                if account.details_submitted:
                    return {
                        "status": "already_connected",
                        "message": "Stripe account already connected",
                        "account_id": stripe_account_id
                    }
            except stripe.error.InvalidRequestError:
                stripe_account_id = None  # Account invalid, create new

        # 2. Create a NEW Stripe Express account (CLEANED VERSION)
        if not stripe_account_id:
            # The user will provide all details in the Stripe-hosted onboarding.
            account = stripe.Account.create(
                type="express",
                country="US",
                email=user_email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_type="individual",
                metadata={
                    "user_id": str(user_id),
                    "platform": "AI_Strategy_Pro"
                }
            )
            stripe_account_id = account.id
            print(f"[Stripe Connect] New account created: {stripe_account_id}")

            # Save to database with initial 'pending' status
            if not payout_account:
                payout_account = PayoutAccount(user_id=user_id)
                db.add(payout_account)

            payout_account.stripe_account_id = stripe_account_id
            payout_account.stripe_account_status = "pending"  # Initial state
            payout_account.default_payout_method = "stripe"
            payout_account.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(payout_account)

        # 3. Generate the onboarding link for the user
        account_link = stripe.AccountLink.create(
            account=stripe_account_id,
            refresh_url=f"{BASE_URL}/dashboard/upgrade?refresh=true",
            return_url=f"{BASE_URL}/dashboard/upgrade?success=true",
            type="account_onboarding",
        )
        print(f"[Stripe Connect] Onboarding URL generated.")
        return {
            "status": "success",
            "onboarding_url": account_link.url,
            "account_id": stripe_account_id
        }

    except stripe.error.StripeError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/account-status")
async def get_stripe_account_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status of user's Stripe Connect account
    """
    try:
        user_data = extract_user_from_token(current_user)
        user_id = user_data.get("id")
        
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        if not payout_account or not payout_account.stripe_account_id:
            return {
                "status": "not_connected",
                "message": "No Stripe account connected"
            }
        
        # Retrieve account from Stripe
        account = stripe.Account.retrieve(payout_account.stripe_account_id)
        
        # Update status in database
        if account.details_submitted:
            payout_account.stripe_account_status = "verified"
            payout_account.is_verified = True
            payout_account.verified_at = datetime.utcnow()
        elif account.charges_enabled:
            payout_account.stripe_account_status = "active"
        else:
            payout_account.stripe_account_status = "pending"
        
        db.commit()
        
        return {
            "status": "connected",
            "account_id": payout_account.stripe_account_id,
            "account_status": payout_account.stripe_account_status,
            "details_submitted": account.details_submitted,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/refresh-onboarding")
async def refresh_stripe_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate new onboarding link if user needs to complete setup
    """
    try:
        user_data = extract_user_from_token(current_user)
        user_id = user_data.get("id")
        
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        if not payout_account or not payout_account.stripe_account_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Stripe account found. Please start onboarding first."
            )
        
        # Create new account link
        account_link = stripe.AccountLink.create(
            account=payout_account.stripe_account_id,
            refresh_url=f"{BASE_URL}/dashboard/upgrade?refresh=true",
            return_url=f"{BASE_URL}/dashboard/upgrade?success=true",
            type="account_onboarding",
        )
        
        return {
            "status": "success",
            "onboarding_url": account_link.url
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/disconnect")
async def disconnect_stripe_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Stripe Connect account
    """
    try:
        user_data = extract_user_from_token(current_user)
        user_id = user_data.get("id")
        
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        if not payout_account or not payout_account.stripe_account_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Stripe account to disconnect"
            )
        
        stripe_account_id = payout_account.stripe_account_id
        
        # Delete Stripe account
        try:
            stripe.Account.delete(stripe_account_id)
        except stripe.error.InvalidRequestError:
            # Account already deleted or doesn't exist
            pass
        
        # Clear from database
        payout_account.stripe_account_id = None
        payout_account.stripe_account_status = None
        
        # Only clear default method if it was Stripe
        if payout_account.default_payout_method == "stripe":
            payout_account.default_payout_method = None
            payout_account.is_verified = False
            payout_account.verified_at = None
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Stripe account disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/webhook")
async def stripe_connect_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    UPDATED: Handle Stripe Connect webhooks, especially account.updated.
    This is where your database status updates automatically.
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        # Get your webhook secret from environment
        webhook_secret = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET")

        # Verify the event in production/live testing. For initial local CLI testing,
        # you can construct the event without verification.
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        else:
            # For local development with Stripe CLI, you can bypass signature check.
            # WARNING: Do NOT use this in production.
            event_data = json.loads(payload)
            event = stripe.Event.construct_from(event_data, stripe.api_key)

        # Handle the specific event type
        if event.type == "account.updated":
            account = event.data.object
            print(f"[Webhook] Received account.updated for: {account.id}")

            # Find the corresponding payout account in your database
            payout_account = db.query(PayoutAccount).filter(
                PayoutAccount.stripe_account_id == account.id
            ).first()

            if payout_account:
                # Update your database based on the live Stripe account status
                payout_account.stripe_account_status = "active" if account.charges_enabled else "pending"
                payout_account.charges_enabled = account.charges_enabled
                payout_account.payouts_enabled = account.payouts_enabled
                payout_account.details_submitted = account.details_submitted
                payout_account.updated_at = datetime.utcnow()

                if account.charges_enabled and account.payouts_enabled:
                    payout_account.is_verified = True
                    payout_account.verified_at = datetime.utcnow()
                    print(f"[Webhook] Account {account.id} marked as ACTIVE.")

                db.commit()

        # Return a 200 status quickly to acknowledge receipt[citation:1]
        return {"status": "success", "event": event.type}

    except stripe.error.SignatureVerificationError as e:
        print(f"[Webhook ERROR] Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        print(f"[Webhook ERROR] {str(e)}")
        # Still return 200 to prevent Stripe retries for unexpected errors[citation:1]
        return {"status": "error_acknowledged", "message": str(e)}


@router.post("/test/fix-restricted-account/{account_id}")
async def fix_restricted_test_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """
    TEST MODE ONLY: Force a restricted test account to active status.
    This bypasses normal verification flow for testing.
    """
    try:
        # Security: Only allow in test mode
        if not stripe.api_key or not stripe.api_key.startswith("sk_test_"):
            raise HTTPException(
                status_code=403,
                detail="This endpoint is only available in test mode"
            )
        
        print(f"[Test] Fixing restricted account: {account_id}")
        
        # 1. FIRST, update the Stripe account to active
        try:
            # This is the key part: Use special test parameters
            account = stripe.Account.modify(
                account_id,
                # These parameters simulate completed verification
                business_type="individual",
                individual={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "phone": "+15005550000",
                    "address": {
                        "line1": "123 Test St",
                        "city": "San Francisco",
                        "state": "CA",
                        "postal_code": "94103",
                        "country": "US"
                    },
                    "dob": {
                        "day": 1,
                        "month": 1,
                        "year": 1990
                    },
                    "ssn_last_4": "0000"
                },
                # Accept terms of service (test mode)
                tos_acceptance={
                    "date": int(datetime.utcnow().timestamp()),
                    "ip": "127.0.0.1"
                },
                # Enable capabilities
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True}
                },
                # Set payout schedule
                settings={
                    "payouts": {
                        "schedule": {"interval": "manual"}
                    }
                }
            )
            print(f"[Test] Stripe account updated: {account_id}")
        except stripe.error.StripeError as e:
            print(f"[Test] Stripe API error: {str(e)}")
            # Even if Stripe fails, we can still update our database for testing
        
        # 2. Update YOUR database regardless
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.stripe_account_id == account_id
        ).first()
        
        if payout_account:
            # Force to active in our system
            payout_account.stripe_account_status = "active"
            payout_account.charges_enabled = True
            payout_account.payouts_enabled = True
            payout_account.is_verified = True
            payout_account.verified_at = datetime.utcnow()
            payout_account.verification_error = None  # Clear any errors
            
            db.commit()
            print(f"[Test] Database updated to 'active' for: {account_id}")
            
            return {
                "status": "success",
                "message": "Account force-verified for testing",
                "account_id": account_id,
                "stripe_status": "active",
                "note": "Test mode bypass - not for production"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No payout account found for Stripe ID: {account_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[Test ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fix restricted account: {str(e)}"
        )