"""
Lavoo Voice Support AI Agent (LiveKit + NVIDIA NIM)

Connects to LiveKit Cloud WebRTC rooms and acts as a real-time conversational voice assistant
for Lavoo Customer Service using NVIDIA NIM (meta/llama-3.2-11b-vision-instruct) for rapid streaming
token generation.
"""

import os
import sys
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

logger = logging.getLogger("lavoo_voice_agent")
logging.basicConfig(level=logging.INFO)

# Voice-optimized system prompt: spoken-friendly, concise, no markdown tokens
VOICE_SUPPORT_PROMPT = """
You are the official Lavoo Voice Support Assistant.
You are having a real-time, two-way voice conversation with a user of Lavoo (an AI business decision engine and founder community).

CRITICAL VOICE CONVERSATION RULES:
1. Speak naturally, warmly, and concisely. Keep responses between 1 and 3 conversational sentences unless the user asks for a detailed breakdown.
2. DO NOT use markdown symbols, asterisks, bullet points, hashtags, or raw URLs since your output is spoken directly aloud to the user.
3. Be clear and helpful about Lavoo features:
   - Decision Engine: Evaluates business viability across 4 pillars (Viability, Monetization, Execution, Scalability) and generates execution roadmaps.
   - The Build Room: Collaborative founder community where builders solve problems and earn Chops.
   - The Signal: Curated market opportunities and business teardowns.
   - Earnings & Commissions: Affiliate referral program with 40% recurring revenue share.
   - Subscriptions: Free tier, Pro at $29/mo or $290/yr, and Premium at $79/mo or $790/yr.
4. SENSITIVE MATTERS: If the user asks for a refund, reports billing/charge disputes, or payout failures, empathetically explain that you will flag their ticket for a human administrator to process within 24 hours.
5. If you do not know something, politely ask them to describe their question further.
"""

def create_voice_agent():
    """
    Constructs and configures the LiveKit Voice Agent pipeline.
    """
    try:
        from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
        from livekit.agents.voice_assistant import VoiceAssistant
        from livekit.plugins import openai, silero
    except ImportError as e:
        logger.warning(f"LiveKit agent plugins not fully installed or in worker mode: {e}")
        return None

    nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")
    grok_api_key = os.getenv("XAI_API_KEY", "")

    # Configure LLM provider: Primary NVIDIA NIM with Grok fallback
    if nvidia_api_key:
        custom_llm = openai.LLM(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_api_key,
            model=os.getenv("CUSTOMER_SERVICE_NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct"),
            temperature=0.7,
        )
    elif grok_api_key:
        custom_llm = openai.LLM(
            base_url="https://api.x.ai/v1",
            api_key=grok_api_key,
            model=os.getenv("CUSTOMER_SERVICE_GROK_MODEL", "grok-4-1-fast-reasoning"),
            temperature=0.7,
        )
    else:
        custom_llm = openai.LLM()

    async def entrypoint(ctx: JobContext):
        logger.info(f"Connecting to room: {ctx.room.name}")
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        # Initialize voice assistant with Silero VAD (Voice Activity Detection)
        assistant = VoiceAssistant(
            vad=silero.VAD.load(),
            stt=openai.STT(), # or LiveKit Cloud hosted Deepgram
            llm=custom_llm,
            tts=openai.TTS(), # or LiveKit Cloud hosted Cartesia/ElevenLabs
            chat_ctx=llm.ChatContext().append(
                role="system",
                text=VOICE_SUPPORT_PROMPT
            ),
        )

        assistant.start(ctx.room)
        await assistant.say("Hello! I am your Lavoo voice support assistant. How can I help you today?", allow_interruptions=True)

    return entrypoint

if __name__ == "__main__":
    from livekit.agents import WorkerOptions, cli
    entrypoint = create_voice_agent()
    if entrypoint:
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    else:
        print("LiveKit Voice Agent entrypoint could not be initialized.")
