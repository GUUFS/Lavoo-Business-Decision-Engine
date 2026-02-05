import stripe
import os
from typing import Dict, Any, Optional
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
                "customer_email": intent.receipt_email,
                "metadata": intent.metadata
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
        # Try multiple keys as fallback
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            webhook_secret = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET")
        if not webhook_secret:
            webhook_secret = os.getenv("STRIPE_PLATFORM_WEBHOOK_SECRET")
        
        if not webhook_secret:
            raise Exception("STRIPE_WEBHOOK_SECRET (or CONNECT/PLATFORM variant) is not set in environment variables")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")
    
    # ============================================================================
    # SUBSCRIPTION MANAGEMENT WITH SAVED CARDS
    # ============================================================================
    
    @staticmethod
    def get_or_create_customer(
        user_id: int,
        email: str,
        name: str,
        stripe_customer_id: Optional[str] = None
    ) -> str:
        """
        Get existing Stripe customer or create new one
        Returns customer ID
        """
        try:
            if stripe_customer_id:
                # Verify customer exists
                try:
                    customer = stripe.Customer.retrieve(stripe_customer_id)
                    return customer.id
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist, create new one
                    pass
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "user_id": str(user_id),
                    "platform": "lavoo_bi"
                }
            )
            return customer.id
            
        except stripe.error.StripeError as e:
            raise Exception(f"Customer creation error: {str(e)}")
    
    @staticmethod
    def attach_payment_method(
        payment_method_id: str,
        customer_id: str,
        set_as_default: bool = True
    ) -> Dict[str, Any]:
        """
        Attach payment method to customer and optionally set as default
        """
        try:
            # Attach payment method
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Set as default if requested
            if set_as_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id,
                    },
                )
            
            return {
                "status": "success",
                "payment_method_id": payment_method_id,
                "customer_id": customer_id
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Payment method attachment error: {str(e)}")
    
    @staticmethod
    def create_subscription_with_saved_card(
        customer_id: str,
        price_id: str,
        payment_method_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create subscription with saved payment method
        This is used for the new checkout flow with card storage
        """
        try:
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
                payment_behavior="default_incomplete",
                payment_settings={
                    "save_default_payment_method": "on_subscription"
                },
                expand=["latest_invoice.payment_intent"],
                metadata=metadata or {}
            )
            
            # Get payment intent for potential 3D Secure
            latest_invoice = subscription.latest_invoice
            payment_intent = latest_invoice.payment_intent if latest_invoice else None
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "client_secret": payment_intent.client_secret if payment_intent else None,
                "current_period_end": subscription.current_period_end,
                "payment_intent_id": payment_intent.id if payment_intent else None
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Subscription creation error: {str(e)}")
    
    @staticmethod
    def retrieve_subscription(subscription_id: str) -> Dict[str, Any]:
        """
        Retrieve subscription details
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at,
                "items": [{
                    "price_id": item.price.id,
                    "interval": item.price.recurring.interval if item.price.recurring else None
                } for item in subscription.items.data]
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Subscription retrieval error: {str(e)}")
    
    @staticmethod
    def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """
        Cancel subscription
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Subscription cancellation error: {str(e)}")
    
    @staticmethod
    def update_subscription_price(
        subscription_id: str,
        new_price_id: str,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """
        Update subscription to different plan (upgrade/downgrade)
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='always_invoice' if prorate else 'none',
            )
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Subscription update error: {str(e)}")
    
    @staticmethod
    def get_customer_payment_methods(customer_id: str) -> list:
        """
        Get all payment methods for a customer
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return [{
                "id": pm.id,
                "brand": pm.card.brand,
                "last4": pm.card.last4,
                "exp_month": pm.card.exp_month,
                "exp_year": pm.card.exp_year
            } for pm in payment_methods.data]
            
        except stripe.error.StripeError as e:
            raise Exception(f"Payment methods retrieval error: {str(e)}")
    
    @staticmethod
    def create_setup_intent(customer_id: str) -> Dict[str, Any]:
        """
        Create setup intent for adding new payment method without immediate charge
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"],
            )
            
            return {
                "client_secret": setup_intent.client_secret,
                "setup_intent_id": setup_intent.id
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Setup intent creation error: {str(e)}")