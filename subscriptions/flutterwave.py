# subscriptions/flutterwave.py
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import os
import requests
from datetime import datetime
from typing import Annotated
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from decimal import Decimal, InvalidOperation

# import the database
from db.pg_connections import get_db
from db.pg_models import User, Subscriptions
# Change prefix to match your frontend URL
router = APIRouter(prefix="/api/payments", tags=["payments"])

# Flutterwave configuration
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"

Subscription_plans = {
    "monthly": {
        "amount": Decimal("29.95"),
        "currency": "USD",
        "duration_of_days":30
    },
    "yearly": {
        "amount": Decimal("99.95"),
        "currency": "USD",
        "duration_of_days": 365
    }
}

class PaymentVerifyRequest(BaseModel):
    transaction_id: str

@router.post("/flutterwave/verify")
async def verify_flutterwave_payment(verify_data: PaymentVerifyRequest, db:Annotated[Session, Depends(get_db)]):
    """
    Verify Flutterwave payment transaction
    """
    try:
        transaction_id = verify_data.transaction_id
        print(f"=== FLUTTERWAVE VERIFICATION ===")
        print(f"Transaction ID: {transaction_id}")
        print(f"Secret Key Present: {bool(FLUTTERWAVE_SECRET_KEY)}")
        
        if not FLUTTERWAVE_SECRET_KEY:
            raise HTTPException(
                status_code=500,
                detail="Flutterwave secret key not configured"
            )
        
        # Make request to Flutterwave API
        url = f"{FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/verify"
        headers = {
            "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"Making request to: {url}")
        response = requests.get(url, headers=headers)
        
        print(f"Flutterwave API response status: {response.status_code}")
        print(f"Flutterwave API response: {response.text}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Flutterwave API error: {response.text}"
            )
        
        data = response.json()
        
        # Check if verification was successful
        if data.get("status") == "success":
            transaction_data = data.get("data", {})
            
            # Check if payment was successful
            if transaction_data.get("status") == "successful":
                amount = transaction_data.get("amount")
                currency = transaction_data.get("currency")
                tx_ref = transaction_data.get("tx_ref")
                customer_email = transaction_data.get("customer", {}).get("email")

                try:
                    verified_amount = Decimal(str(amount)) # Convert to string first to avoid float conversion errors
                except InvalidOperation:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid amount received from Flutterwave API."
                    )
                
                current_plan = None
                plan_duration_days = None
                for name, plan_details in Subscription_plans.items():
                # --- MODIFIED: Direct Decimal comparison (no need for epsilon/tolerance) ---
                    if plan_details["currency"] == currency and plan_details["amount"] == verified_amount:
                        current_plan = name
                        plan_duration_days = plan_details["duration_of_days"]
                    break
        
                if not current_plan:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Verified amount {verified_amount} {currency} does not match any known subscription plan."
                    )
                print(f"✅ Payment verified successfully:")
                print(f"  Amount: {amount} {currency}")
                print(f"  TX Ref: {tx_ref}")
                print(f"  Customer: {customer_email}")
                
                # Update user subscription in database
                user = db.query(User).filter(User.email == customer_email).first()

                if not user: # --- ADDED: Handle User Not Found ---
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User with email {customer_email} not found in database."
                    )
                
                user.subscription_status = "active"
                user.subscription_plan = current_plan

                # Create New Subscription Record
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=plan_duration_days)

                # Check for Duplicate Transaction (Idempotency) --- RECOMMENDED ADDITION ---
                existing_sub = db.query(Subscriptions).filter(
                    (Subscriptions.tx_ref == tx_ref) | (Subscriptions.transaction_id == transaction_id)
                ).first()

                if existing_sub:
                    # If subscription already exists, return success without re-creating
                    print(f"⚠️ Transaction {tx_ref} already processed.")
                    return {
                        "status": "success",
                        "message": "Payment verified successfully (already processed).",
                        "data": {
                            "amount": str(verified_amount), 
                            "currency": currency,
                            "tx_ref": tx_ref,
                            "transaction_id": transaction_id,
                        }
                    }

                new_subscription = Subscriptions(
                    user_id=user.id,
                    tx_ref=tx_ref,
                    transaction_id=transaction_id,
                    # --- MODIFIED: Use the Decimal amount ---
                    amount_paid=verified_amount,
                    payment_provider="Flutterwave",
                    # ---------------------------------------
                    currency=currency,
                    subscription_plan=current_plan,
                    status="active",
                    start_date=start_date,
                    end_date=end_date )
                db.add(new_subscription)
                db.commit()
                db.refresh(user)

                print(f"✅ User {customer_email} updated to {current_plan} subscription.")
                
                return {
                    "status": "success",
                    "message": "Payment verified successfully",
                    "data": {
                        # --- MODIFIED: Convert Decimal back to string for JSON serialization ---
                        "amount": str(verified_amount), 
                        # ----------------------------------------------------------------------
                        "currency": currency,
                        "tx_ref": tx_ref,
                        "customer_email": customer_email,
                        "transaction_id": transaction_id,
                        "subscription_plan": current_plan,
                        "expires_on": end_date.isoformat()
                    }
                }
            else:
                print(f"❌ Payment not successful. Status: {transaction_data.get('status')}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Payment not successful. Status: {transaction_data.get('status')}"
                )
        else:
            print(f"❌ Verification failed. Response status: {data.get('status')}")
            raise HTTPException(
                status_code=400,
                detail="Verification failed"
            )
            
    except requests.RequestException as e:
        db.rollback()
        print(f"❌ Request error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to communicate with Flutterwave: {str(e)}"
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Payment verification failed: {str(e)}"
        )

@router.get("/health")
async def payment_health_check():
    """
    Check if payment system is configured correctly
    """
    return {
        "status": "healthy",
        "flutterwave_configured": bool(FLUTTERWAVE_SECRET_KEY),
        "public_key_configured": bool(FLUTTERWAVE_PUBLIC_KEY),
        "secret_key_prefix": FLUTTERWAVE_SECRET_KEY[:15] + "..." if FLUTTERWAVE_SECRET_KEY else None,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/test")
async def test_endpoint():
    """
    Simple test endpoint to verify routes are working
    """
    return {
        "status": "ok",
        "message": "Flutterwave payment routes are working",
        "endpoints": [
            "POST /api/payments/flutterwave/verify",
            "GET /api/payments/health",
            "GET /api/payments/test"
        ]
    }