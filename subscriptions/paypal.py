from fastapi import FastAPI, HTTPException, Request, Header, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)

router = APIRouter(prefix="", tags=["payments"])


# Pydantic models
class CreateOrderRequest(BaseModel):
    amount: str
    currency: str = "USD"

class CaptureRequest(BaseModel):
    order_id: str

# PayPal configuration
PAYPAL_MODE = os.getenv("Mode", "sandbox")
Client_Id = os.getenv("Client_Id")
PAYPAL_CLIENT_SECRET = os.getenv("Client_Secret")

API_BASE = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"

logger.info(f"PayPal Mode: {PAYPAL_MODE}")
logger.info(f"API Base: {API_BASE}")

async def get_access_token() -> str:
    """Get PayPal access token"""
    try:
        auth = base64.b64encode(f"{Client_Id}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE}/v1/oauth2/token",
                headers=headers,
                data={"grant_type": "client_credentials"}
            )
            r.raise_for_status()
            token = r.json()["access_token"]
            logger.info("✅ Access token obtained")
            return token
    except Exception as e:
        logger.error(f"❌ Failed to get access token: {str(e)}")
        raise

async def create_paypal_order(amount: str, currency: str = "USD") -> dict:
    """Create a PayPal order"""
    try:
        token = await get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": amount
                },
                "description": "Premium Plan"
            }]
        }
        
        logger.info(f"Creating order with amount: {amount} {currency}")
        logger.info(f"Using Client ID: {Client_Id[:10]}...") # Log partial Client ID
        logger.info(f"API Base: {API_BASE}")
        
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE}/v2/checkout/orders",
                headers=headers,
                json=body
            )
            r.raise_for_status()
            order_data = r.json()
            logger.info(f"✅ Order created: {order_data.get('id')}")
            logger.info(f"Full order response: {order_data}")
            return order_data
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ PayPal API error: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ Order creation failed: {str(e)}")
        raise

async def capture_paypal_order(order_id: str) -> dict:
    """Capture a PayPal order"""
    try:
        token = await get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Capturing order: {order_id}")
        logger.info(f"Using Client ID: {Client_Id[:10]}...")
        logger.info(f"API Base: {API_BASE}")
        
        # First, get order details to verify it exists
        async with httpx.AsyncClient() as client:
            # Get order details first
            try:
                get_response = await client.get(
                    f"{API_BASE}/v2/checkout/orders/{order_id}",
                    headers=headers
                )
                get_response.raise_for_status()
                order_details = get_response.json()
                logger.info(f"Order status: {order_details.get('status')}")
                logger.info(f"Order details: {order_details}")
            except Exception as e:
                logger.error(f"❌ Failed to get order details: {str(e)}")
                
            # Now capture
            r = await client.post(
                f"{API_BASE}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                json={}
            )
            r.raise_for_status()
            capture_data = r.json()
            logger.info(f"✅ Order captured successfully")
            logger.info(f"Capture data: {capture_data}")
            return capture_data
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Capture failed - Status: {e.response.status_code}")
        logger.error(f"❌ Capture failed - Response: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ Capture error: {str(e)}")
        raise

@router.post("/api/paypal/create-order")
async def api_create_order(body: CreateOrderRequest):
    """API endpoint to create PayPal order"""
    try:
        logger.info(f"📝 Received create order request: {body.amount} {body.currency}")
        order = await create_paypal_order(body.amount, body.currency)
        return {
            "id": order["id"],
            "links": order.get("links", [])
        }
    except httpx.HTTPStatusError as e:
        logger.exception("Create order failed")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
    except Exception as e:
        logger.exception("Unexpected error in create-order")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paypal/capture-order")
async def api_capture_order(body: CaptureRequest):
    """API endpoint to capture PayPal order"""
    try:
        logger.info(f"💰 Received capture request for order: {body.order_id}")
        capture = await capture_paypal_order(body.order_id)
        
        # Check capture status
        status = capture.get("status")
        logger.info(f"Capture status: {status}")
        
        return {
            "status": "success",
            "capture": capture
        }
    except httpx.HTTPStatusError as e:
        logger.exception("Capture order failed")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
    except Exception as e:
        logger.exception("Unexpected error in capture-order")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/paypal/webhook")
async def paypal_webhook(
    request: Request,
    paypal_transmission_id: str = Header(None),
    paypal_transmission_time: str = Header(None),
    paypal_cert_url: str = Header(None),
    paypal_auth_algo: str = Header(None),
    paypal_transmission_sig: str = Header(None)
):
    """PayPal webhook endpoint"""
    try:
        body_json = await request.json()
        logger.info(f"📨 Received webhook: {body_json.get('event_type')}")
        
        verify_body = {
            "transmission_id": paypal_transmission_id,
            "transmission_time": paypal_transmission_time,
            "cert_url": paypal_cert_url,
            "auth_algo": paypal_auth_algo,
            "transmission_sig": paypal_transmission_sig,
            "webhook_id": os.getenv("Webhook_Id"),
            "webhook_event": body_json
        }

        token = await get_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE}/v1/notifications/verify-webhook-signature",
                headers=headers,
                json=verify_body
            )
            r.raise_for_status()
            res = r.json()
            
            if res.get("verification_status") != "SUCCESS":
                logger.warning("⚠️ Webhook signature verification failed")
                return {"ok": False, "reason": "invalid signature"}
            
            event_type = body_json.get("event_type")
            logger.info(f"✅ Webhook verified: {event_type}")
            
            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                # Handle successful payment
                logger.info("💰 Payment capture completed")
                # TODO: Update your database here
                pass
                
            return {"ok": True}
    except Exception as e:
        logger.exception("Webhook processing failed")
        return {"ok": False, "reason": str(e)}

@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "paypal_mode": PAYPAL_MODE}

@router.get("/api/paypal/config")
async def get_paypal_config():
    """Get PayPal client configuration"""
    return {
        "client_id": Client_Id,
        "mode": PAYPAL_MODE
    }
