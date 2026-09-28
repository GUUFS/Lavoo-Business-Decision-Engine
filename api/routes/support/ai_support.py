"""
Lavoo AI Support Copilot & Sensitivity Escalation Engine

Provides human-sounding, hyper-accurate customer support replies grounded in
the full Lavoo platform knowledge base (Decision Engine, Build Room, The Signal,
Earnings, Subscriptions, Badges/Chops), while automatically escalating sensitive
matters (refunds, payout failures, account compromise, disputes) to human administrators.
"""

import os
import re
import logging
from typing import Tuple, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.pg_connections import SessionLocal
from database.pg_models import Ticket, TicketMessage, User, UserNotification

logger = logging.getLogger(__name__)

# ─── LAVOO PLATFORM KNOWLEDGE BASE ────────────────────────────────────────────
LAVOO_KNOWLEDGE_BASE = """
LAVOO PLATFORM MASTER KNOWLEDGE BASE:

1. CORE IDENTITY:
Lavoo is an AI-powered business decision intelligence and execution platform for solo founders, builders, and entrepreneurs. It helps founders validate business ideas, turn strategic insights into actionable execution missions, learn from business teardowns, and connect with other builders.

2. KEY FEATURES & PRODUCTS:
- DECISION ENGINE (/l/decision-engine):
  * Evaluates business ideas across 4 Pillars: Viability, Monetization, Execution, and Scalability.
  * Generates an overall Viability Score (0-100), SWOT analysis, competitive matrix, and step-by-step Execution Roadmap.
  * Allows converting roadmap milestones into actionable Missions (/l/decision-engine/missions).
  * Founders can complete missions and post Founder Reflections directly to the Build Room.

- THE BUILD ROOM (/l/thebuildroom):
  * Founder community where builders share updates, polls, milestones, and questions.
  * Questions posted by Paid/Pro/Premium founders automatically receive an intelligent strategic answer from VOO (the AI advisor) after 10 minutes.
  * Polls allow multiple options and time durations (e.g. 24h, 3d, 7d).
  * Chops Rewards: Founders earn +10 Chops for creating a discussion and +5 Chops for marking their question resolved.

- THE SIGNAL (/l/thesignal):
  * Curated business teardowns, market opportunities, and founder case studies.
  * Users can read, bookmark, react, and subscribe for weekly market signals.

- EARNINGS & COMMISSIONS (/l/earnings):
  * Referral affiliate program where users earn recurring commissions by sharing their unique referral link.
  * Includes a Level / Tier Calculator estimating monthly earnings based on referrals.
  * Payouts are processed to user bank accounts once the minimum payout threshold is reached.

- BADGES & CHOPS REWARDS (/l/badges):
  * Chops (₵) is the platform reputation currency earned through active participation, missions, and community problem-solving.
  * Badges are awarded for milestones (e.g. First Post, Roadmap Master, Top Contributor).

- CUSTOMER SUPPORT HUB (/l/customer-service):
  * Two-pane support desk where users submit tickets across Billing, Technical, Account, Feature Ideas, and General Inquiries.
  * Users can mark tickets resolved or reopen them anytime.

- SUBSCRIPTION TIERS (/l/upgrade):
  * Free Plan: Basic idea validation, access to Build Room reading and public signals.
  * Pro Plan: Unlimited deep evaluations, execution roadmap generation, Voo AI answers on community questions, and full Signal library access.
  * Premium / Lifetime Plan: Priority AI compute, advanced market simulation, custom financial modeling, and VIP support desk access.
  * Payments are powered securely by Stripe, Flutterwave, and PayPal.

3. SUPPORT PRINCIPLES & VOICE:
- Tone: Warm, empathetic, professional, confident, and direct. You write like a seasoned human customer support engineer and founder colleague.
- Never say "I am an AI", "As an AI model", or "Certainly! Here are some steps:".
- Write naturally with clear, friendly greetings (e.g., "Hi {name}," or "Hey {name},").
- Break answers into 2 to 3 concise, digestible paragraphs with 2-line spacing (\\n\\n) between paragraphs.
- Never use em-dashes (—). Use natural commas, colons, periods, or clean sentences.
"""

# ─── SENSITIVITY CLASSIFIER ───────────────────────────────────────────────────
# Sensitive requests must NOT be auto-answered; they require human admin review.
SENSITIVE_PATTERNS = [
    # Financial / Refunds / Disputes
    r"\b(refund|refunds|chargeback|chargebacks|dispute|disputes)\b",
    r"\b(charged twice|double charged|unauthorized charge|wrong charge|overcharged)\b",
    r"\b(cancel my subscription and refund|money back|reimburse|reimbursement)\b",
    r"\b(billing error|stolen card|fraudulent charge)\b",

    # Payouts / Banking failures
    r"\b(payout failed|payout missing|haven't received my payout|withdrawal failed)\b",
    r"\b(bank transfer failed|commission missing|payout stuck|send my money)\b",

    # Security & Account Takeover
    r"\b(hacked|account stolen|compromised|unauthorized access|someone logged into)\b",
    r"\b(change my email|lost access to email|2fa locked|security breach)\b",

    # Explicit Human Admin Requests
    r"\b(talk to a human|speak with a human|real person|human agent|talk to founder|talk to ceo)\b",
    r"\b(legal action|lawyer|sue|court)\b",
]


def _classify_support_sensitivity(category: str, issue_text: str) -> Tuple[bool, str]:
    """
    Checks if a ticket requires human administrator handling.
    Returns (is_sensitive, reason_explanation).
    """
    text = f"{category} {issue_text}".lower()

    for pattern in SENSITIVE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, f"Matched sensitive pattern: '{match.group(0)}'"

    # Short or empty issues with ambiguous billing/technical demands
    if len(issue_text.strip()) < 8 and category in ["billing", "account"]:
        return True, "Short ambiguous financial/account inquiry"

    return False, "Standard inquiry eligible for automated AI support"


# ─── RESPONSE NORMALIZATION ───────────────────────────────────────────────────
def _normalize_support_paragraphs(text: str) -> str:
    """
    Ensures paragraphs are separated by double newlines (\\n\\n) with no em-dashes.
    """
    if not text:
        return ""
    # Strip em-dashes
    clean = text.replace("—", ", ").replace("–", "-")
    # Split non-empty lines and join with double newline
    chunks = [c.strip() for c in clean.split("\n") if c.strip()]
    return "\n\n".join(chunks)


# ─── RESPONSE GENERATOR ───────────────────────────────────────────────────────
def _generate_humanized_support_reply(
    user_name: str,
    user_email: str,
    category: str,
    issue_text: str,
    ticket_id: int,
    conversation_history: Optional[str] = None
) -> str:
    """
    Generates a human-written, warm, and accurate support answer using NVIDIA NIM LLM
    (or xAI Grok as configurable toggle/fallback).
    """
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    xai_key = os.getenv("XAI_API_KEY")
    preferred_provider = os.getenv("CUSTOMER_SERVICE_LLM_PROVIDER", os.getenv("VOO_LLM_PROVIDER", "")).strip().lower()

    if not preferred_provider:
        preferred_provider = "nvidia" if nvidia_key else "grok"

    display_name = user_name.strip() if user_name else "there"

    fallback_reply = (
        f"Hi {display_name},\n\n"
        f"Thanks for reaching out to us. I have looked into your inquiry regarding **{category.capitalize()}**.\n\n"
        f"To resolve this quickly, please check that you are on the latest version of the dashboard and try refreshing your browser. If you are referencing a specific mission or idea evaluation, navigating to `/l/decision-engine` will allow you to access your latest saved data.\n\n"
        f"Please let me know if this helps or if you need any further assistance. We are happy to help!"
    )

    if not nvidia_key and not xai_key:
        return _normalize_support_paragraphs(fallback_reply)

    system_prompt = (
        "You are a helpful, empathetic, and knowledgeable Senior Support Specialist on the Lavoo team replying to a user support ticket. "
        "Your replies must sound 100% human, personal, and authentic.\n\n"
        "STRICT RULES:\n"
        "1. NEVER identify as an AI, bot, or language model. Write as an actual human team member on the Lavoo engineering & support team.\n"
        "2. Never use generic robotic intros like 'Certainly!', 'I understand your concern', or 'I hope this message finds you well'.\n"
        "3. Strictly NEVER use em-dashes (—), en-dashes (–), or hyphens for pauses. Use commas, colons, or clean sentences instead.\n"
        "4. Separate all paragraphs and greeting with clean blank lines so there is generous breathing room. Never output literal backslash-n or slash-n tokens.\n"
        "5. Keep the reply concise (2-3 paragraphs), direct, helpful, and polite.\n"
        "6. Reference actual Lavoo pages and concepts (/l/decision-engine, /l/thebuildroom, /l/earnings, /l/thesignal, Chops, Missions) accurately."
    )

    history_section = f"--- PREVIOUS CONVERSATION THREAD ---\n{conversation_history}\n\n" if conversation_history else ""

    user_prompt = (
        f"Here is the Lavoo Platform Master Knowledge:\n"
        f"{LAVOO_KNOWLEDGE_BASE}\n\n"
        f"--- USER TICKET DETAILS ---\n"
        f"Ticket ID: #{ticket_id}\n"
        f"User Name: {display_name}\n"
        f"User Email: {user_email}\n"
        f"Category: {category}\n\n"
        f"{history_section}"
        f"--- LATEST USER MESSAGE TO ANSWER ---\n"
        f"{issue_text}\n\n"
        f"Please write a warm, expert, human response directly answering {display_name}'s latest message using Lavoo platform specifics.\n"
        f"Start with 'Hi {display_name},' and end with a friendly sign-off like 'Let me know if you need anything else, and I will be glad to assist!'."
    )

    from openai import OpenAI

    def _call_nvidia():
        if not nvidia_key:
            return None
        model_name = os.getenv("CUSTOMER_SERVICE_NVIDIA_MODEL", os.getenv("VOO_NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct"))
        client = OpenAI(
            api_key=nvidia_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=30.0,
            max_retries=2,
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.35,
            max_tokens=450,
        )
        if completion and completion.choices:
            return completion.choices[0].message.content.strip()
        return None

    def _call_grok():
        if not xai_key:
            return None
        model_name = os.getenv("CUSTOMER_SERVICE_GROK_MODEL", os.getenv("VOO_GROK_MODEL", "grok-4-1-fast-reasoning"))
        client = OpenAI(
            api_key=xai_key,
            base_url="https://api.x.ai/v1",
            timeout=30.0,
            max_retries=2,
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.35,
            max_tokens=450,
        )
        if completion and completion.choices:
            return completion.choices[0].message.content.strip()
        return None

    order = [_call_nvidia, _call_grok] if preferred_provider == "nvidia" else [_call_grok, _call_nvidia]

    for call_fn in order:
        try:
            raw_text = call_fn()
            if raw_text:
                return _normalize_support_paragraphs(raw_text)
        except Exception as e:
            provider_name = "NVIDIA" if call_fn == _call_nvidia else "Grok"
            logger.warning(f"[AI Support] {provider_name} generation failed, attempting next provider: {e}")

    return _normalize_support_paragraphs(fallback_reply)


# ─── BACKGROUND WORKER ENTRYPOINT ─────────────────────────────────────────────
async def async_process_ticket_support_ai(ticket_id: int):
    """
    Background worker invoked whenever a new support ticket is submitted or user replies.
    1. Inspects the latest message in the thread.
    2. If latest is from user -> checks sensitivity; if standard, generates humanized reply.
    3. Posts reply as official admin message and updates ticket.
    """
    with SessionLocal() as db:
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"[AI Support] Ticket #{ticket_id} not found.")
                return

            # Fetch all messages in the thread ordered chronologically
            messages = db.query(TicketMessage).filter(
                TicketMessage.ticket_id == ticket_id
            ).order_by(TicketMessage.created_at.asc()).all()

            if not messages:
                logger.info(f"[AI Support] No messages found for ticket #{ticket_id}. Skipping.")
                return

            # Inspect latest message
            latest_msg = messages[-1]
            if latest_msg.sender_role in ["admin", "system"]:
                logger.info(f"[AI Support] Ticket #{ticket_id} latest message is already from {latest_msg.sender_role}. Skipping.")
                return

            user = db.query(User).filter(User.id == ticket.user_id).first()
            user_name = user.name if user and hasattr(user, 'name') and user.name else "there"
            user_email = user.email if user and hasattr(user, 'email') and user.email else ""

            category_val = ticket.category or "general"
            latest_user_text = (latest_msg.message or ticket.issue or "").strip()

            # Run Sensitivity Classifier on latest user message
            is_sensitive, reason = _classify_support_sensitivity(category_val, latest_user_text)

            if is_sensitive:
                logger.info(f"[AI Support] Ticket #{ticket_id} is sensitive ({reason}). Escalating to Human Admin.")
                # Leave ticket in 'open' status for human admin to review in lavoo_admin
                return

            # Format previous conversation history (up to last 6 messages)
            history_lines = []
            for msg in messages[:-1][-6:]:
                role_label = "User" if msg.sender_role == "user" else "Lavoo Support"
                history_lines.append(f"{role_label}: {msg.message}")
            conversation_history = "\n\n".join(history_lines) if history_lines else None

            # Generate humanized support reply
            ai_reply_text = _generate_humanized_support_reply(
                user_name=user_name,
                user_email=user_email,
                category=category_val,
                issue_text=latest_user_text,
                ticket_id=ticket.id,
                conversation_history=conversation_history
            )

            if not ai_reply_text:
                return

            # Find an admin user ID to associate or fallback
            admin_user = db.query(User).filter(User.is_admin == True).first()
            admin_id = admin_user.id if admin_user else (user.id if user else 1)
            admin_name = "Lavoo Admin"

            # Insert message as official support response (role: admin)
            support_msg = TicketMessage(
                ticket_id=ticket.id,
                sender_id=admin_id,
                sender_role="admin",
                message=ai_reply_text,
                is_read=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(support_msg)

            # Update ticket status to in_progress
            ticket.status = "in_progress"
            ticket.updated_at = datetime.now(timezone.utc)

            # Create UserNotification for user dashboard
            user_notif = UserNotification(
                user_id=ticket.user_id,
                type="support_reply",
                title="🎧 Lavoo Admin replied",
                message=f"Lavoo Admin replied to your ticket: '{(latest_user_text or ticket.issue or 'Support Request')[:45]}'",
                link=f"/l/customer-service?ticketId={ticket.id}",
                is_read=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(user_notif)

            db.commit()
            db.refresh(support_msg)
            logger.info(f"✅ [AI Support] Successfully posted support reply to ticket #{ticket.id}")

            # Notify via WebSockets if available
            try:
                import json
                from api.routes.support.customer_service import manager, notification_manager

                created_iso = support_msg.created_at.replace(tzinfo=timezone.utc).isoformat() if support_msg.created_at else datetime.now(timezone.utc).isoformat()
                ws_payload = json.dumps({
                    "type": "new_message",
                    "payload": {
                        "id": support_msg.id,
                        "ticket_id": ticket.id,
                        "sender_id": admin_id,
                        "sender_role": "admin",
                        "sender_name": admin_name,
                        "message": support_msg.message,
                        "content": support_msg.message,
                        "created_at": created_iso
                    },
                    "message": {
                        "id": support_msg.id,
                        "ticket_id": ticket.id,
                        "sender_id": admin_id,
                        "sender_role": "admin",
                        "sender_name": admin_name,
                        "message": support_msg.message,
                        "content": support_msg.message,
                        "created_at": created_iso
                    }
                })
                # Broadcast to admin and user notification channels
                await manager.broadcast(ws_payload)
                await notification_manager.send_personal_message(ws_payload, ticket.user_id)
            except Exception as ws_err:
                logger.debug(f"[AI Support] WebSocket push (non-critical): {ws_err}")

        except Exception as err:
            db.rollback()
            logger.error(f"❌ [AI Support] Failed to process ticket #{ticket_id}: {err}")
