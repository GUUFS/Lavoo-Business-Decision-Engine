"""
Meta Conversions API: sends the ad events from our server too, not only
from the browser's Meta Pixel (components/MetaPixel.tsx in the main app).

Why both: ad blockers and Safari often stop the browser Pixel. The server
copy still reaches Meta. Each event carries the same `event_id` from both
sides, so Meta counts it once.

Events (from the ad brief):
  ViewContent           landing page opens            (browser, relayed here)
  StartCheckup          "Run my free check-up" tapped (browser + server)
  ViewResult            the result page shows         (browser, relayed here)
  ViewGate              the sign-up card shows        (browser, relayed here)
  CompleteRegistration  they create their account     (server, on claim)
  Purchase              a Flutterwave payment succeeds (server)

Does nothing unless META_PIXEL_ID and META_CAPI_TOKEN are set. Never raises:
tracking must never break a check-up or a payment.
"""
import hashlib
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
# The only events the public relay accepts (so nobody can send made-up ones).
BROWSER_EVENTS = {"ViewContent", "StartCheckup", "ViewResult", "ViewGate"}


def _sha256(value: str | None) -> str | None:
    """Meta wants emails trimmed, lower-case and hashed, never as plain text."""
    if not value:
        return None
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def is_configured() -> bool:
    """True when both the Pixel id and the access token are set."""
    return bool(os.getenv("META_PIXEL_ID") and os.getenv("META_CAPI_TOKEN"))


def send_event(event_name: str, event_id: str | None = None, *, email: str | None = None,
               external_id: str | int | None = None, ip: str | None = None, user_agent: str | None = None,
               fbp: str | None = None, fbc: str | None = None, source_url: str | None = None,
               custom_data: dict | None = None) -> bool:
    """Send one event to Meta. Returns True if Meta accepted it. Never raises."""
    # 1. Not set up: nothing to send.
    if not is_configured():
        return False
    try:
        # 2. Who did it (hashed where Meta asks for hashing; empty values left out).
        user_data = {
            "em": [_sha256(email)] if email else None,
            "external_id": [_sha256(str(external_id))] if external_id else None,
            "client_ip_address": ip,
            "client_user_agent": user_agent,
            "fbp": fbp,
            "fbc": fbc,
        }
        event = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "action_source": "website",
            "user_data": {k: v for k, v in user_data.items() if v},
        }
        # 3. The shared id (so the browser and server copies count once), page and details.
        if event_id:
            event["event_id"] = event_id
        if source_url:
            event["event_source_url"] = source_url
        if custom_data:
            event["custom_data"] = custom_data
        # 4. Post it to Meta.
        response = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{os.getenv('META_PIXEL_ID')}/events",
            params={"access_token": os.getenv("META_CAPI_TOKEN")},
            json={"data": [event]},
            timeout=5,
        )
        if response.status_code != 200:
            logger.warning(f"[meta-capi] {event_name} refused: {response.status_code} {response.text[:300]}")
            return False
        return True
    except Exception as exc:
        logger.warning(f"[meta-capi] {event_name} not sent: {exc}")
        return False
