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
        Verify a payment intent or setup intent status
        """
        try:
            if payment_intent_id.startswith("seti_"):
                # Handle SetupIntent
                intent = stripe.SetupIntent.retrieve(payment_intent_id)
                return {
                    "status": intent.status,
                    "amount": 0,  # Setup intents don't have amounts
                    "currency": "USD",
                    "payment_method": intent.payment_method,
                    "customer_email": None,
                    "metadata": intent.metadata
                }
            else:
                # Handle PaymentIntent
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
            raise e
    
    @staticmethod
    def create_subscription_with_saved_card(
        customer_id: str,
        price_id: str,
        payment_method_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create subscription with saved payment method
        FIXED: Handles missing current_period_end for incomplete subscriptions
        """
        try:
            print(f"🔵 Creating subscription for customer {customer_id} with price {price_id}")
            
            # Create subscription - DO NOT expand invoice (causes API version issues)
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
                payment_behavior="default_incomplete",
                payment_settings={
                    "save_default_payment_method": "on_subscription",
                    "payment_method_types": ["card"]
                },
                metadata=metadata or {}
            )
            
            print(f"✅ Subscription created: {subscription.id}, status: {subscription.status}")
            
            # Extract client_secret for 3D Secure
            client_secret = None
            payment_intent_id = None
            
            # For incomplete subscriptions, get the latest invoice and payment intent
            if subscription.status in ["incomplete", "past_due"]:
                latest_invoice_id = subscription.latest_invoice
                
                if latest_invoice_id:
                    print(f"🔄 Retrieving invoice {latest_invoice_id} for payment intent...")
                    try:
                        # Retrieve invoice WITHOUT expansion to avoid API version issues
                        invoice = stripe.Invoice.retrieve(latest_invoice_id)
                        
                        # Get payment intent ID from invoice
                        # Note: New API uses 'payment_intent' as an ID string, not an object
                        pi_id = getattr(invoice, 'payment_intent', None)
                        
                        if pi_id:
                            if isinstance(pi_id, str):
                                payment_intent_id = pi_id
                            else:
                                payment_intent_id = pi_id.id
                            
                            # Retrieve the full payment intent
                            print(f"💳 Retrieving PaymentIntent {payment_intent_id}...")
                            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                            client_secret = payment_intent.client_secret
                            print(f"✅ Got client_secret from PaymentIntent")
                            
                    except Exception as e:
                        print(f"⚠️ Invoice retrieval method 1 failed: {str(e)}")
                
                # Fallback: Search recent payment intents
                if not client_secret:
                    print(f"🔍 Searching payment intents for customer {customer_id}...")
                    try:
                        recent_intents = stripe.PaymentIntent.list(
                            customer=customer_id,
                            limit=5
                        )
                        
                        for intent in recent_intents.data:
                            if intent.status in ["requires_action", "requires_payment_method", "requires_confirmation"]:
                                payment_intent_id = intent.id
                                client_secret = intent.client_secret
                                print(f"✅ Found matching payment intent: {payment_intent_id}")
                                break
                    except Exception as e:
                        print(f"⚠️ Failed to search payment intents: {str(e)}")
                
                # If still no client_secret, this is an error
                if not client_secret:
                    print(f"❌ ERROR: Subscription requires action but no client_secret found")
                    return {
                        "subscription_id": subscription.id,
                        "status": "requires_action",
                        "client_secret": None,
                        "current_period_end": None,
                        "payment_intent_id": None,
                        "error": "Unable to retrieve payment authentication details. Please try again."
                    }
            
            # Get current_period_end safely (might not exist for incomplete subscriptions)
            current_period_end = getattr(subscription, 'current_period_end', None)
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "client_secret": client_secret,
                "current_period_end": current_period_end,
                "payment_intent_id": payment_intent_id
            }
            
        except stripe.error.CardError as e:
            print(f"❌ Card error: {str(e)}")
            raise e
        except stripe.error.InvalidRequestError as e:
            print(f"❌ Invalid request: {str(e)}")
            raise e
        except stripe.error.StripeError as e:
            print(f"❌ Stripe error: {str(e)}")
            raise e
    
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
                "current_period_start": getattr(subscription, 'current_period_start', None),
                "current_period_end": getattr(subscription, 'current_period_end', None),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at,
                "items": [{
                    "price_id": item.price.id,
                    "interval": item.price.recurring.interval if item.price.recurring else None
                } for item in subscription["items"].data]
            }
            
        except stripe.error.StripeError as e:
            raise e
    
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
            raise e
    
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
                "current_period_end": getattr(subscription, 'current_period_end', None)
            }
            
        except stripe.error.StripeError as e:
            raise e
    
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
            raise e
    
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

    @staticmethod
    def detach_payment_method(payment_method_id: str) -> Dict[str, Any]:
        """
        Detach a payment method from a customer
        """
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            return {
                "status": "success",
                "payment_method_id": payment_method.id
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Payment method detachment error: {str(e)}")