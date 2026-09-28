"""
Test script for the new POST /customer-service/voice/chat endpoint.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

def test_nvidia_voice_generation():
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    print(f"Testing with NVIDIA_API_KEY: {nvidia_key[:8]}...")

    from openai import OpenAI
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=nvidia_key,
        timeout=15.0
    )

    prompt = (
        "You are the official Lavoo Voice Support Assistant having a real-time spoken voice conversation with a founder.\n\n"
        "SPOKEN VOICE CONVERSATION RULES:\n"
        "1. Speak naturally, warmly, and concisely. Keep responses between 1 and 3 conversational sentences so they sound natural when spoken aloud.\n"
        "2. STRICTLY DO NOT use markdown symbols, asterisks, hashtags, bullet points, or raw URLs. Format everything as clean spoken text.\n"
        "3. Core Lavoo platform context:\n"
        "   - Decision Engine: Evaluates business viability across 4 pillars.\n"
        "   - The Build Room: Collaborative founder community.\n"
        "   - Earnings: 40% recurring affiliate commissions.\n"
    )

    completion = client.chat.completions.create(
        model="meta/llama-3.2-11b-vision-instruct",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Hi, how can I use the decision engine to evaluate my idea?"}
        ],
        temperature=0.7,
        max_tokens=200
    )

    reply = completion.choices[0].message.content
    print("\n[AI Voice Spoken Reply]:")
    print(reply)
    assert len(reply) > 10, "Response too short"
    print("\nVoice chat generation test passed!")

if __name__ == "__main__":
    test_nvidia_voice_generation()
