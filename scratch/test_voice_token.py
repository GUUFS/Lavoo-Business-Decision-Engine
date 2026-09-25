"""
Verification script for LiveKit Voice token generation and room verification.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

from livekit.api import AccessToken, VideoGrants

def test_token():
    url = os.getenv("LIVEKIT_URL", "wss://car-service-provider-3lj5cuhr.livekit.cloud")
    key = os.getenv("LIVEKIT_API_KEY", "APIeLDUXJAVzbFq")
    secret = os.getenv("LIVEKIT_API_SECRET", "uyExBRIXqf9D2euQfZl3UKeZIUcIoewVq5nsqHNSthqH")

    print(f"Testing LiveKit URL: {url}")
    print(f"Testing API Key: {key[:6]}...")

    token = (
        AccessToken(key, secret)
        .with_identity("test-user-42")
        .with_name("Lavoo Test Founder")
        .with_grants(VideoGrants(
            room_join=True,
            room="support-ticket-101",
            can_publish=True,
            can_subscribe=True,
        ))
        .to_jwt()
    )

    print(f"Generated JWT successfully (length={len(token)})")
    assert len(token) > 50, "Token is too short"
    print("Token validation passed!")

if __name__ == "__main__":
    test_token()
