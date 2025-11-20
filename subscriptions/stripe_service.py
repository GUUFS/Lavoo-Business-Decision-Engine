
import stripe
import os
from typing import Dict, Any
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    
    @staticmethod
    def create_payment_intent(
        amount: Decimal,
        currency: str = "usd",
        customer_email: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent
        Amount should be in dollars (e.g., 29.95)
        """
        try:
            # Convert amount to cents (Stripe uses smallest currency unit)
            amount_in_cents = int(amount * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                receipt_email=customer_email,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            return {
                "clientSecret": intent.client_secret,
                "paymentIntentId": intent.id,
                "amount": amount,
                "currency": currency
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    @staticmethod
    def verify_payment(payment_intent_id: str) -> Dict[str, Any]:
        """
        Verify a payment intent status
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "status": intent.status,
                "amount": intent.amount / 100,  # Convert back to dollars
                "currency": intent.currency,
                "payment_method": intent.payment_method,
                "customer_email": intent.receipt_email
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe verification error: {str(e)}")
    
    @staticmethod
    def create_refund(payment_intent_id: str, amount: float = None) -> Dict[str, Any]:
        """
        Create a refund for a payment
        """
        try:
            refund_data = {"payment_intent": payment_intent_id}
            
            if amount:
                refund_data["amount"] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Refund error: {str(e)}")
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")