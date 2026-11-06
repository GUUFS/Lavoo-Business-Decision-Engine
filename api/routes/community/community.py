"""
Community Feature — Channels, Discussions, Events, Leaderboard, Saved Items
"""
import logging
import re
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timezone, timedelta
import json
import os
import hashlib

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func, or_, String

from database.pg_connections import get_db, SessionLocal
from database.pg_models import (
    User,
    CommunityChannel, ChannelMember,
    CommunityDiscussion, DiscussionReply, DiscussionLike, DiscussionBookmark, DiscussionPollVote,
    CommunityEvent, EventRegistration,
    CommunityActivity, SavedItem,
    UserSettings, BusinessAnalysis,
    FounderInsightCard,
    VooAngleLog,
    VooFollowupLog,
    VooCallLog,
)
from api.routes.auth.login import get_current_user
from api.routes.dependencies import get_current_user_optional
from api.routes.user.missions import _flatten_roadmap_tasks
from api.cache import get_cached, set_cached, delete_cached
from api.services.notification_service import NotificationService

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community", tags=["community"])

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def _notify_community(db: Session, user_id: int, type: str, title: str, message: str, link: str):
    """Route Build Room notifications through preference checks and WebSocket delivery."""
    return NotificationService.create_notification(
        db=db, user_id=user_id, type=type, title=title, message=message, link=link
    )


def ensure_voo_bot_user(db: Session) -> User:
    """
    Ensures the system bot user "Voo's Angle" exists in the database.
    """
    bot = db.query(User).filter(func.lower(User.username) == "voo").first()
    if not bot:
        bot = db.query(User).filter(User.email == "voo@lavoo.io").first()
    if not bot:
        bot_pw = pwd_context.hash("voo_bot_secure_password_99x")
        bot = User(
            name="Voo's Angle",
            email="voo@lavoo.io",
            username="voo",
            is_bot=True,
            role="ai_bot",
            avatar_url="https://lavoo.io/logo.png",
            bio="Lavoo's intelligent AI assistant in The Build Room.",
            password=bot_pw,
            confirm_password=bot_pw
        )
        db.add(bot)
        db.commit()
        db.refresh(bot)
        logger.info(f"[voo-bot] Created Voo's Angle bot user account (id={bot.id})")
    else:
        changed = False
        if not getattr(bot, "is_bot", False):
            bot.is_bot = True
            changed = True
        if getattr(bot, "role", "") != "ai_bot":
            bot.role = "ai_bot"
            changed = True
        if bot.name != "Voo's Angle":
            bot.name = "Voo's Angle"
            changed = True
        if changed:
            db.commit()
    return bot


def _is_question_discussion(post_type: str = "", title: str = "", content: str = "") -> bool:
    """
    Intelligently identifies if a discussion is an inquiry, question, or advice request.
    Strictly avoids false-positive matches on ordinary reflections, statements, and updates.
    """
    p_type = (post_type or "").strip().lower()
    if p_type in ("questions", "question", "ask-the-community", "decision-help", "ask", "help", "inquiry", "advice", "poll", "polls"):
        return True

    t = (title or "").strip().lower()
    c = (content or "").strip().lower()

    # 1. Explicit question mark in title or content
    if "?" in t or "?" in c:
        return True

    # 2. Strict question phrase starters (checked only at the beginning of title or sentence/line starters)
    explicit_inquiry_phrases = (
        "how do i", "how can i", "how should", "how to", "how do you", "how would", "how did",
        "what is", "what are", "what would", "what should", "what do you", "what can i", "what's the best",
        "why is", "why does", "why did", "why do", "why would",
        "where can i", "where should", "where do i", "where to find",
        "when should", "when is the best",
        "which one", "which tool", "which platform",
        "who has experience", "who has used",
        "can anyone", "can somebody", "could someone", "could anyone",
        "does anyone", "has anyone", "have you ever", "is anyone here",
        "need help with", "need advice on", "need recommendations", "need input on",
        "help me with", "help me decide",
        "any recommendation", "any recommendations", "any advice on", "any thoughts on", "any suggestions for",
        "wondering if", "curious if anyone", "looking for advice", "seeking advice", "seeking recommendations",
        "what are your thoughts", "would love your feedback", "would love feedback"
    )

    # Check title prefix
    for phrase in explicit_inquiry_phrases:
        if t.startswith(phrase):
            return True

    # Check beginning of the first 3 lines of content
    lines = [line.strip() for line in c.split("\n") if line.strip()]
    for line in lines[:3]:
        for phrase in explicit_inquiry_phrases:
            if line.startswith(phrase):
                return True

    return False


def _normalize_paragraph_spacing(text: str) -> str:
    """
    Ensures that every paragraph, greeting, numbered point, and closing note
    is cleanly separated by standard newlines without rendering literal escaped tokens.
    """
    if not text:
        return ""
    # Strip literal \n or \\n characters outputted by LLMs, and cleanse em/en dashes
    cleaned = text.replace("\\n", "\n").replace("\\r", "").replace("/n", "\n")
    cleaned = cleaned.replace("—", ", ").replace("–", ", ")
    # Split on newlines, strip each chunk, filter out empty ones and raw slash-n tokens
    chunks = [c.strip() for c in cleaned.split("\n") if c.strip() and c.strip().lower() not in ("\\n", "/n", r"\n")]
    return "\n\n".join(chunks)


VOO_GLOSSARY_TEXT: Optional[str] = None
VOO_ANGLE_SYSTEM_PROMPT: Optional[str] = None
VOO_FOLLOWUP_SYSTEM_PROMPT: Optional[str] = None
VOO_ANGLE_SYSTEM_PROMPT_HASH: Optional[str] = None
VOO_FOLLOWUP_SYSTEM_PROMPT_HASH: Optional[str] = None

VOO_SUMMARY_SYSTEM_PROMPT: Optional[str] = None
VOO_SUMMARY_SYSTEM_PROMPT_HASH: Optional[str] = None

ANGLE_PROMPT_VERSION = "angle_v2.1"
SUMMARY_PROMPT_VERSION = "summary_v2.0"
FOLLOWUP_PROMPT_VERSION = "followup_v1.0"


def _load_voo_glossary() -> str:
    """
    Loads facts from voo_glossary.txt. Checks for [FILL IN] placeholders.
    Refuses to start in production if unfilled placeholders exist.
    """
    global VOO_GLOSSARY_TEXT
    if VOO_GLOSSARY_TEXT is not None:
        return VOO_GLOSSARY_TEXT

    glossary_path = os.path.join(os.path.dirname(__file__), "voo_glossary.txt")
    try:
        with open(glossary_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"[voo-bot] Failed to read voo_glossary.txt: {e}")
        text = ""

    if "[FILL IN]" in text:
        env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").lower()
        err_msg = "CRITICAL: voo_glossary.txt contains '[FILL IN]' placeholders. Fill all details before running in production."
        if env in ("production", "prod"):
            logger.critical(f"[voo-bot] {err_msg}")
            raise RuntimeError(err_msg)
        else:
            logger.warning(f"[voo-bot] {err_msg}")

    VOO_GLOSSARY_TEXT = text
    return VOO_GLOSSARY_TEXT


def get_voo_angle_system_prompt() -> str:
    """
    Returns the static, cacheable system prompt for Voo's Angle containing
    identity, platform glossary, thinking rules, and 18 few-shot examples.
    """
    global VOO_ANGLE_SYSTEM_PROMPT, VOO_ANGLE_SYSTEM_PROMPT_HASH
    if VOO_ANGLE_SYSTEM_PROMPT is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "voo_angle_system_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            glossary = _load_voo_glossary()
            VOO_ANGLE_SYSTEM_PROMPT = template.replace("{{GLOSSARY}}", glossary)
            VOO_ANGLE_SYSTEM_PROMPT_HASH = hashlib.sha256(VOO_ANGLE_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"[voo-bot] Failed to build voo_angle_system_prompt.txt: {e}")
            VOO_ANGLE_SYSTEM_PROMPT = ""
            VOO_ANGLE_SYSTEM_PROMPT_HASH = ""
    return VOO_ANGLE_SYSTEM_PROMPT


def get_voo_summary_system_prompt() -> str:
    """
    Returns the static, cacheable system prompt for Voo's Summary from voo_summary_system_prompt.txt.
    """
    global VOO_SUMMARY_SYSTEM_PROMPT, VOO_SUMMARY_SYSTEM_PROMPT_HASH
    if VOO_SUMMARY_SYSTEM_PROMPT is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "voo_summary_system_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                VOO_SUMMARY_SYSTEM_PROMPT = f.read()
            VOO_SUMMARY_SYSTEM_PROMPT_HASH = hashlib.sha256(VOO_SUMMARY_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"[voo-bot] Failed to load voo_summary_system_prompt.txt: {e}")
            VOO_SUMMARY_SYSTEM_PROMPT = ""
            VOO_SUMMARY_SYSTEM_PROMPT_HASH = ""
    return VOO_SUMMARY_SYSTEM_PROMPT


def get_voo_followup_system_prompt() -> str:
    """
    Returns the static, cacheable system prompt for Voo's follow-ups containing
    identity, platform glossary, thinking rules, and 8 few-shot examples.
    """
    global VOO_FOLLOWUP_SYSTEM_PROMPT, VOO_FOLLOWUP_SYSTEM_PROMPT_HASH
    if VOO_FOLLOWUP_SYSTEM_PROMPT is None:
        prompt_path = os.path.join(os.path.dirname(__file__), "voo_followup_system_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            glossary = _load_voo_glossary()
            VOO_FOLLOWUP_SYSTEM_PROMPT = template.replace("{{GLOSSARY}}", glossary)
            VOO_FOLLOWUP_SYSTEM_PROMPT_HASH = hashlib.sha256(VOO_FOLLOWUP_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"[voo-bot] Failed to build voo_followup_system_prompt.txt: {e}")
            VOO_FOLLOWUP_SYSTEM_PROMPT = ""
            VOO_FOLLOWUP_SYSTEM_PROMPT_HASH = ""
    return VOO_FOLLOWUP_SYSTEM_PROMPT


def _get_voo_memory(db: Session) -> Tuple[str, str, str, List[str]]:
    """
    Retrieves the 10 most recent openings, tests, and lenses across the entire Build Room
    from voo_angle_log so Voo does not repeat opening patterns or lean repeatedly on the same lens.
    """
    try:
        logs = db.query(VooAngleLog).order_by(VooAngleLog.created_at.desc()).limit(10).all()
        if not logs:
            return "None", "None", "None", []
        openings = [f'"{log.opening.strip()}"' for log in logs if log.opening]
        tests = [f'"{log.test.strip()}"' for log in logs if log.test]
        types = [log.angle_type.strip() for log in logs if log.angle_type]
        raw_openings = [log.opening.strip() for log in logs if log.opening]

        openings_str = "\n".join(openings) if openings else "None"
        tests_str = "\n".join(tests) if tests else "None"
        types_str = ", ".join(types) if types else "None"
        return openings_str, tests_str, types_str, raw_openings
    except Exception as e:
        logger.error(f"[voo-bot] Error retrieving Voo memory: {e}")
        return "None", "None", "None", []


BANNED_OPENINGS = (
    "be honest with yourself",
    "the real question is",
    "here's the uncomfortable truth",
    "here is the uncomfortable truth",
    "let's talk about",
    "let us talk about",
    "great question",
    "great point",
    "interesting",
    "so,",
    "so ",
)

BANNED_PHRASES = (
    "it's important to",
    "it is important to",
    "at the end of the day",
    "game changer",
    "unlock",
    "dive into",
    "navigate",
    "in today's world",
    "this highlights",
    "a testament to",
    "great question",
    "great point",
)

LAVOO_PROTECTED_TERMS = (
    "lavoo",
    "voo",
    "check-up",
    "checkup",
    "mission",
    "missions",
    "chops",
    "build room",
    "decision engine",
    "reflection",
)


def _clean_dashes(text: str) -> str:
    """
    Replaces em dashes and en dashes with a comma and a space, then tidies double spaces.
    Leaves normal hyphens alone so words like 'Check-up' survive.
    """
    if not text:
        return ""
    text = text.replace("—", ", ").replace("–", ", ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r",\s*,", ", ", text)
    return text.strip()


def _clean_text_extras(text: str, replier_handle: Optional[str] = None) -> str:
    """
    Cleans text, removes em/en dashes, trims quotes and backticks,
    and strips any leading greeting if the model generated one.
    """
    text = _clean_dashes(text)
    text = text.strip('`"\' \n\r\t')
    if replier_handle:
        h = replier_handle.lstrip("@")
        greeting_pattern = rf"^(?:hey|hello|hi)\s+(?:@{re.escape(h)}|{re.escape(h)}|there|founder|builder)[.,!:]*\s*"
        text = re.sub(greeting_pattern, "", text, flags=re.IGNORECASE).strip()
    generic_greeting = r"^(?:hey|hello|hi)\s+(?:there|founder|builder)[.,!:]*\s*"
    text = re.sub(generic_greeting, "", text, flags=re.IGNORECASE).strip()
    return text


def _parse_json_response(raw_text: str) -> Optional[dict]:
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return None


def _extract_opening(angle: str) -> str:
    sentences = re.split(r'[.!?]\s+', angle.strip())
    first_sentence = sentences[0].strip() if sentences else angle.strip()
    words = first_sentence.split()
    return " ".join(words[:12])


def _validate_angle_data(
    data: dict,
    recent_raw_openings: List[str],
    thread_replies_str: str,
    post_type: str,
    post_title: str,
    post_content: str
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validates LLM angle output according to Section 4 of Code Spec:
    1. Parse JSON with required 7 fields: respond, question_type, reasoning, obvious_answer, angle_type, angle, test
    2. Check respond boolean
    3. question_type must be 'direct' or 'decision'
    4. Length: angle (40-140 words), test (<30 words)
    5. Repetition check: compare first 4 words of angle with stored openings
    6. Banned phrases / openings / leverage / contrast patterns
    7. Lavoo guard: if ordinary question without Lavoo terms, angle & test must not contain them
    8. Handle guard: any @handle must appear in thread_replies
    9. Stray letter guard: flag standalone capital other than 'I' and 'A'
    10. Placeholder guard: reject [FILL IN], {, }
    11. Clean dashes while preserving hyphens
    12. Strip stray greetings, quotes, markdown
    """
    required_fields = ["respond", "reasoning", "obvious_answer", "angle_type", "angle", "test"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'", None

    if not data.get("respond"):
        return True, None, data

    # question_type is optional in newer developer pack prompts (defaults to 'decision')
    q_type = str(data.get("question_type", "decision") or "decision").strip().lower()
    if q_type not in ("direct", "decision"):
        q_type = "decision"

    raw_angle = str(data.get("angle", ""))
    raw_test = str(data.get("test", ""))

    for placeholder_marker in ("[fill in]", "{", "}"):
        if placeholder_marker in raw_angle.lower() or placeholder_marker in raw_test.lower():
            return False, f"Output contains placeholder marker: '{placeholder_marker}'", None

    angle = _clean_text_extras(raw_angle)
    test = _clean_dashes(raw_test).strip('`"\' \n\r\t')
    test = re.sub(r"^(?:the\s+)?voo\s+test[:\s-]*", "", test, flags=re.IGNORECASE).strip()

    angle_words = angle.split()
    test_words = test.split()

    if len(angle_words) < 40 or len(angle_words) > 140:
        return False, f"Angle word count out of bounds: {len(angle_words)} words (expected 40-140)", None
    if len(test_words) >= 30:
        return False, f"Test word count too long: {len(test_words)} words (expected <30)", None

    angle_first_4 = " ".join([re.sub(r"\W+", "", w).lower() for w in angle_words[:4] if re.sub(r"\W+", "", w)])
    for past_op in recent_raw_openings:
        past_words = past_op.strip().lower().split()
        past_first_4 = " ".join([re.sub(r"\W+", "", w).lower() for w in past_words[:4] if re.sub(r"\W+", "", w)])
        if angle_first_4 and angle_first_4 == past_first_4:
            return False, f"Angle opening repeats recent pattern: '{angle_first_4}'", None

    angle_lower = angle.lower()
    test_lower = test.lower()
    for banned in BANNED_OPENINGS:
        if angle_lower.startswith(banned):
            return False, f"Angle starts with banned opening: '{banned}'", None

    for phrase in BANNED_PHRASES:
        if phrase in angle_lower or phrase in test_lower:
            return False, f"Angle/test contains banned phrase: '{phrase}'", None

    if re.search(r"\bleverag(?:e|es|ed|ing)\b", angle_lower) or re.search(r"\bleverag(?:e|es|ed|ing)\b", test_lower):
        return False, "Angle uses banned word 'leverage'", None

    if re.search(r"\b(?:this|it)\s+(?:isn't|is\s+not)\b.*,\s*(?:it's|it\s+is)\b", angle_lower) or \
       re.search(r"\b(?:it's|it\s+is)\s+not\s+about\b.*,\s*(?:it's|it\s+is)\s+about\b", angle_lower):
        return False, "Angle uses banned contrast pattern ('This is not X, it is Y')", None

    is_platform_poll = (post_type or "").strip().lower() in ("platform poll", "poll")
    if not is_platform_poll:
        post_text = f"{post_title} {post_content}".lower()
        post_has_lavoo = any(re.search(rf"\b{re.escape(term)}\b", post_text) for term in LAVOO_PROTECTED_TERMS)
        if not post_has_lavoo:
            for term in LAVOO_PROTECTED_TERMS:
                if re.search(rf"\b{re.escape(term)}\b", angle_lower) or re.search(rf"\b{re.escape(term)}\b", test_lower):
                    return False, f"Lavoo guard triggered: ordinary question without '{term}' had '{term}' in reply", None

    output_handles = re.findall(r"@([a-zA-Z0-9_]+)", f"{angle} {test}")
    if output_handles:
        allowed_handles = [h.lower() for h in re.findall(r"@([a-zA-Z0-9_]+)", thread_replies_str or "")]
        for h in output_handles:
            if h.lower() not in allowed_handles:
                return False, f"Handle guard triggered: '@{h}' was not mentioned in thread replies", None

    for text_to_check in (angle, test):
        stray = re.search(r"(?:^|\s)([B-HJ-Z])(?:[.,!?:;]|\s|$)", text_to_check)
        if stray:
            return False, f"Stray letter guard triggered: found standalone letter '{stray.group(1)}'", None

    cleaned_data = dict(data)
    cleaned_data["angle"] = angle
    cleaned_data["test"] = test
    cleaned_data["question_type"] = q_type
    return True, None, cleaned_data


def _validate_followup_data(
    data: dict,
    original_angle_text: str,
    conversation_str: str,
    post_type: str,
    post_title: str,
    post_content: str
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validates LLM follow-up output according to Section 5 of Code Spec:
    1. Parse JSON with required 5 fields: respond, reply_type, reasoning, changes_original, reply
    2. If respond is false, valid
    3. reply_type must be in allowed list
    4. Length: reply (15-150 words)
    5. Banned phrases, leverage, contrast patterns
    6. Lavoo guard: allowed if in post or in conversation so far
    7. Handle guard: any @handle in reply must appear in conversation
    8. Sensitive data guard: no phone numbers, emails, or 8+ digit strings
    9. Repetition: first 6 words must not match original Angle
    10. Stray letter guard
    11. Placeholder guard
    12. Clean dashes and strip extras
    """
    required_fields = ["respond", "reply_type", "reasoning", "changes_original", "reply"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'", None

    if not data.get("respond"):
        return True, None, data

    allowed_types = (
        "clarifying", "new_details", "pushback", "how_to",
        "other_member", "cannot_access", "privacy", "thanks", "off_topic"
    )
    reply_type = str(data.get("reply_type", "")).strip().lower()
    if reply_type not in allowed_types:
        return False, f"Invalid reply_type: '{reply_type}'", None

    raw_reply = str(data.get("reply", ""))

    for placeholder_marker in ("[fill in]", "{", "}"):
        if placeholder_marker in raw_reply.lower():
            return False, f"Follow-up contains placeholder marker: '{placeholder_marker}'", None

    reply = _clean_text_extras(raw_reply)
    reply_words = reply.split()

    if len(reply_words) < 15 or len(reply_words) > 150:
        return False, f"Follow-up word count out of bounds: {len(reply_words)} words (expected 15-150)", None

    reply_lower = reply.lower()

    for banned in BANNED_OPENINGS:
        if reply_lower.startswith(banned):
            return False, f"Follow-up starts with banned opening: '{banned}'", None

    for phrase in BANNED_PHRASES:
        if phrase in reply_lower:
            return False, f"Follow-up contains banned phrase: '{phrase}'", None

    if re.search(r"\bleverag(?:e|es|ed|ing)\b", reply_lower):
        return False, "Follow-up uses banned word 'leverage'", None

    if re.search(r"\b(?:this|it)\s+(?:isn't|is\s+not)\b.*,\s*(?:it's|it\s+is)\b", reply_lower) or \
       re.search(r"\b(?:it's|it\s+is)\s+not\s+about\b.*,\s*(?:it's|it\s+is)\s+about\b", reply_lower):
        return False, "Follow-up uses banned contrast pattern ('This is not X, it is Y')", None

    is_platform_poll = (post_type or "").strip().lower() in ("platform poll", "poll")
    if not is_platform_poll:
        prior_context = f"{post_title} {post_content} {conversation_str}".lower()
        for term in LAVOO_PROTECTED_TERMS:
            if not re.search(rf"\b{re.escape(term)}\b", prior_context):
                if re.search(rf"\b{re.escape(term)}\b", reply_lower):
                    return False, f"Lavoo guard triggered: term '{term}' not in conversation context but appeared in follow-up", None

    output_handles = re.findall(r"@([a-zA-Z0-9_]+)", reply)
    if output_handles:
        allowed_handles = [h.lower() for h in re.findall(r"@([a-zA-Z0-9_]+)", f"{post_title} {post_content} {conversation_str}")]
        for h in output_handles:
            if h.lower() not in allowed_handles:
                return False, f"Handle guard triggered: '@{h}' was not in conversation history", None

    if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", reply):
        return False, "Sensitive data guard triggered: email address detected in reply", None
    if re.search(r"\b\d{8,}\b", reply):
        return False, "Sensitive data guard triggered: long digit sequence detected in reply", None
    if re.search(r"\b0[789][01]\d{8}\b|\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", reply):
        return False, "Sensitive data guard triggered: phone number pattern detected in reply", None

    if original_angle_text:
        angle_first_6 = " ".join([re.sub(r"\W+", "", w).lower() for w in original_angle_text.split()[:6] if re.sub(r"\W+", "", w)])
        reply_first_6 = " ".join([re.sub(r"\W+", "", w).lower() for w in reply_words[:6] if re.sub(r"\W+", "", w)])
        if angle_first_6 and angle_first_6 == reply_first_6:
            return False, f"Follow-up repeats original angle opening: '{reply_first_6}'", None

    stray = re.search(r"(?:^|\s)([B-HJ-Z])(?:[.,!?:;]|\s|$)", reply)
    if stray:
        return False, f"Stray letter guard triggered: found standalone letter '{stray.group(1)}'", None

    cleaned_data = dict(data)
    cleaned_data["reply"] = reply
    return True, None, cleaned_data


def _call_voo_llm(
    system_prompt: str,
    user_prompt: str,
    mode: str = "angle",
    temperature: float = 0.6,
    max_tokens: int = 1000
) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls NVIDIA NIM or xAI Grok with configured parameters and timeout.
    """
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    xai_key = os.getenv("XAI_API_KEY")
    preferred_provider = os.getenv("VOO_LLM_PROVIDER", "").strip().lower()

    from openai import OpenAI

    def _call_grok():
        if not xai_key:
            return None
        model_name = os.getenv("VOO_GROK_MODEL", "grok-4-1-fast-reasoning")
        client = OpenAI(
            api_key=xai_key,
            base_url="https://api.x.ai/v1",
            timeout=45.0,
            max_retries=2,
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if completion and completion.choices:
            return completion.choices[0].message.content.strip(), model_name
        return None, None

    def _call_nvidia():
        if not nvidia_key:
            return None
        model_name = os.getenv("VOO_NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
        client = OpenAI(
            api_key=nvidia_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=45.0,
            max_retries=2,
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if completion and completion.choices:
            return completion.choices[0].message.content.strip(), model_name
        return None, None

    order = [_call_nvidia, _call_grok] if preferred_provider == "nvidia" else [_call_grok, _call_nvidia]

    for call_fn in order:
        try:
            content, model_name = call_fn()
            if content:
                return content, model_name
        except Exception as e:
            provider_name = "NVIDIA" if call_fn == _call_nvidia else "Grok"
            logger.warning(f"[voo-bot] {provider_name} {mode} call failed: {e}")

    return None, None


def _log_voo_call(
    db: Session,
    post_id: Optional[int],
    mode: str,
    prompt_version: str,
    assembled_user_prompt: str,
    system_prompt_hash: str,
    raw_response: str,
    validation_result: str,
    retry_count: int
):
    try:
        call_log = VooCallLog(
            post_id=post_id,
            mode=mode,
            prompt_version=prompt_version,
            assembled_user_prompt=assembled_user_prompt,
            system_prompt_hash=system_prompt_hash,
            raw_response=raw_response,
            validation_result=validation_result,
            retry_count=retry_count
        )
        db.add(call_log)
        db.commit()
    except Exception as e:
        logger.warning(f"[voo-bot] Failed to record VooCallLog: {e}")
        db.rollback()


def _generate_voo_angle_reply(
    db: Session,
    post_id: int,
    post_type: str,
    question_title: str,
    question_content: str,
    member_details: str,
    thread_replies: str,
    community_context: str,
    recent_openings: str,
    recent_tests: str,
    recent_angle_types: str,
    recent_raw_openings: List[str],
    author_handle: str = "@builder",
    author_role: str = "member",
    post_topic: str = "General"
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Executes Voo's Angle pipeline (v2.0) with prompt caching, glossary injection,
    memory avoidance, structured JSON validation, and single retry.
    """
    system_prompt = get_voo_angle_system_prompt()
    if not system_prompt:
        logger.error("[voo-bot] Angle system prompt is empty — cannot generate Voo Angle")
        return None, None

    prompt_path = os.path.join(os.path.dirname(__file__), "voo_angle_user_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            user_template = f.read()
    except Exception as e:
        logger.error(f"[voo-bot] Failed to read voo_angle_user_prompt.txt: {e}")
        return None, None

    user_prompt = user_template.format(
        author_handle=author_handle or "@builder",
        author_role=author_role or "member",
        author_context=member_details or "None",
        post_type=post_type or "Question",
        post_topic=post_topic or "General",
        post_title=question_title or "",
        post_content=question_content or "",
        thread_replies=thread_replies or "None",
        community_context=community_context or "None",
        recent_openings=recent_openings or "None",
        recent_tests=recent_tests or "None",
        recent_angle_types=recent_angle_types or "None",
    )

    for attempt in range(1, 3):
        raw_content, model_name = _call_voo_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="angle",
            temperature=0.6,
            max_tokens=1000
        )
        if not raw_content:
            logger.warning(f"[voo-bot] Angle LLM returned empty response on attempt {attempt}")
            _log_voo_call(
                db=db,
                post_id=post_id,
                mode="angle",
                prompt_version=ANGLE_PROMPT_VERSION,
                assembled_user_prompt=user_prompt,
                system_prompt_hash=VOO_ANGLE_SYSTEM_PROMPT_HASH or "",
                raw_response="",
                validation_result="empty_llm_response",
                retry_count=attempt - 1
            )
            continue

        parsed = _parse_json_response(raw_content)
        if not parsed:
            logger.warning(f"[voo-bot] Failed to parse JSON on attempt {attempt}: {raw_content[:200]}")
            _log_voo_call(
                db=db,
                post_id=post_id,
                mode="angle",
                prompt_version=ANGLE_PROMPT_VERSION,
                assembled_user_prompt=user_prompt,
                system_prompt_hash=VOO_ANGLE_SYSTEM_PROMPT_HASH or "",
                raw_response=raw_content,
                validation_result="json_parse_error",
                retry_count=attempt - 1
            )
            continue

        is_valid, error_reason, cleaned_data = _validate_angle_data(
            data=parsed,
            recent_raw_openings=recent_raw_openings,
            thread_replies_str=thread_replies,
            post_type=post_type,
            post_title=question_title,
            post_content=question_content
        )

        _log_voo_call(
            db=db,
            post_id=post_id,
            mode="angle",
            prompt_version=ANGLE_PROMPT_VERSION,
            assembled_user_prompt=user_prompt,
            system_prompt_hash=VOO_ANGLE_SYSTEM_PROMPT_HASH or "",
            raw_response=raw_content,
            validation_result="passed" if is_valid else (error_reason or "validation_failed"),
            retry_count=attempt - 1
        )

        if is_valid:
            return cleaned_data, model_name
        else:
            logger.warning(f"[voo-bot] Angle validation failed on attempt {attempt}: {error_reason}")

    return None, None


def _generate_voo_followup_reply(
    db: Session,
    post_id: int,
    post_type: str,
    question_title: str,
    question_content: str,
    voo_angle: str,
    voo_test: str,
    conversation: str,
    latest_reply_from: str,
    latest_reply_text: str
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Executes Voo's Follow-up pipeline (v1.0) with prompt caching, glossary injection,
    sensitive data guards, structured JSON validation, and single retry.
    """
    system_prompt = get_voo_followup_system_prompt()
    if not system_prompt:
        logger.error("[voo-bot] Follow-up system prompt is empty — cannot generate follow-up")
        return None, None

    prompt_path = os.path.join(os.path.dirname(__file__), "voo_followup_user_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            user_template = f.read()
    except Exception as e:
        logger.error(f"[voo-bot] Failed to read voo_followup_user_prompt.txt: {e}")
        return None, None

    user_prompt = user_template.format(
        post_type=post_type or "Question",
        question_title=question_title or "",
        question_content=question_content or "",
        voo_angle=voo_angle or "",
        voo_test=voo_test or "",
        conversation=conversation or "None",
        latest_reply_from=latest_reply_from or "Asker",
        latest_reply_text=latest_reply_text or "",
    )

    for attempt in range(1, 3):
        raw_content, model_name = _call_voo_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="followup",
            temperature=0.5,
            max_tokens=700
        )
        if not raw_content:
            logger.warning(f"[voo-bot] Followup LLM returned empty response on attempt {attempt}")
            _log_voo_call(
                db=db,
                post_id=post_id,
                mode="followup",
                prompt_version=FOLLOWUP_PROMPT_VERSION,
                assembled_user_prompt=user_prompt,
                system_prompt_hash=VOO_FOLLOWUP_SYSTEM_PROMPT_HASH or "",
                raw_response="",
                validation_result="empty_llm_response",
                retry_count=attempt - 1
            )
            continue

        parsed = _parse_json_response(raw_content)
        if not parsed:
            logger.warning(f"[voo-bot] Failed to parse JSON on attempt {attempt}: {raw_content[:200]}")
            _log_voo_call(
                db=db,
                post_id=post_id,
                mode="followup",
                prompt_version=FOLLOWUP_PROMPT_VERSION,
                assembled_user_prompt=user_prompt,
                system_prompt_hash=VOO_FOLLOWUP_SYSTEM_PROMPT_HASH or "",
                raw_response=raw_content,
                validation_result="json_parse_error",
                retry_count=attempt - 1
            )
            continue

        is_valid, error_reason, cleaned_data = _validate_followup_data(
            data=parsed,
            original_angle_text=voo_angle,
            conversation_str=conversation,
            post_type=post_type,
            post_title=question_title,
            post_content=question_content
        )

        _log_voo_call(
            db=db,
            post_id=post_id,
            mode="followup",
            prompt_version=FOLLOWUP_PROMPT_VERSION,
            assembled_user_prompt=user_prompt,
            system_prompt_hash=VOO_FOLLOWUP_SYSTEM_PROMPT_HASH or "",
            raw_response=raw_content,
            validation_result="passed" if is_valid else (error_reason or "validation_failed"),
            retry_count=attempt - 1
        )

        if is_valid:
            return cleaned_data, model_name
        else:
            logger.warning(f"[voo-bot] Followup validation failed on attempt {attempt}: {error_reason}")

    return None, None


def _generate_voo_answer_message(author_handle: str, question_title: str, question_content: str, contributors: List[str], replies_text: str) -> str:
    """
    Backwards-compatible wrapper. Generates Voo's Angle for the given question.
    """
    clean_h = author_handle.strip().lstrip("@")
    return f"Hey @{clean_h}.\n\nWhat is the single constraint you are avoiding that settles this decision?\n\nTHE VOO TEST\nIf you could only build one thing this month, what survives?"


async def cron_process_pending_voo_replies(db: Session):
    """
    Checks for discussions where voo_status == 'scheduled' AND voo_scheduled_for <= now.
    Generates intelligent Voo's Angle with deep reasoning, memory avoidance, and validation,
    posting the response as Voo and logging to voo_angle_log.
    """
    now = datetime.now(timezone.utc)
    eligible = db.query(CommunityDiscussion).filter(
        CommunityDiscussion.voo_status == "scheduled",
        CommunityDiscussion.voo_scheduled_for <= now,
        or_(CommunityDiscussion.is_resolved == False, CommunityDiscussion.is_resolved == None)
    ).all()

    if not eligible:
        return

    logger.info(f"[voo-bot] Found {len(eligible)} discussions eligible for Voo answer")
    voo_user = ensure_voo_bot_user(db)

    for d in eligible:
        try:
            # Check if discussion already has a Voo reply
            existing_voo_reply = db.query(DiscussionReply).filter_by(
                discussion_id=d.id,
                user_id=voo_user.id
            ).first()

            if existing_voo_reply:
                d.voo_status = "completed"
                d.voo_reply_id = existing_voo_reply.id
                db.commit()
                continue

            # Skip posts under 8 words of content where the title is not a question
            content_words = (d.content or "").strip().split()
            title_is_q = "?" in (d.title or "")
            if len(content_words) < 8 and not title_is_q:
                d.voo_status = "skipped"
                db.commit()
                logger.info(f"[voo-bot] Skipping discussion {d.id}: under 8 words and title is not a question.")
                continue

            # Author lookup and Pro / Paid Account verification
            author_user = db.query(User).filter_by(id=d.user_id).first()
            if not author_user:
                d.voo_status = "skipped"
                db.commit()
                continue

            author_sub = (getattr(author_user, 'subscription_status', '') or '').strip().lower()
            author_is_paid = bool(author_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(author_user, 'is_admin', False))
            if not author_is_paid:
                d.voo_status = "skipped"
                d.voo_scheduled_for = None
                db.commit()
                logger.info(f"[voo-bot] Skipping Voo answer for discussion {d.id}: author {author_user.id} is a beta/free account.")
                continue

            # Section 3: Member details (Prioritize author's real Build Room journey and posts)
            bits = []
            is_staff = bool(getattr(author_user, "is_admin", False))
            if not is_staff:
                if getattr(author_user, "company_name", None):
                    bits.append(f"Business: {author_user.company_name}")
                if getattr(author_user, "industry", None):
                    bits.append(f"Industry: {author_user.industry}")
                if getattr(author_user, "venture_stage", None):
                    bits.append(f"Stage: {author_user.venture_stage}")
                if getattr(author_user, "location", None):
                    bits.append(f"Country/Location: {author_user.location}")

            # Fetch author's recent public posts/reflections in the Build Room (up to 3, excluding current post)
            recent_author_discussions = (
                db.query(CommunityDiscussion)
                .filter(
                    CommunityDiscussion.user_id == d.user_id,
                    CommunityDiscussion.id != d.id,
                    CommunityDiscussion.visibility == "public"
                )
                .order_by(CommunityDiscussion.id.desc())
                .limit(4)
                .all()
            )
            seen_recent_titles = set()
            recent_history_snippets = []
            for past_d in recent_author_discussions:
                t = (past_d.title or "").strip()
                if t and t.lower() not in seen_recent_titles:
                    seen_recent_titles.add(t.lower())
                    c_snip = " ".join((past_d.content or "").strip().split()[:15])
                    if c_snip:
                        recent_history_snippets.append(f'"{t}" ({c_snip}...)')
                    else:
                        recent_history_snippets.append(f'"{t}"')

            if recent_history_snippets:
                bits.append(f"Recent Build Room activity: {'; '.join(recent_history_snippets[:3])}")

            member_details = " | ".join(bits) if bits else "None"

            # Post type: Only staff accounts can create Platform Polls
            post_type_label = "Platform Poll" if (d.post_type == "poll" or d.poll_data) else "Question"

            # Trim question content to ~1,500 words
            trimmed_content = " ".join(content_words[:1500])

            # Fetch human thread replies (up to 10, oldest first, trimmed to ~80 words)
            # Resolve handles fresh by user ID at call time
            replies = db.query(DiscussionReply).filter(
                DiscussionReply.discussion_id == d.id,
                DiscussionReply.user_id != voo_user.id
            ).order_by(DiscussionReply.created_at.asc()).limit(10).all()

            reply_lines = []
            for r in replies:
                u = db.query(User).filter_by(id=r.user_id).first()
                u_handle = (u.username if u and u.username else (u.name if u and u.name else "builder")).strip().lstrip("@")
                r_words = (r.content or "").split()
                r_trimmed = " ".join(r_words[:80])
                reply_lines.append(f"@{u_handle}: {r_trimmed}")
            thread_replies_str = "\n".join(reply_lines) if reply_lines else "None"

            # Optional community context: up to 3 similar resolved questions
            similar_resolved = db.query(CommunityDiscussion).filter(
                CommunityDiscussion.id != d.id,
                CommunityDiscussion.is_resolved == True
            ).order_by(CommunityDiscussion.created_at.desc()).limit(3).all()
            if similar_resolved:
                community_context_str = "Recent resolved discussions:\n" + "\n".join([f"- {s.title}" for s in similar_resolved])
            else:
                community_context_str = "None"

            # Memory from voo_angle_log
            recent_openings, recent_tests, recent_angle_types, recent_raw_openings = _get_voo_memory(db)

            # Extract author handle, role and post topic
            author_handle = (f"@{author_user.username}" if getattr(author_user, "username", None) else (f"@{author_user.name}" if getattr(author_user, "name", None) else "@builder")).strip()
            is_staff = bool(getattr(author_user, "is_admin", False))
            author_role = "lavoo_team" if is_staff else "member"
            post_topic = "General"
            if d.channel_id:
                ch = db.query(CommunityChannel).filter_by(id=d.channel_id).first()
                if ch and ch.name:
                    post_topic = ch.name

            # Generate Voo Angle
            angle_data, used_model = _generate_voo_angle_reply(
                db=db,
                post_id=d.id,
                post_type=post_type_label,
                question_title=d.title,
                question_content=trimmed_content,
                member_details=member_details,
                thread_replies=thread_replies_str,
                community_context=community_context_str,
                recent_openings=recent_openings,
                recent_tests=recent_tests,
                recent_angle_types=recent_angle_types,
                recent_raw_openings=recent_raw_openings,
                author_handle=author_handle,
                author_role=author_role,
                post_topic=post_topic
            )

            if not angle_data:
                logger.warning(f"[voo-bot] Voo angle generation failed or timed out for discussion {d.id}")
                d.voo_status = "skipped"
                db.commit()
                continue

            if not angle_data.get("respond"):
                logger.info(f"[voo-bot] Voo angle skipped for discussion {d.id}. Reasoning: {angle_data.get('reasoning')}")
                d.voo_status = "skipped"
                db.commit()
                continue

            angle_body = angle_data.get("angle", "").strip()
            test_line = angle_data.get("test", "").strip()

            # Section 3 & 4: Resolve author handle fresh by user ID at posting time
            fresh_author = db.query(User).filter_by(id=d.user_id).first()
            author_handle = (fresh_author.username if fresh_author and fresh_author.username else (fresh_author.name if fresh_author and fresh_author.name else "builder")).strip().lstrip("@")

            full_reply_text = f"Hey @{author_handle}.\n\n{angle_body}\n\nTHE VOO TEST\n{test_line}"

            voo_reply = DiscussionReply(
                discussion_id=d.id,
                user_id=voo_user.id,
                content=full_reply_text,
                parent_reply_id=None,
                tagged_user_ids=[d.user_id] if d.user_id else []
            )
            db.add(voo_reply)
            db.flush()

            # Record in voo_angle_log
            opening_snippet = _extract_opening(angle_body)
            log_entry = VooAngleLog(
                post_id=d.id,
                prompt_version=ANGLE_PROMPT_VERSION,
                question_type=angle_data.get("question_type", "decision"),
                opening=opening_snippet,
                test=test_line,
                angle=angle_body,
                angle_type=angle_data.get("angle_type", "reframe"),
                reasoning=angle_data.get("reasoning", ""),
                obvious_answer=angle_data.get("obvious_answer", ""),
                model=used_model
            )
            db.add(log_entry)

            d.reply_count = (d.reply_count or 0) + 1
            d.voo_status = "completed"
            d.voo_reply_id = voo_reply.id
            db.commit()
            db.refresh(voo_reply)

            # Notify author
            if d.user_id:
                try:
                    _notify_community(
                        db, d.user_id, "voo_checkin", "🤖 Voo answered your question",
                        f"Voo shared an angle on your question: '{d.title[:50]}'",
                        f"/dashboard/community?discussionId={d.id}",
                    )
                except Exception as ne:
                    logger.warning(f"[voo-bot] Notification creation failed: {ne}")

            await delete_cached("community:discussions:*")
            logger.info(f"[voo-bot] Successfully posted Voo Angle on discussion {d.id} and recorded to voo_angle_log")

        except Exception as e:
            logger.error(f"[voo-bot] Failed processing discussion {d.id}: {e}", exc_info=True)
            db.rollback()


async def _process_voo_followup_task(discussion_id: int, trigger_reply_id: int, replier_user_id: int):
    """
    Background worker for Voo Follow-up mode.
    Debounces rapid replies from the same member, verifies caps,
    gathers the conversation history involving Voo, and generates/posts Voo's follow-up.
    """
    import asyncio
    # Wait 5 seconds for debounce
    await asyncio.sleep(5)

    db: Session = SessionLocal()
    try:
        voo_user = ensure_voo_bot_user(db)
        if replier_user_id == voo_user.id:
            return

        d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
        if not d:
            return

        # Fetch Voo's Angle log for this discussion
        angle_log = db.query(VooAngleLog).filter_by(post_id=discussion_id).order_by(VooAngleLog.created_at.desc()).first()
        if not angle_log:
            logger.info(f"[voo-followup] No Voo Angle found for discussion {discussion_id}; skipping follow-up.")
            return

        replier_user = db.query(User).filter_by(id=replier_user_id).first()
        if not replier_user:
            return

        # Sync user subscription to ensure latest status
        try:
            from api.utils.sub_utils import sync_user_subscription
            sync_user_subscription(db, replier_user)
        except Exception as se:
            logger.warning(f"[voo-followup] Failed to sync subscription for user {replier_user_id}: {se}")

        sub_status = (getattr(replier_user, "subscription_status", "") or "").strip().lower()
        sub_plan = (getattr(replier_user, "subscription_plan", "") or "").strip().lower()
        is_admin = bool(getattr(replier_user, "is_admin", False))
        is_staff = bool(getattr(replier_user, "is_staff", False))

        is_paid = (
            is_admin or
            is_staff or
            sub_status in ("active", "trialing", "pro", "premium", "lifetime", "paid") or
            (sub_plan and sub_plan not in ("free", "none", ""))
        )

        if not is_paid:
            logger.info(f"[voo-followup] Skipping follow-up for user {replier_user_id}: not an active paid or admin account (status='{sub_status}', plan='{sub_plan}')")
            return

        # Caps check: hard cap of 3 follow-up responses per user per thread; 15 total for thread
        user_thread_count = db.query(VooFollowupLog).filter(
            VooFollowupLog.post_id == discussion_id,
            VooFollowupLog.replier_user_id == replier_user_id
        ).count()

        total_thread_count = db.query(VooFollowupLog).filter(
            VooFollowupLog.post_id == discussion_id
        ).count()

        replier_handle = (replier_user.username if replier_user and replier_user.username else (replier_user.name if replier_user and replier_user.name else "builder")).strip().lstrip("@")

        if user_thread_count >= 3 or total_thread_count >= 15:
            logger.info(f"[voo-followup] Cap reached for discussion {discussion_id} (user_thread_count={user_thread_count}, total_thread_count={total_thread_count})")
            if user_thread_count == 3:
                cap_msg = f"@{replier_handle} I have shared what I can in this thread for today. Take that test into the real world this week and share what happens in your next reflection!"
                cap_reply = DiscussionReply(
                    discussion_id=discussion_id,
                    user_id=voo_user.id,
                    content=cap_msg,
                    parent_reply_id=trigger_reply_id,
                    tagged_user_ids=[replier_user_id]
                )
                db.add(cap_reply)
                db.flush()

                cap_log = VooFollowupLog(
                    post_id=discussion_id,
                    parent_message_id=trigger_reply_id,
                    replier_user_id=replier_user_id,
                    prompt_version=FOLLOWUP_PROMPT_VERSION,
                    reply_type="cap_reached",
                    changes_original=False,
                    reply=cap_msg,
                    reasoning="Thread per-user cap reached (3 replies)",
                    model="static"
                )
                db.add(cap_log)
                d.reply_count = (d.reply_count or 0) + 1
                db.commit()
                await delete_cached(f"community:public_post:{discussion_id}")
                await delete_cached("community:discussions:*")
            return

        trigger_reply = db.query(DiscussionReply).filter_by(id=trigger_reply_id).first()
        if not trigger_reply:
            return

        # Debounce join for rapid replies: find replies by this user created after the last Voo reply
        last_voo_reply = db.query(DiscussionReply).filter(
            DiscussionReply.discussion_id == discussion_id,
            DiscussionReply.user_id == voo_user.id
        ).order_by(DiscussionReply.created_at.desc()).first()

        debounce_cutoff = last_voo_reply.created_at if last_voo_reply else (trigger_reply.created_at - timedelta(seconds=60))

        recent_user_replies = db.query(DiscussionReply).filter(
            DiscussionReply.discussion_id == discussion_id,
            DiscussionReply.user_id == replier_user_id,
            DiscussionReply.created_at >= debounce_cutoff,
            DiscussionReply.created_at <= trigger_reply.created_at
        ).order_by(DiscussionReply.created_at.asc()).all()

        if recent_user_replies:
            latest_reply_text = "\n\n".join([r.content.strip() for r in recent_user_replies if r.content])
        else:
            latest_reply_text = trigger_reply.content.strip()

        latest_reply_words = latest_reply_text.split()
        latest_reply_trimmed = " ".join(latest_reply_words[:300])

        latest_reply_from = "Asker" if replier_user_id == d.user_id else f"@{replier_handle}"

        # Conversation chain involving Voo (last 12 messages before trigger, oldest first)
        past_replies = db.query(DiscussionReply).filter(
            DiscussionReply.discussion_id == discussion_id,
            DiscussionReply.id != trigger_reply_id,
            DiscussionReply.created_at <= trigger_reply.created_at
        ).order_by(DiscussionReply.created_at.desc()).limit(12).all()
        past_replies.reverse()

        conv_lines = []
        for pr in past_replies:
            pr_words = (pr.content or "").split()
            pr_trimmed = " ".join(pr_words[:100])
            if pr.user_id == voo_user.id:
                speaker = "Voo"
            elif pr.user_id == d.user_id:
                speaker = "Asker"
            else:
                pu = db.query(User).filter_by(id=pr.user_id).first()
                ph = (pu.username if pu and pu.username else (pu.name if pu and pu.name else "builder")).strip().lstrip("@")
                speaker = f"@{ph}"
            conv_lines.append(f"{speaker}: {pr_trimmed}")

        conversation_str = "\n".join(conv_lines) if conv_lines else "None"
        post_type_label = "Platform Poll" if (d.post_type == "poll" or d.poll_data) else "Question"
        content_words = (d.content or "").strip().split()
        trimmed_content = " ".join(content_words[:1500])

        followup_data, used_model = _generate_voo_followup_reply(
            db=db,
            post_id=discussion_id,
            post_type=post_type_label,
            question_title=d.title,
            question_content=trimmed_content,
            voo_angle=angle_log.angle or angle_log.opening,
            voo_test=angle_log.test,
            conversation=conversation_str,
            latest_reply_from=latest_reply_from,
            latest_reply_text=latest_reply_trimmed,
        )

        if not followup_data or not followup_data.get("respond"):
            logger.info(f"[voo-followup] Follow-up skipped or declined to respond for discussion {discussion_id}")
            return

        reply_body = followup_data.get("reply", "").strip()
        if not reply_body:
            return

        fresh_replier = db.query(User).filter_by(id=replier_user_id).first()
        fresh_handle = (fresh_replier.username if fresh_replier and fresh_replier.username else (fresh_replier.name if fresh_replier and fresh_replier.name else "builder")).strip().lstrip("@")

        full_followup_text = f"@{fresh_handle} {reply_body}"

        voo_reply = DiscussionReply(
            discussion_id=discussion_id,
            user_id=voo_user.id,
            content=full_followup_text,
            parent_reply_id=trigger_reply_id,
            tagged_user_ids=[replier_user_id]
        )
        db.add(voo_reply)
        db.flush()

        log_entry = VooFollowupLog(
            post_id=discussion_id,
            parent_message_id=trigger_reply_id,
            replier_user_id=replier_user_id,
            prompt_version=FOLLOWUP_PROMPT_VERSION,
            reply_type=followup_data.get("reply_type", "clarifying"),
            changes_original=bool(followup_data.get("changes_original", False)),
            reply=reply_body,
            reasoning=followup_data.get("reasoning", ""),
            model=used_model
        )
        db.add(log_entry)

        d.reply_count = (d.reply_count or 0) + 1
        db.commit()

        try:
            _notify_community(
                db, replier_user_id, "voo_followup", "🤖 Voo replied to you",
                f"Voo followed up: \"{reply_body[:60]}...\"",
                f"/dashboard/community?discussionId={discussion_id}",
            )
        except Exception as ne:
            logger.warning(f"[voo-followup] Notification failed: {ne}")

        await delete_cached(f"community:public_post:{discussion_id}")
        await delete_cached("community:discussions:*")
        logger.info(f"[voo-followup] Successfully posted Voo follow-up for discussion {discussion_id}")

    except Exception as e:
        logger.error(f"[voo-followup] Failed processing follow-up for discussion {discussion_id}: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def _generate_grok_takeaways(title: str, content: str, author_name: str = "A builder") -> Optional[List[str]]:
    """
    Calls configured LLM using voo_summary_system_prompt.txt and voo_summary_user_prompt.txt
    from the Voo Developer Pack with strict attribution, dash cleaning, and skip control.
    """
    total_words = len(f"{title} {content}".split())
    # Skip if title plus content is under 25 words per voo_code_spec.md Section 3
    if total_words < 25:
        logger.info(f"[voo-summary] Skipping summary: total words ({total_words}) < 25")
        return []

    system_prompt = get_voo_summary_system_prompt()
    if not system_prompt:
        logger.error("[voo-summary] Summary system prompt is empty")
        return None

    user_prompt_path = os.path.join(os.path.dirname(__file__), "voo_summary_user_prompt.txt")
    try:
        with open(user_prompt_path, "r", encoding="utf-8") as f:
            user_template = f.read()
    except Exception as e:
        logger.error(f"[voo-summary] Failed to read voo_summary_user_prompt.txt: {e}")
        return None

    # Clean author display name
    clean_author = "A builder"
    if author_name and author_name.strip():
        stripped = author_name.strip()
        if stripped.lower() not in ("a builder", "builder", "anonymous", "someone", "unknown", "user"):
            parts = stripped.split()
            first_name = parts[0].lstrip("@")
            if first_name:
                clean_author = first_name

    # Trim content to ~1,500 words
    content_words = content.split()
    trimmed_content = " ".join(content_words[:1500])

    user_prompt = user_template.format(
        author_name=clean_author,
        post_title=title,
        post_content=trimmed_content
    )

    raw_text, used_model = _call_voo_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        mode="summary",
        temperature=0.2,
        max_tokens=300
    )

    if not raw_text:
        return None

    parsed = _parse_json_response(raw_text)
    if not parsed:
        return None

    if parsed.get("skip") is True:
        return []

    takeaways = parsed.get("takeaways", [])
    if not isinstance(takeaways, list) or not takeaways:
        return []

    cleaned = []
    for t in takeaways[:3]:
        s = str(t).strip()
        s = _clean_dashes(s)
        s = re.sub(r"^Point\s*\d+[:\-.]\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^[›\-*\d.\s]+", "", s).strip()
        if s:
            cleaned.append(s)

    return cleaned[:3]


def generate_ai_takeaways_for_discussion(discussion_id: int, db: Session, force: bool = False) -> Optional[List[str]]:
    """
    Synchronous / On-demand helper to generate and store takeaways for a discussion.
    Used for Strategy 2 (on-demand lazy generation for previous posts).
    """
    try:
        d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
        if not d:
            return None
        post_type_val = getattr(d, 'post_type', None) or getattr(d, 'type', '') or ''
        if _is_question_discussion(post_type=post_type_val, title=d.title or "", content=d.content or ""):
            logger.info(f"[takeaways] Skipping takeaway generation for discussion {d.id} because it is a question.")
            return None
        if not force and d.ai_takeaways is not None and isinstance(d.ai_takeaways, list) and len(d.ai_takeaways) > 0:
            return d.ai_takeaways

        # Look up author name for attribution
        author_user = db.query(User).filter_by(id=d.user_id).first() if d.user_id else None
        author_name = author_user.name if (author_user and author_user.name) else (
            author_user.username if (author_user and author_user.username) else "A builder"
        )
        post_title = d.title
        post_content = d.content

        takeaways = _generate_grok_takeaways(post_title, post_content, author_name=author_name)
        if takeaways is not None:
            try:
                d.ai_takeaways = takeaways
                db.add(d)
                db.commit()
                db.refresh(d)
                return takeaways
            except Exception as db_err:
                logger.warning(f"[takeaways] Session disconnected during LLM call; saving with fresh session: {db_err}")
                db.rollback()
                with SessionLocal() as fresh_db:
                    fresh_d = fresh_db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
                    if fresh_d:
                        fresh_d.ai_takeaways = takeaways
                        fresh_db.add(fresh_d)
                        fresh_db.commit()
                        return takeaways
    except Exception as e:
        logger.error(f"generate_ai_takeaways_for_discussion failed for post {discussion_id}: {e}")
        db.rollback()
    return None


def _async_generate_takeaways_worker(discussion_id: int, force: bool = False):
    """
    Background worker that runs after FastAPI HTTP response is sent.
    """
    db = SessionLocal()
    try:
        generate_ai_takeaways_for_discussion(discussion_id, db, force=force)
    finally:
        db.close()


def _log_activity(db: Session, user_id: int, action_type: str, target_id: Optional[int] = None, target_type: Optional[str] = None, target_name: Optional[str] = None):
    try:
        db.add(CommunityActivity(user_id=user_id, action_type=action_type, target_id=target_id, target_type=target_type, target_name=target_name))
    except Exception as e:
        logger.warning(f"Activity logging failed: {e}")


def _channel_dict(ch: CommunityChannel, joined_ids: Optional[set] = None) -> dict:
    is_member = ch.id in joined_ids if joined_ids is not None else False
    return {
        "id": ch.id, "name": ch.name, "slug": ch.slug, "description": ch.description,
        "category": ch.category, "member_count": ch.member_count,
        "members": ch.member_count,  # frontend alias
        "active": True,
        "isJoined": is_member, "is_member": is_member,
        "post_count": ch.post_count,
        "icon": ch.icon, "is_public": ch.is_public,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


class GiftChopsRequest(BaseModel):
    amount: int


_AUTHOR_GRADIENTS = [
    "from-orange-400 to-rose-500",
    "from-amber-400 to-orange-500",
    "from-rose-400 to-pink-500",
    "from-yellow-400 to-amber-500",
]

# All valid topic slugs that can be stored as post_type
_TOPIC_SLUGS = {
    'what-worked', 'tool-recommendations', 'collaboration-offers',
    'questions', 'shared-wins', 'resources', 'reflections', 'poll',
}


def _slugify(text: str) -> str:
    if not text:
        return "post"
    clean = re.sub(r'[^a-zA-Z0-9\s\-]', '', text).lower().strip()
    slug = re.sub(r'[\s\-]+', '-', clean)
    return slug or "post"


def _get_poll_payload(d: CommunityDiscussion, current_user: Optional[User] = None, db: Optional[Session] = None) -> Optional[dict]:
    poll_data = getattr(d, 'poll_data', None)
    if not poll_data or not isinstance(poll_data, dict):
        return None
    raw_options = poll_data.get("options", [])
    if not raw_options or not isinstance(raw_options, list):
        return None

    votes = getattr(d, 'poll_votes', None)
    if votes is None or not isinstance(votes, list) or len(votes) == 0:
        if db:
            votes = db.query(DiscussionPollVote).filter_by(discussion_id=d.id).all()
        else:
            try:
                from database.pg_connections import SessionLocal
                with SessionLocal() as s:
                    votes = s.query(DiscussionPollVote).filter_by(discussion_id=d.id).all()
            except Exception:
                votes = []

    total_votes = len(votes)
    counts = {}
    user_voted_idx = None

    for v in votes:
        opt_idx = getattr(v, 'option_index', 0)
        counts[opt_idx] = counts.get(opt_idx, 0) + 1
        if current_user and getattr(v, 'user_id', None) == current_user.id:
            user_voted_idx = opt_idx

    formatted_options = []
    for idx, opt in enumerate(raw_options):
        text = opt if isinstance(opt, str) else (opt.get("text", "") if isinstance(opt, dict) else str(opt))
        cnt = counts.get(idx, 0)
        pct = round((cnt / total_votes * 100), 1) if total_votes > 0 else 0.0
        formatted_options.append({
            "id": idx,
            "text": text,
            "votes": cnt,
            "count": cnt,
            "percentage": pct,
        })

    # Calculate expiration status
    expires_at_raw = poll_data.get("expires_at")
    duration_val = poll_data.get("duration", "none")
    is_closed = False
    time_remaining_str = None

    if expires_at_raw:
        try:
            clean_iso = str(expires_at_raw).replace('Z', '+00:00')
            expires_dt = datetime.fromisoformat(clean_iso)
            now = datetime.now(timezone.utc)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            
            diff = expires_dt - now
            if diff.total_seconds() <= 0:
                is_closed = True
                time_remaining_str = "Final results · Poll closed"
            else:
                secs = int(diff.total_seconds())
                days = secs // 86400
                hours = (secs % 86400) // 3600
                mins = (secs % 3600) // 60
                if days > 0:
                    time_remaining_str = f"{days}d {hours}h left" if hours > 0 else f"{days}d left"
                elif hours > 0:
                    time_remaining_str = f"{hours}h {mins}m left"
                else:
                    time_remaining_str = f"{max(1, mins)}m left"
        except Exception:
            is_closed = False
            time_remaining_str = None

    return {
        "options": formatted_options,
        "total_votes": total_votes,
        "user_voted_option": user_voted_idx,
        "is_closed": is_closed,
        "expires_at": expires_at_raw,
        "duration": duration_val,
        "time_remaining": time_remaining_str,
    }


def _bg_increment_view_count(discussion_id: int):
    """Increment discussion view count asynchronously in the background."""
    try:
        with SessionLocal() as session:
            session.query(CommunityDiscussion).filter(CommunityDiscussion.id == discussion_id).update(
                {CommunityDiscussion.view_count: func.coalesce(CommunityDiscussion.view_count, 0) + 1}
            )
            session.commit()
    except Exception as e:
        logger.warning(f"[community] Background view count increment error for {discussion_id}: {e}")


def _discussion_dict(
    d: CommunityDiscussion,
    liked_ids: Optional[set] = None,
    saved_ids: Optional[set] = None,
    include_quoted: bool = True,
    current_user: Optional[User] = None,
    db: Optional[Session] = None,
    recent_likers_map: Optional[Dict[int, List[dict]]] = None
) -> dict:
    has_liked = d.id in liked_ids if liked_ids is not None else False
    has_saved = d.id in saved_ids if saved_ids is not None else False
    post_type_val = getattr(d, 'post_type', None) or 'discussion'

    # Return topic slug as a plain string so the frontend can filter by it directly.
    # Generic 'discussion' posts fall back to the actual backend channel object.
    if post_type_val == 'reflection':
        channel_display: any = 'reflections'
    elif post_type_val in _TOPIC_SLUGS:
        channel_display = post_type_val
    else:
        channel_display = {"id": d.channel.id, "name": d.channel.name, "slug": d.channel.slug} if d.channel else None

    author_obj = None
    author_is_paid = False
    if d.user:
        name = d.user.name or "Member"
        author_sub = (getattr(d.user, 'subscription_status', '') or '').strip().lower()
        author_is_paid = bool(author_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(d.user, 'is_admin', False))
        author_obj = {
            "id": d.user.id,
            "name": name,
            "initials": name[:2].upper(),
            "gradient": _AUTHOR_GRADIENTS[d.user.id % len(_AUTHOR_GRADIENTS)],
            "role": getattr(d.user, 'role', '') or '',
            "total_chops": d.user.total_chops or 0,
            "is_paid": author_is_paid,
        }

    quoted_dict = None
    if include_quoted and getattr(d, 'quoted_discussion', None) is not None:
        try:
            quoted_dict = _discussion_dict(d.quoted_discussion, liked_ids=liked_ids, saved_ids=saved_ids, include_quoted=False, current_user=current_user, db=db)
        except Exception:
            quoted_dict = None

    spice_cnt = getattr(d, 'spice_count', 0) or 0
    raw_takeaways = getattr(d, 'ai_takeaways', None)

    tagged_ids = getattr(d, 'tagged_user_ids', None) or []
    visibility_val = getattr(d, 'visibility', 'public') or 'public'

    slug_val = _slugify(d.title or "")

    is_q_post = _is_question_discussion(post_type=post_type_val, title=d.title or "", content=d.content or "")
    has_valid_takeaways = bool(author_is_paid and raw_takeaways and not is_q_post)
    takeaways_val = raw_takeaways if has_valid_takeaways else None

    recent_likers = []
    if recent_likers_map is not None:
        recent_likers = recent_likers_map.get(d.id, [])
    elif db and (d.like_count or 0) > 0:
        try:
            recent_likes_rows = (
                db.query(User.id, User.name, User.username)
                .join(DiscussionLike, DiscussionLike.user_id == User.id)
                .filter(DiscussionLike.discussion_id == d.id)
                .order_by(DiscussionLike.created_at.desc())
                .limit(3)
                .all()
            )
            recent_likers = [
                {"id": r[0], "name": r[1] or "Member", "username": r[2] or ""}
                for r in recent_likes_rows
            ]
        except Exception:
            recent_likers = []

    return {
        "id": d.id, "channel_id": d.channel_id, "title": d.title, "content": d.content,
        "slug": slug_val,
        "canonical_url": f"https://lavoo.io/l/thebuildroom/posts/{d.id}/{slug_val}",
        "tags": d.tags or [], "like_count": d.like_count, "reply_count": d.reply_count,
        "likes": d.like_count, "replies": d.reply_count,
        "pinned": d.is_pinned, "is_pinned": d.is_pinned,
        "hot": d.like_count >= 10,
        "view_count": d.view_count, "has_liked": has_liked, "liked_by_user": has_liked,
        "isBookmarked": has_saved, "is_saved": has_saved, "saved_by_user": has_saved, "bookmarked": has_saved,
        "chops_gifted": d.chops_gifted or 0,
        "spice_count": spice_cnt, "spiced": spice_cnt, "spices": spice_cnt,
        "quoted_discussion_id": getattr(d, 'quoted_discussion_id', None),
        "quoted_discussion": quoted_dict,
        "takeaways": takeaways_val,
        "has_takeaways": has_valid_takeaways,
        "is_question": is_q_post,
        "author_is_paid": author_is_paid,
        "type": post_type_val,
        "analysis_id": getattr(d, 'analysis_id', None),
        "analysis_goal": getattr(d, 'analysis_goal', None),
        "mission_task": getattr(d, 'mission_task', None),
        "tagged_user_ids": tagged_ids,
        "visibility": visibility_val,
        "poll": _get_poll_payload(d, current_user=current_user, db=db),
        "voo_status": getattr(d, 'voo_status', 'untracked') or 'untracked',
        "voo_reply_id": getattr(d, 'voo_reply_id', None),
        "is_resolved": getattr(d, 'is_resolved', False) or False,
        "decision_note": getattr(d, 'decision_note', None),
        "chosen_reply_id": getattr(d, 'chosen_reply_id', None),
        "author": author_obj,
        "channel": channel_display,
        "recent_likers": recent_likers,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


EVENT_TYPE_MAP = {"live": "Live", "workshop": "Workshop", "webinar": "Webinar"}

def _event_dict(ev: CommunityEvent, registered_ids: Optional[set] = None) -> dict:
    is_registered = ev.id in registered_ids if registered_ids is not None else False
    formatted_date = ev.scheduled_at.strftime("%b %d, %Y") if ev.scheduled_at else None
    formatted_time = ev.scheduled_at.strftime("%I:%M %p") if ev.scheduled_at else None
    frontend_type = EVENT_TYPE_MAP.get((ev.event_type or "").lower(), ev.event_type or "Live")
    return {
        "id": ev.id, "title": ev.title, "description": ev.description,
        "event_type": ev.event_type, "type": frontend_type,
        "date": formatted_date, "time": formatted_time,
        "attendees": ev.attendee_count, "attendee_count": ev.attendee_count,
        "registered": is_registered, "is_registered": is_registered,
        "scheduled_at": ev.scheduled_at.isoformat() if ev.scheduled_at else None,
        "duration_minutes": ev.duration_minutes, "max_attendees": ev.max_attendees,
        "host_name": ev.host_name, "meeting_link": ev.meeting_link,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


# ─── Content moderation ─────────────────────────────────────────────────────

_DEROGATORY_TERMS = {
    "nigger", "nigga", "faggot", "fag", "retard", "retarded", "cunt",
    "kike", "spic", "chink", "gook", "wetback", "tranny", "dyke",
    "whore", "slut", "bitch", "bastard", "asshole", "motherfucker",
    "fuck you", "go fuck", "piece of shit", "piece of crap",
}

def _contains_derogatory_content(text: str) -> bool:
    lowered = text.lower()
    for term in _DEROGATORY_TERMS:
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, lowered):
            return True
    return False


# ─── Pydantic Models ────────────────────────────────────────────────────────

class CreateDiscussionRequest(BaseModel):
    title: str
    content: str
    channel_id: int
    tags: Optional[List[str]] = None
    type: Optional[str] = "discussion"  # "discussion" | "reflection" | "spiced" | "poll"
    tagged_user_ids: Optional[List[int]] = None
    visibility: Optional[str] = "public"  # "public" | "tagged_only"
    poll_options: Optional[List[str]] = None
    poll_duration: Optional[str] = "none"  # "none" | "24h" | "3d" | "7d"


class UpdateDiscussionRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    type: Optional[str] = None
    channel_id: Optional[int] = None
    visibility: Optional[str] = None
    analysis_id: Optional[int] = None
    step_id: Optional[str] = None
    task_id: Optional[str] = None


class VotePollRequest(BaseModel):
    option_index: int


class SpiceDiscussionRequest(BaseModel):
    content: str


class CreateReplyRequest(BaseModel):
    content: str
    parent_reply_id: Optional[int] = None
    tagged_user_ids: Optional[List[int]] = None


class ResolveDiscussionRequest(BaseModel):
    decision_note: Optional[str] = None
    chosen_reply_id: Optional[int] = None


class LikeReplyRequest(BaseModel):
    action: str  # "like" | "unlike"


class SaveItemRequest(BaseModel):
    item_id: int
    item_type: str


# ─── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_community_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    try:
        total_channels = db.query(CommunityChannel).count()
        total_discussions = db.query(CommunityDiscussion).count()
        total_events = db.query(CommunityEvent).filter_by(is_published=True).count()
        total_members = db.query(User).count()
        user_channels = db.query(ChannelMember).filter_by(user_id=current_user.id).count() if current_user else 0

        return {"success": True, "data": {
            "total_channels": total_channels,
            "total_discussions": total_discussions,
            "total_events": total_events,
            "total_members": total_members,
            "my_channels": user_channels,
        }}
    except Exception as e:
        logger.error(f"Community stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch community stats")


# ─── Channels ───────────────────────────────────────────────────────────────

@router.get("/channels/my")
async def get_my_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        memberships = db.query(ChannelMember).filter_by(user_id=current_user.id).all()
        joined = {m.channel_id for m in memberships}
        channels = [_channel_dict(m.channel, joined) for m in memberships if m.channel]
        return {"success": True, "data": channels}
    except Exception as e:
        logger.error(f"Get my channels error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch your channels")


@router.get("/channels/{channel_name}")
async def get_channel_by_name(
    channel_name: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(slug=channel_name).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    joined = {m.channel_id for m in db.query(ChannelMember.channel_id).filter_by(user_id=current_user.id).all()} if current_user else set()
    return {"success": True, "data": _channel_dict(ch, joined)}


@router.get("/channels")
async def get_channels(
    category: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    try:
        valid_slugs = list(_TOPIC_SLUGS)
        q = db.query(CommunityChannel).filter(CommunityChannel.slug.in_(valid_slugs))
        if category and category.lower() != "all":
            q = q.filter(CommunityChannel.category == category)
        channels = q.order_by(CommunityChannel.member_count.desc()).all()
        # Batch-fetch memberships to avoid N+1
        joined = {m.channel_id for m in db.query(ChannelMember.channel_id).filter_by(user_id=current_user.id).all()} if current_user else set()
        return {"success": True, "data": [_channel_dict(ch, joined) for ch in channels]}
    except Exception as e:
        logger.error(f"Get channels error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch channels")


@router.post("/channels/{channel_id}/join")
async def join_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ch = db.query(CommunityChannel).filter_by(id=channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = db.query(ChannelMember).filter_by(user_id=current_user.id, channel_id=channel_id).first()
    if existing:
        return {"success": True, "message": "Already a member"}

    db.add(ChannelMember(user_id=current_user.id, channel_id=channel_id))
    ch.member_count = (ch.member_count or 0) + 1
    db.commit()
    _log_activity(db, current_user.id, "joined_channel", channel_id, "channel", ch.name)
    return {"success": True, "message": f"Joined {ch.name}"}


@router.post("/channels/{channel_id}/leave")
async def leave_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    membership = db.query(ChannelMember).filter_by(user_id=current_user.id, channel_id=channel_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")

    ch = db.query(CommunityChannel).filter_by(id=channel_id).first()
    db.delete(membership)
    if ch and ch.member_count > 0:
        ch.member_count -= 1
    db.commit()
    return {"success": True, "message": "Left channel"}


# ─── Discussions ─────────────────────────────────────────────────────────────

def _summarize_mission_title(text: str, max_chars: int = 80) -> str:
    """Word-bounded summary of a mission's full task text for the reflection
    post card's title slot — caps length like the old `[:80]` slice did, but
    never cuts a word in half."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    words = text.split()
    out, length = [], 0
    for w in words:
        add = len(w) + (1 if out else 0)
        if length + add > max_chars - 1:  # leave room for the ellipsis
            break
        out.append(w)
        length += add
    return (' '.join(out) + '…') if out else text[:max_chars - 1] + '…'


def _resolve_geo_bucket(country_code: Optional[str]) -> str:
    """
    Normalizes a country code into one of four geo buckets:
    - 'NG' -> 'nigeria'
    - 'US' -> 'us'
    - 'GB' / 'UK' -> 'uk'
    - other -> 'row' (Rest of World)
    """
    if not country_code:
        return "row"
    code = country_code.strip().upper()
    if code == "NG":
        return "nigeria"
    if code == "US":
        return "us"
    if code in ("GB", "UK"):
        return "uk"
    return "row"


_BACKEND_IP_GEO_CACHE: dict = {}  # {ip: (country_code, expire_timestamp)}

def _lookup_ip_country(ip: str) -> Optional[str]:
    """
    Fast server-side fallback IP lookup with in-memory caching and short timeout.
    """
    if not ip or ip in ("127.0.0.1", "localhost", "::1") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
        return None
    import time
    now = time.time()
    cached = _BACKEND_IP_GEO_CACHE.get(ip)
    if cached and cached[1] > now:
        return cached[0]

    # Try geojs.io
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"https://get.geojs.io/v1/ip/country/{ip}.json")
            if resp.status_code == 200:
                data = resp.json()
                code = data.get("country")
                if code and len(str(code).strip()) == 2:
                    clean_code = str(code).strip().upper()
                    _BACKEND_IP_GEO_CACHE[ip] = (clean_code, now + 3600)
                    return clean_code
    except Exception:
        pass

    # Fallback to ipwho.is
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"https://ipwho.is/{ip}")
            if resp.status_code == 200:
                data = resp.json()
                code = data.get("country_code")
                if code and len(str(code).strip()) == 2:
                    clean_code = str(code).strip().upper()
                    _BACKEND_IP_GEO_CACHE[ip] = (clean_code, now + 3600)
                    return clean_code
    except Exception:
        pass

    return None


def _extract_country_code(
    request: Optional[Request] = None,
    explicit_country: Optional[str] = None,
    current_user: Optional[User] = None
) -> str:
    """
    Resolves client country from:
    1. Explicit query parameter or query override (e.g., country=NG or country=US)
    2. Cloudflare edge header (cf-ipcountry)
    3. Client forwarded country headers (x-user-country, x-country-code, x-country)
    4. Server-side IP lookup fallback (cached)
    5. User profile country (if available on User model)
    6. Defaults to 'ROW'
    """
    if explicit_country and len(explicit_country.strip()) == 2:
        return explicit_country.strip().upper()

    if request:
        # 1. Check Cloudflare edge header
        cf_country = request.headers.get("cf-ipcountry")
        if cf_country and len(cf_country.strip()) == 2 and cf_country.strip().upper() not in ("XX", "T1"):
            return cf_country.strip().upper()

        # 2. Client forwarded header (sent with 0ms by frontend geo.ts)
        user_country = (
            request.headers.get("x-user-country")
            or request.headers.get("x-country-code")
            or request.headers.get("x-country")
        )
        if user_country and len(user_country.strip()) == 2 and user_country.strip().upper() not in ("XX", "T1"):
            return user_country.strip().upper()

        # 3. Server-side IP geo-lookup fallback (only if headers absent)
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = ""
        if forwarded_for and isinstance(forwarded_for, str):
            client_ip = forwarded_for.split(",")[0].strip()
        if not client_ip:
            x_real = request.headers.get("x-real-ip")
            if x_real and isinstance(x_real, str):
                client_ip = x_real.strip()
            elif getattr(request, 'client', None) and hasattr(request.client, 'host') and isinstance(request.client.host, str):
                client_ip = request.client.host.strip()
        if client_ip:
            ip_country = _lookup_ip_country(client_ip)
            if ip_country:
                return ip_country

    if current_user and getattr(current_user, "country", None):
        c = str(current_user.country).strip().upper()
        if len(c) == 2:
            return c

    return "ROW"


_INSIGHT_CARDS_CACHE: dict = {"data": None, "expires_at": 0}

def _get_geo_weighted_insights(db: Session, geo_bucket: str) -> List[dict]:
    """
    Fetches active FounderInsightCard records with 120s in-memory caching:
    - 'us': 60% US : 40% Global
    - 'uk': 60% UK : 40% Global
    - 'nigeria': 60% Nigeria/African Tech : 40% Global
    - 'row': 70% Global : 30% US
    """
    import time
    now = time.time()
    insights_raw = None
    if _INSIGHT_CARDS_CACHE["data"] is not None and _INSIGHT_CARDS_CACHE["expires_at"] > now:
        insights_raw = _INSIGHT_CARDS_CACHE["data"]
    else:
        insights_raw = db.query(FounderInsightCard).filter(FounderInsightCard.is_active == True).order_by(FounderInsightCard.created_at.desc()).all()
        _INSIGHT_CARDS_CACHE["data"] = insights_raw
        _INSIGHT_CARDS_CACHE["expires_at"] = now + 120.0

    if not insights_raw:
        return []

    def _to_dict(card: FounderInsightCard) -> dict:
        return {
            "id": f"insight_{card.id}",
            "type": "founder_insight",
            "isStat": True,
            "big": card.highlight_stat or "",
            "highlight_stat": card.highlight_stat or "",
            "headline": card.insight_text,
            "insight_text": card.insight_text,
            "source": card.source,
            "category": card.category or "global",
            "accent": card.accent_color or "#e87a02",
            "accent_color": card.accent_color or "#e87a02",
            "created_at": card.created_at.isoformat() if card.created_at else None
        }

    # Partition by category
    by_cat: dict = {
        "us": [],
        "uk": [],
        "nigeria": [],
        "global": []
    }

    for card in insights_raw:
        cat = (card.category or "global").lower().strip()
        if cat in ("us", "united_states", "usa", "us_tech"):
            by_cat["us"].append(_to_dict(card))
        elif cat in ("uk", "united_kingdom", "gb", "britain", "uk_tech", "europe"):
            by_cat["uk"].append(_to_dict(card))
        elif cat in ("nigeria", "ng", "african_tech", "africa", "west_africa"):
            by_cat["nigeria"].append(_to_dict(card))
        else:
            by_cat["global"].append(_to_dict(card))

    all_available = [_to_dict(c) for c in insights_raw]

    # Select primary and secondary pools and ratios
    if geo_bucket == "us":
        pool_primary = by_cat["us"]
        pool_secondary = by_cat["global"] or by_cat["nigeria"] or by_cat["uk"]
        ratio_primary, ratio_secondary = 3, 2  # 60% : 40%
    elif geo_bucket == "uk":
        pool_primary = by_cat["uk"]
        pool_secondary = by_cat["global"] or by_cat["us"] or by_cat["nigeria"]
        ratio_primary, ratio_secondary = 3, 2  # 60% : 40%
    elif geo_bucket == "nigeria":
        pool_primary = by_cat["nigeria"]
        pool_secondary = by_cat["global"] or by_cat["us"] or by_cat["uk"]
        ratio_primary, ratio_secondary = 3, 2  # 60% : 40%
    else:  # 'row'
        pool_primary = by_cat["global"] or by_cat["us"]
        pool_secondary = by_cat["us"] or by_cat["uk"] or by_cat["nigeria"]
        ratio_primary, ratio_secondary = 7, 3  # 70% : 30%

    if not pool_primary and not pool_secondary:
        return all_available
    if not pool_primary:
        pool_primary = pool_secondary or all_available
    if not pool_secondary:
        pool_secondary = pool_primary or all_available

    # Generate blended sequence
    blended = []
    total_slots = max(len(pool_primary) + len(pool_secondary), 10)
    p_idx = 0
    s_idx = 0

    while len(blended) < total_slots:
        for _ in range(ratio_primary):
            if pool_primary:
                blended.append(pool_primary[p_idx % len(pool_primary)])
                p_idx += 1
        for _ in range(ratio_secondary):
            if pool_secondary:
                blended.append(pool_secondary[s_idx % len(pool_secondary)])
                s_idx += 1
        if len(blended) >= 30:
            break

    return blended


_MISSION_REFLECTIONS_CACHE: dict = {"data": [], "expires_at": 0}

def _get_cached_mission_reflections(db: Session) -> List[dict]:
    """
    Fetches and caches completed mission roadmap reflection items for 60 seconds
    to prevent querying and parsing multi-MB BusinessAnalysis JSON trees on every feed request.
    """
    import time
    now = time.time()
    if _MISSION_REFLECTIONS_CACHE["data"] and _MISSION_REFLECTIONS_CACHE["expires_at"] > now:
        return _MISSION_REFLECTIONS_CACHE["data"]

    reflections = []
    try:
        # Exclude only users who have explicitly opted out of sharing reflections
        opted_out_user_ids = {
            row[0] for row in db.query(UserSettings.user_id).filter(
                UserSettings.show_mission_comments_in_community == False
            ).all()
        }
        explicit_user_opt_outs = {
            row[0] for row in db.query(User.id).filter(
                User.share_reflections == False
            ).all()
        }
        excluded_ids = opted_out_user_ids.union(explicit_user_opt_outs)

        query = db.query(BusinessAnalysis, User).join(User, BusinessAnalysis.user_id == User.id)
        if excluded_ids:
            query = query.filter(~BusinessAnalysis.user_id.in_(excluded_ids))

        analyses = (
            query
            .filter(BusinessAnalysis.user_progress != None)
            .order_by(BusinessAnalysis.updated_at.desc())
            .limit(30)
            .all()
        )

        seen_reflection_keys = set()

        for analysis, author in analyses:
            up_raw = analysis.user_progress
            if isinstance(up_raw, str):
                try:
                    up = json.loads(up_raw)
                except Exception:
                    up = {}
            elif isinstance(up_raw, dict):
                up = up_raw
            else:
                up = {}

            if not isinstance(up, dict) or not up:
                continue

            roadmap_tasks = _flatten_roadmap_tasks(analysis)
            task_by_frontend_id = {t.get('frontend_id'): t.get('text') for t in roadmap_tasks if isinstance(t, dict)}
            task_by_index = {idx + 1: t.get('text') for idx, t in enumerate(roadmap_tasks) if isinstance(t, dict)}

            completion_dates = up.get('completion_dates', {}) if isinstance(up.get('completion_dates'), dict) else {}
            reflections_dict = up.get('reflections', {}) if isinstance(up.get('reflections'), dict) else {}
            roadmap_comments = up.get('roadmap_comments', {}) if isinstance(up.get('roadmap_comments'), dict) else {}

            # 1. Primary: Step reflections created on mission step completion
            for step_id, text in reflections_dict.items():
                if not text or not isinstance(text, str):
                    continue
                clean_text = text.strip()
                if len(clean_text) < 3 or clean_text.lower().strip('.!') in (
                    'test', 'testing', 'tes', 'tesst', 'text', 'test2', 'tessssst', 'reesss', 'done', 'testtt'
                ):
                    continue

                ref_key = f"{analysis.id}_{step_id}"
                if ref_key in seen_reflection_keys:
                    continue
                seen_reflection_keys.add(ref_key)

                # Determine task title
                full_title = ""
                if '_action_' in str(step_id):
                    try:
                        step_num = int(str(step_id).split('_action_')[-1])
                        full_title = task_by_index.get(step_num) or ""
                    except Exception:
                        full_title = ""
                if not full_title:
                    full_title = task_by_frontend_id.get(str(step_id)) or ""

                created_at = completion_dates.get(step_id) or (analysis.updated_at.isoformat() if analysis.updated_at else None)

                reflections.append({
                    "id": f"mr_{analysis.id}_{step_id}",
                    "type": "mission_reflection",
                    "title": full_title if full_title else clean_text[:80],
                    "mission_task": full_title if full_title else clean_text[:80],
                    "analysis_goal": analysis.business_goal,
                    "analysis_id": analysis.id,
                    "step_id": str(step_id),
                    "content": clean_text,
                    "excerpt": clean_text[:160],
                    "tags": [],
                    "like_count": 0, "reply_count": 0,
                    "likes": 0, "replies": 0,
                    "pinned": False, "is_pinned": False,
                    "hot": False,
                    "view_count": 0,
                    "has_liked": False, "liked_by_user": False,
                    "chops_gifted": 0,
                    "author": {
                        "id": author.id,
                        "name": author.name or "Member",
                        "initials": (author.name or "M")[:2].upper(),
                        "gradient": _AUTHOR_GRADIENTS[author.id % len(_AUTHOR_GRADIENTS)],
                        "role": getattr(author, 'role', '') or 'Founder',
                        "total_chops": author.total_chops or 0,
                    },
                    "channel": "reflections",
                    "created_at": created_at,
                    "timeAgo": created_at,
                    "updated_at": None,
                })

            # 2. Secondary: Roadmap comments (if user added legacy or extra task comments)
            for task_id, comments in roadmap_comments.items():
                if not isinstance(comments, list):
                    continue
                for comment in comments:
                    if not isinstance(comment, dict):
                        continue
                    text = comment.get('text', '').strip()
                    if not text or len(text) < 3 or text.lower().strip('.!') in (
                        'test', 'testing', 'tes', 'tesst', 'text', 'test2', 'tessssst', 'reesss', 'done', 'testtt'
                    ):
                        continue
                    raw_cid = str(comment.get('id') or f"{analysis.id}_{task_id}")
                    if raw_cid.startswith('rc_'):
                        raw_cid = raw_cid[3:]
                    if not raw_cid.startswith(f"{analysis.id}_"):
                        comment_id = f"{analysis.id}_{raw_cid}"
                    else:
                        comment_id = raw_cid

                    ref_key = f"{analysis.id}_{comment_id}"
                    if ref_key in seen_reflection_keys:
                        continue
                    seen_reflection_keys.add(ref_key)

                    created_at = comment.get('createdAt') or (analysis.updated_at.isoformat() if analysis.updated_at else None)
                    full_title = task_by_frontend_id.get(task_id) or ""

                    reflections.append({
                        "id": f"rc_{comment_id}",
                        "type": "mission_reflection",
                        "title": full_title if full_title else text[:80],
                        "mission_task": full_title if full_title else text[:80],
                        "analysis_goal": analysis.business_goal,
                        "analysis_id": analysis.id,
                        "step_id": str(task_id),
                        "task_id": str(task_id),
                        "comment_id": str(comment.get('id') or ''),
                        "content": text,
                        "excerpt": text[:160],
                        "tags": [],
                        "like_count": 0, "reply_count": 0,
                        "likes": 0, "replies": 0,
                        "pinned": False, "is_pinned": False,
                        "hot": False,
                        "view_count": 0,
                        "has_liked": False, "liked_by_user": False,
                        "chops_gifted": 0,
                        "author": {
                            "id": author.id,
                            "name": author.name or "Member",
                            "initials": (author.name or "M")[:2].upper(),
                            "gradient": _AUTHOR_GRADIENTS[author.id % len(_AUTHOR_GRADIENTS)],
                            "role": getattr(author, 'role', '') or 'Founder',
                            "total_chops": author.total_chops or 0,
                        },
                        "channel": "reflections",
                        "created_at": created_at,
                        "timeAgo": created_at,
                        "updated_at": None,
                    })

        # Sort all reflections by creation date descending
        reflections.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        _MISSION_REFLECTIONS_CACHE["data"] = reflections[:30]
        _MISSION_REFLECTIONS_CACHE["expires_at"] = now + 60.0
    except Exception as reflection_err:
        logger.warning(f"Mission reflections fetch error: {reflection_err}")
    return _MISSION_REFLECTIONS_CACHE["data"]


@router.get("/discussions")
async def get_discussions(
    request: Request,
    country: Optional[str] = Query(None),
    channel_id: Optional[int] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    try:
        detected_country = _extract_country_code(request, explicit_country=country, current_user=current_user)
        geo_bucket = _resolve_geo_bucket(detected_country)
        cache_key = f"community:discussions:geo:{geo_bucket}:ch:{channel_id}:lim:{limit}:off:{offset}"
        cached = await get_cached(cache_key)
        if cached is not None:
            items = cached.get("data") if isinstance(cached, dict) else (cached if isinstance(cached, list) else None)
            if items and isinstance(items, list):
                # Bypass stale cache if any reflection item is missing mission_task
                has_stale_reflection = False
                for item in items:
                    if isinstance(item, dict) and item.get("type") == "mission_reflection" and not item.get("mission_task"):
                        has_stale_reflection = True
                        break
                if not has_stale_reflection:
                    post_ids = [i.get("id") for i in items if isinstance(i, dict) and isinstance(i.get("id"), int)]
                    if post_ids:
                        if current_user:
                            user_likes = {row[0] for row in db.query(DiscussionLike.discussion_id).filter(
                                DiscussionLike.user_id == current_user.id,
                                DiscussionLike.discussion_id.in_(post_ids)
                            ).all()}
                            bm_saves = {row[0] for row in db.query(DiscussionBookmark.discussion_id).filter(
                                DiscussionBookmark.user_id == current_user.id,
                                DiscussionBookmark.discussion_id.in_(post_ids)
                            ).all()}
                            tbl_saves = {row[0] for row in db.query(SavedItem.item_id).filter(
                                SavedItem.user_id == current_user.id,
                                SavedItem.item_id.in_(post_ids)
                            ).all()}
                            user_saves = bm_saves.union(tbl_saves)
                            for item in items:
                                if isinstance(item, dict) and isinstance(item.get("id"), int):
                                    pid = item["id"]
                                    item["has_liked"] = pid in user_likes
                                    item["liked_by_user"] = pid in user_likes
                                    item["isBookmarked"] = pid in user_saves
                                    item["is_saved"] = pid in user_saves
                                    item["saved_by_user"] = pid in user_saves
                                    item["bookmarked"] = pid in user_saves
                        else:
                            for item in items:
                                if isinstance(item, dict):
                                    item["has_liked"] = False
                                    item["liked_by_user"] = False
                                    item["isBookmarked"] = False
                                    item["is_saved"] = False
                                    item["saved_by_user"] = False
                                    item["bookmarked"] = False

                        # Rehydrate poll state in real-time for all cached items
                        poll_pids = [
                            i["id"] for i in items
                            if isinstance(i, dict) and isinstance(i.get("id"), int) and (i.get("type") == "poll" or i.get("poll") is not None)
                        ]
                        if poll_pids:
                            poll_discussions = db.query(CommunityDiscussion).filter(CommunityDiscussion.id.in_(poll_pids)).all()
                            poll_map = {p.id: _get_poll_payload(p, current_user=current_user, db=db) for p in poll_discussions}
                            for item in items:
                                if isinstance(item, dict) and item.get("id") in poll_map:
                                    item["poll"] = poll_map[item["id"]]

                        # Rehydrate recent_likers in real-time for all cached items
                        posts_needing_likers = [
                            i.get("id") for i in items
                            if isinstance(i, dict)
                            and isinstance(i.get("id"), int)
                            and ((i.get("like_count") or i.get("likes") or 0) > 0 or not i.get("recent_likers"))
                        ]
                        if posts_needing_likers:
                            try:
                                rl_rows = (
                                    db.query(DiscussionLike.discussion_id, User.id, User.name, User.username)
                                    .join(User, DiscussionLike.user_id == User.id)
                                    .filter(DiscussionLike.discussion_id.in_(posts_needing_likers))
                                    .order_by(DiscussionLike.discussion_id, DiscussionLike.created_at.desc())
                                    .all()
                                )
                                rl_map: Dict[int, List[dict]] = {}
                                for disc_id, u_id, u_name, u_uname in rl_rows:
                                    if disc_id not in rl_map:
                                        rl_map[disc_id] = []
                                    if len(rl_map[disc_id]) < 3:
                                        rl_map[disc_id].append({
                                            "id": u_id,
                                            "name": u_name or "Member",
                                            "username": u_uname or ""
                                        })
                                for item in items:
                                    if isinstance(item, dict) and isinstance(item.get("id"), int):
                                        pid = item["id"]
                                        if pid in rl_map:
                                            item["recent_likers"] = rl_map[pid]
                                        elif "recent_likers" not in item:
                                            item["recent_likers"] = []
                            except Exception as e:
                                logger.warning(f"[community] Cache rehydrate recent_likers error: {e}")

                    return cached

        # Eager load user and channel relationships to eliminate N+1 queries
        q = db.query(CommunityDiscussion).options(
            joinedload(CommunityDiscussion.user),
            joinedload(CommunityDiscussion.channel)
        )
        if channel_id:
            q = q.filter_by(channel_id=channel_id)

        # Enforce Tag-Gated Visibility:
        # If visibility == 'tagged_only', post is visible ONLY IF user is author, tagged, or moderator/admin
        is_mod_or_admin = bool(current_user and (current_user.is_admin or (getattr(current_user, 'role', '') in ('moderator', 'admin'))))
        if not is_mod_or_admin:
            if current_user:
                q = q.filter(
                    or_(
                        CommunityDiscussion.visibility == 'public',
                        CommunityDiscussion.visibility == None,
                        CommunityDiscussion.user_id == current_user.id,
                        func.cast(CommunityDiscussion.tagged_user_ids, String).contains(str(current_user.id))
                    )
                )
            else:
                q = q.filter(
                    or_(
                        CommunityDiscussion.visibility == 'public',
                        CommunityDiscussion.visibility == None
                    )
                )

        discussions = q.order_by(CommunityDiscussion.is_pinned.desc(), CommunityDiscussion.created_at.desc()).offset(offset).limit(limit).all()
        # Batch-fetch likes and bookmarks to avoid N+1
        discussion_ids = [d.id for d in discussions]
        liked = {row[0] for row in db.query(DiscussionLike.discussion_id).filter(
            DiscussionLike.user_id == current_user.id,
            DiscussionLike.discussion_id.in_(discussion_ids)
        ).all()} if (current_user and discussion_ids) else set()

        bm_saved = {row[0] for row in db.query(DiscussionBookmark.discussion_id).filter(
            DiscussionBookmark.user_id == current_user.id,
            DiscussionBookmark.discussion_id.in_(discussion_ids)
        ).all()} if (current_user and discussion_ids) else set()

        tbl_saved = {row[0] for row in db.query(SavedItem.item_id).filter(
            SavedItem.user_id == current_user.id,
            SavedItem.item_id.in_(discussion_ids)
        ).all()} if (current_user and discussion_ids) else set()

        saved = bm_saved.union(tbl_saved)

        recent_likers_map: Dict[int, List[dict]] = {}
        if discussion_ids:
            try:
                recent_likes_rows = (
                    db.query(DiscussionLike.discussion_id, User.id, User.name, User.username)
                    .join(User, DiscussionLike.user_id == User.id)
                    .filter(DiscussionLike.discussion_id.in_(discussion_ids))
                    .order_by(DiscussionLike.discussion_id, DiscussionLike.created_at.desc())
                    .all()
                )
                for disc_id, u_id, u_name, u_uname in recent_likes_rows:
                    if disc_id not in recent_likers_map:
                        recent_likers_map[disc_id] = []
                    if len(recent_likers_map[disc_id]) < 3:
                        recent_likers_map[disc_id].append({
                            "id": u_id,
                            "name": u_name or "Member",
                            "username": u_uname or ""
                        })
            except Exception as e:
                logger.warning(f"[community] Batch-fetch recent likers failed: {e}")

        result = [
            _discussion_dict(
                d,
                liked_ids=liked,
                saved_ids=saved,
                current_user=current_user,
                db=db,
                recent_likers_map=recent_likers_map
            )
            for d in discussions
        ]

        # Fast cached mission roadmap reflections
        cached_reflections = _get_cached_mission_reflections(db)
        if cached_reflections:
            result.extend(cached_reflections)

        # Interleave Geo-Weighted Builder Insights & Decision Engine Reflections into the discussion stream (4 Standard : 1 Insight : 4 Standard : 1 Reflection)
        try:
            insight_cards = _get_geo_weighted_insights(db, geo_bucket)

            std_posts = [p for p in result if p.get("type") != "mission_reflection"]
            ref_posts = sorted(
                [p for p in result if p.get("type") == "mission_reflection"],
                key=lambda x: str(x.get("created_at") or ""),
                reverse=True
            )

            if (insight_cards or ref_posts) and std_posts:
                interleaved = []
                std_i, ins_i, ref_i = 0, 0, 0
                cycle = 0

                while std_i < len(std_posts) or ins_i < len(insight_cards) or ref_i < len(ref_posts):
                    # 1. Add up to 4 standard posts
                    for _ in range(4):
                        if std_i < len(std_posts):
                            interleaved.append(std_posts[std_i])
                            std_i += 1

                    # 2. Alternating cadence: Even cycle = Insight, Odd cycle = Decision Engine Reflection
                    if cycle % 2 == 0:
                        if ins_i < len(insight_cards):
                            interleaved.append(insight_cards[ins_i % len(insight_cards)])
                            ins_i += 1
                        elif ref_i < len(ref_posts):
                            interleaved.append(ref_posts[ref_i])
                            ref_i += 1
                    else:
                        if ref_i < len(ref_posts):
                            interleaved.append(ref_posts[ref_i])
                            ref_i += 1
                        elif ins_i < len(insight_cards):
                            interleaved.append(insight_cards[ins_i % len(insight_cards)])
                            ins_i += 1

                    cycle += 1
                    if std_i >= len(std_posts) and ins_i >= len(insight_cards) and ref_i >= len(ref_posts):
                        break

                result = interleaved
        except Exception as interleave_err:
            logger.warning(f"Feed interleaving error: {interleave_err}")

        response = {"success": True, "data": result}
        await set_cached(cache_key, response, ttl_seconds=60)
        return response
    except Exception as e:
        logger.error(f"Get discussions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch discussions")

@router.post("/cron/process-reflections")
async def cron_process_pending_reflections(db: Session = Depends(get_db)):
    """
    Background Cron Service: Runs every 5 minutes to process completed mission reflections,
    respecting the user's 'show_mission_comments_in_community' preference setting.
    """
    try:
        opted_in_user_ids = {
            row[0] for row in db.query(UserSettings.user_id).filter(
                UserSettings.show_mission_comments_in_community == True
            ).all()
        }

        completed_analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.status == "completed"
        ).order_by(BusinessAnalysis.updated_at.desc()).limit(20).all()

        published_count = 0
        for analysis in completed_analyses:
            if analysis.user_id not in opted_in_user_ids:
                continue

            up = analysis.user_progress or {}
            roadmap_comments = up.get("roadmap_comments", {}) if isinstance(up, dict) else {}
            if not isinstance(roadmap_comments, dict) or not roadmap_comments:
                continue

            for task_id, comments in roadmap_comments.items():
                if not isinstance(comments, list):
                    continue
                for comment in comments:
                    text = comment.get("text", "").strip()
                    if not text:
                        continue
                    user = db.query(User).filter_by(id=analysis.user_id).first()
                    if user:
                        user.total_chops = (user.total_chops or 0) + 50
                        published_count += 1

        db.commit()
        return {"success": True, "published_count": published_count}
    except Exception as e:
        logger.error(f"Cron process reflections error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/discussions/{discussion_id}")
async def get_discussion(
    discussion_id: int,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    d = (
        db.query(CommunityDiscussion)
        .options(
            joinedload(CommunityDiscussion.user),
            joinedload(CommunityDiscussion.channel),
            selectinload(CommunityDiscussion.replies).joinedload(DiscussionReply.user),
            selectinload(CommunityDiscussion.replies).selectinload(DiscussionReply.sub_replies).joinedload(DiscussionReply.user),
        )
        .filter(CommunityDiscussion.id == discussion_id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # Increment view count in background without blocking response or holding DB commit
    background_tasks.add_task(_bg_increment_view_count, d.id)

    # Strategy 2: On-Demand "Lazy" Generation in background if ai_takeaways is NULL (Paid authors only, non-questions)
    author_user = d.user
    author_sub = (getattr(author_user, 'subscription_status', '') or '').strip().lower() if author_user else ''
    author_is_paid = bool(author_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(author_user, 'is_admin', False) if author_user else False)

    post_type_val = getattr(d, 'post_type', None) or getattr(d, 'type', '') or ''
    is_q = _is_question_discussion(post_type=post_type_val, title=d.title or "", content=d.content or "")
    if author_is_paid and d.ai_takeaways is None and not is_q:
        background_tasks.add_task(_async_generate_takeaways_worker, d.id)

    def _serialise_reply_node(r) -> dict:
        is_bot = bool(
            (r.user and getattr(r.user, 'is_bot', False))
            or (r.user and getattr(r.user, 'role', '') == 'ai_bot')
            or (r.user and (getattr(r.user, 'username', '') or '').lower() in ('voo', 'vooangle'))
            or (r.user and (getattr(r.user, 'name', '') or '').lower() in ('voo', 'voo angle', "voo's angle"))
        )
        author_name = "Voo's Angle" if is_bot else (r.user.name if r.user else "Member")
        return {
            "id": r.id,
            "content": r.content,
            "like_count": r.like_count,
            "parent_reply_id": r.parent_reply_id,
            "author": {
                "id": r.user.id,
                "name": author_name,
                "username": getattr(r.user, 'username', '') or '',
                "role": getattr(r.user, 'role', '') or '',
                "is_bot": is_bot,
                "total_chops": r.user.total_chops or 0,
                "is_paid": bool(
                    (getattr(r.user, 'subscription_status', '') or '').strip().lower()
                    in ("active", "trialing", "pro", "premium", "lifetime")
                ) or bool(getattr(r.user, 'is_admin', False)),
            } if r.user else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "sub_replies": [],
        }

    all_replies = (
        db.query(DiscussionReply)
        .options(joinedload(DiscussionReply.user))
        .filter_by(discussion_id=discussion_id)
        .order_by(DiscussionReply.created_at.asc())
        .all()
    )
    reply_map = {r.id: _serialise_reply_node(r) for r in all_replies}
    top_level = []
    for r in all_replies:
        item = reply_map[r.id]
        if r.parent_reply_id and r.parent_reply_id in reply_map:
            reply_map[r.parent_reply_id]["sub_replies"].append(item)
        elif r.parent_reply_id is None:
            top_level.append(item)
    replies = top_level

    liked = {d.id} if (current_user and db.query(DiscussionLike.id).filter_by(user_id=current_user.id, discussion_id=d.id).first()) else set()
    saved = {d.id} if (current_user and db.query(SavedItem.id).filter_by(user_id=current_user.id, item_id=d.id).first()) else set()
    data = _discussion_dict(d, liked_ids=liked, saved_ids=saved, current_user=current_user, db=db, recent_likers_map=None)
    data["replies"] = replies
    return {"success": True, "data": data}


@router.get("/discussions/{discussion_id}/takeaways")
async def get_discussion_takeaways(
    discussion_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    post_type_val = getattr(d, 'post_type', None) or getattr(d, 'type', '') or ''
    if _is_question_discussion(post_type=post_type_val, title=d.title or "", content=d.content or ""):
        return {"status": "none", "has_takeaways": False, "takeaways": None}

    author_user = db.query(User).filter_by(id=d.user_id).first() if d.user_id else None
    author_sub = (getattr(author_user, 'subscription_status', '') or '').strip().lower() if author_user else ''
    author_is_paid = bool(author_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(author_user, 'is_admin', False) if author_user else False)

    if not author_is_paid:
        return {"status": "none", "has_takeaways": False, "takeaways": None}

    if not force and d.ai_takeaways is not None and isinstance(d.ai_takeaways, list):
        if len(d.ai_takeaways) == 0:
            return {"status": "none", "has_takeaways": False, "takeaways": None}
        return {"status": "ready", "takeaways": d.ai_takeaways}

    # Strategy 2: On-Demand Lazy Generation for paid authors (schedule in background and return status)
    background_tasks.add_task(_async_generate_takeaways_worker, d.id, force=force)
    return {"status": "generating", "takeaways": None}


@router.post("/discussions")
async def create_discussion(
    body: CreateDiscussionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if _contains_derogatory_content(body.title) or _contains_derogatory_content(body.content):
        raise HTTPException(
            status_code=422,
            detail="Your post contains language that isn't allowed in the Lavoo Build Room. Please review your content and try again."
        )

    ch = db.query(CommunityChannel).filter_by(id=body.channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    _all_valid_types = {'discussion', 'reflection'} | _TOPIC_SLUGS
    raw_type = (body.type or 'discussion').strip().lower()
    post_type = raw_type if raw_type in _all_valid_types else 'discussion'

    tagged_ids = body.tagged_user_ids or []
    if not tagged_ids:
        found_usernames = re.findall(r'@([a-zA-Z0-9_]+)', f"{body.title} {body.content}")
        if found_usernames:
            matching = db.query(User.id).filter(func.lower(User.username).in_([u.lower() for u in found_usernames])).all()
            tagged_ids = [m[0] for m in matching]

    visibility_val = "tagged_only" if body.visibility == "tagged_only" else "public"

    poll_payload = None
    clean_options = [o.strip() for o in (body.poll_options or []) if isinstance(o, str) and o.strip()]
    if post_type == 'poll' or len(clean_options) >= 2:
        if len(clean_options) >= 2:
            post_type = 'poll'
            duration_str = (body.poll_duration or "none").strip().lower()
            expires_at_iso = None
            
            now = datetime.now(timezone.utc)
            if duration_str == "24h" or duration_str == "1d":
                expires_at_iso = (now + timedelta(days=1)).isoformat()
            elif duration_str == "3d":
                expires_at_iso = (now + timedelta(days=3)).isoformat()
            elif duration_str == "7d":
                expires_at_iso = (now + timedelta(days=7)).isoformat()
            else:
                duration_str = "none"

            poll_payload = {
                "options": clean_options,
                "duration": duration_str,
                "expires_at": expires_at_iso
            }

    # Detect if post is an inquiry / question and schedule Voo initial answer in 10 minutes (paid accounts only)
    is_question = _is_question_discussion(post_type=post_type, title=body.title, content=body.content)
    sub_status = (getattr(current_user, 'subscription_status', '') or '').strip().lower()
    is_paid_user = bool(sub_status in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(current_user, 'is_admin', False))
    should_schedule_voo = is_question and is_paid_user

    interval_minutes = int(os.getenv("VOO_BOT_INTERVAL_MINUTES", "10"))
    voo_init_status = "scheduled" if should_schedule_voo else "untracked"
    voo_init_scheduled_for = (datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)) if should_schedule_voo else None

    d = CommunityDiscussion(
        channel_id=body.channel_id, user_id=current_user.id,
        title=body.title.strip(), content=body.content.strip(),
        tags=body.tags or [], post_type=post_type,
        tagged_user_ids=tagged_ids, visibility=visibility_val,
        poll_data=poll_payload,
        voo_status=voo_init_status,
        voo_scheduled_for=voo_init_scheduled_for
    )
    db.add(d)
    ch.post_count = (ch.post_count or 0) + 1
    current_user.total_chops = (current_user.total_chops or 0) + 10
    db.commit()
    db.refresh(d)
    await delete_cached("community:discussions:*")
    
    _log_activity(db, current_user.id, "posted", d.id, "discussion", d.title)

    # Trigger notifications for tagged users
    if tagged_ids:
        for tagged_id in set(tagged_ids):
            if tagged_id != current_user.id:
                try:
                    _notify_community(
                        db, tagged_id, "user_tagged", "You were tagged in a Build Room post!",
                        f"{current_user.name} tagged you in: \"{d.title[:60]}\"",
                        f"/dashboard/community?discussionId={d.id}",
                    )
                except Exception:
                    pass
        db.commit()

    # Automatically schedule background AI generation for new posts upon creation if creator is paid/pro/trial and NOT a question
    creator_sub = (getattr(current_user, 'subscription_status', '') or '').strip().lower()
    creator_is_paid = bool(creator_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(current_user, 'is_admin', False))
    if creator_is_paid and not is_question:
        background_tasks.add_task(_async_generate_takeaways_worker, d.id)

    return {"success": True, "data": _discussion_dict(d, set(), current_user=current_user)}


@router.post("/discussions/{discussion_id}/poll/vote")
async def vote_poll(
    discussion_id: int,
    body: VotePollRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if not d.poll_data or not isinstance(d.poll_data, dict):
        raise HTTPException(status_code=400, detail="This discussion is not a poll")

    raw_options = d.poll_data.get("options", [])
    if body.option_index < 0 or body.option_index >= len(raw_options):
        raise HTTPException(status_code=422, detail="Invalid poll option index")

    poll_payload = _get_poll_payload(d, current_user=current_user, db=db)
    if poll_payload and poll_payload.get("is_closed"):
        raise HTTPException(status_code=400, detail="This poll has closed and is no longer accepting votes.")

    # Strictly enforce ONE VOTE per user: if user already voted, return status already_voted with canonical poll
    existing_vote = db.query(DiscussionPollVote).filter_by(
        discussion_id=discussion_id, user_id=current_user.id
    ).first()
    if existing_vote:
        return {
            "status": "already_voted",
            "message": "You have already voted in this poll.",
            "poll": _get_poll_payload(d, current_user=current_user, db=db)
        }

    vote = DiscussionPollVote(
        discussion_id=discussion_id,
        user_id=current_user.id,
        option_index=body.option_index
    )
    db.add(vote)
    db.commit()
    db.expire_all()
    await delete_cached("community:discussions:*")

    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    return {
        "status": "success",
        "poll": _get_poll_payload(d, current_user=current_user, db=db)
    }


@router.get("/public/posts/{discussion_id}")
async def get_public_discussion(
    discussion_id: int,
    db: Session = Depends(get_db)
):
    cache_key = f"community:public_post:{discussion_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    d = (
        db.query(CommunityDiscussion)
        .options(
            joinedload(CommunityDiscussion.user),
            joinedload(CommunityDiscussion.channel),
        )
        .filter(CommunityDiscussion.id == discussion_id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if getattr(d, 'visibility', 'public') == 'tagged_only':
        raise HTTPException(status_code=403, detail="This post is private to tagged members")
        
    discussion_data = _discussion_dict(d, liked_ids=set(), saved_ids=set(), current_user=None, db=db, recent_likers_map=None)
    
    replies_raw = (
        db.query(DiscussionReply)
        .options(joinedload(DiscussionReply.user))
        .filter_by(discussion_id=discussion_id)
        .order_by(DiscussionReply.created_at.asc())
        .all()
    )
    author_ids = list(set([r.user_id for r in replies_raw] + [d.user_id]))
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}
    
    reply_map = {}
    for r in replies_raw:
        r_author = authors.get(r.user_id) or r.user
        is_bot = bool(
            getattr(r_author, 'is_bot', False)
            or (r_author and getattr(r_author, 'role', '') == 'ai_bot')
            or (r_author and (getattr(r_author, 'username', '') or '').lower() in ('voo', 'vooangle'))
            or (r_author and (getattr(r_author, 'name', '') or '').lower() in ('voo', 'voo angle', "voo's angle"))
        )
        author_name = "Voo's Angle" if is_bot else (r_author.name if r_author else "Member")
        reply_map[r.id] = {
            "id": r.id,
            "user_id": r.user_id,
            "content": r.content,
            "like_count": r.like_count or 0,
            "chops_gifted": getattr(r, 'chops_gifted', 0) or 0,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "parent_reply_id": r.parent_reply_id,
            "author": {
                "id": r.user_id,
                "name": author_name,
                "username": getattr(r_author, 'username', '') if r_author else '',
                "initials": (author_name or "M")[:2].upper(),
                "role": getattr(r_author, 'role', '') if r_author else '',
                "is_bot": is_bot,
                "is_paid": bool(
                    (getattr(r_author, 'subscription_status', '') or '').strip().lower()
                    in ("active", "trialing", "pro", "premium", "lifetime")
                ) or bool(getattr(r_author, 'is_admin', False) if r_author else False),
            },
            "sub_replies": []
        }

    top_level = []
    for r in replies_raw:
        item = reply_map[r.id]
        if r.parent_reply_id and r.parent_reply_id in reply_map:
            reply_map[r.parent_reply_id]["sub_replies"].append(item)
        elif r.parent_reply_id is None:
            top_level.append(item)

    resp = {
        "success": True,
        "data": {
            **discussion_data,
            "replies": top_level,
            "replies_list": list(reply_map.values())
        }
    }
    await set_cached(cache_key, resp, ttl_seconds=60)
    return resp


def _resolve_reflection_target(
    str_id: str,
    body: Optional[UpdateDiscussionRequest] = None,
    current_user: Optional[User] = None,
    db: Optional[Session] = None
) -> Tuple[Optional[BusinessAnalysis], bool, str, str]:
    """
    Robust resolver for mission reflections and roadmap comments.
    Supports formats:
      - mr_{analysis_id}_{step_id}
      - rc_{comment_id}
      - rc_{analysis_id}_{comment_id}
      - rc_{analysis_id}_{task_id}_{comment_id}
      - comment-... or comment_...
      - Resolves by body.analysis_id and body.step_id/task_id
      - Resolves by searching current_user's analyses and all analyses
    Returns: (analysis, is_rc, clean_id, step_id)
    """
    if not db:
        return None, False, str_id, ""

    is_rc = str_id.startswith("rc_")
    clean_id = str_id
    while clean_id.startswith("mr_") or clean_id.startswith("rc_"):
        if clean_id.startswith("rc_"):
            is_rc = True
        clean_id = clean_id[3:]

    analysis = None
    step_id = ""

    # Strategy 1: clean_id starts with numeric analysis_id
    parts = clean_id.split("_", 1)
    if parts and parts[0].isdigit():
        cand_id = int(parts[0])
        analysis = db.query(BusinessAnalysis).filter_by(id=cand_id).first()
        if analysis:
            step_id = parts[1] if len(parts) > 1 else ""

    # Strategy 2: Explicit analysis_id in request body
    if not analysis and body and getattr(body, "analysis_id", None):
        try:
            cand_id = int(body.analysis_id)
            analysis = db.query(BusinessAnalysis).filter_by(id=cand_id).first()
            if analysis:
                step_id = getattr(body, "step_id", None) or getattr(body, "task_id", None) or clean_id
        except Exception:
            pass

    # Search helper for user_progress
    def search_in_analyses(analyses_list):
        nonlocal analysis, is_rc, step_id, clean_id
        for a in analyses_list:
            up = a.user_progress
            if isinstance(up, str):
                try:
                    up = json.loads(up)
                except Exception:
                    up = {}
            if not isinstance(up, dict):
                continue

            # Check roadmap_comments
            rcs = up.get("roadmap_comments", {})
            if isinstance(rcs, dict):
                for tid, comms in rcs.items():
                    if isinstance(comms, list):
                        for c in comms:
                            if isinstance(c, dict):
                                cid = str(c.get("id") or "")
                                ctext = (c.get("text") or "").strip()
                                if cid and (
                                    cid == clean_id
                                    or cid == str_id
                                    or str_id.endswith(cid)
                                    or cid in str_id
                                    or clean_id in cid
                                    or (parts and len(parts) > 1 and parts[1] == cid)
                                ):
                                    analysis = a
                                    is_rc = True
                                    step_id = tid
                                    clean_id = cid
                                    return True
                                if body and getattr(body, "content", None) and ctext and ctext == body.content.strip():
                                    analysis = a
                                    is_rc = True
                                    step_id = tid
                                    clean_id = cid
                                    return True

            # Check reflections dictionary
            refs = up.get("reflections", {})
            if isinstance(refs, dict):
                for rid, rtext in refs.items():
                    s_rid = str(rid)
                    r_content = (rtext or "").strip() if isinstance(rtext, str) else ""
                    if (
                        s_rid == clean_id
                        or s_rid == str_id
                        or clean_id.endswith(s_rid)
                        or (clean_id.startswith(f"{a.id}_") and s_rid == clean_id[len(f"{a.id}_"):])
                    ):
                        analysis = a
                        is_rc = False
                        step_id = s_rid
                        return True
                    if body and getattr(body, "content", None) and r_content and r_content == body.content.strip():
                        analysis = a
                        is_rc = False
                        step_id = s_rid
                        return True
        return False

    # Strategy 3: Search within current user's analyses
    if not analysis and current_user:
        user_analyses = db.query(BusinessAnalysis).filter_by(user_id=current_user.id).all()
        search_in_analyses(user_analyses)

    # Strategy 4: Fallback search across recent analyses in system
    if not analysis:
        all_analyses = db.query(BusinessAnalysis).order_by(BusinessAnalysis.id.desc()).limit(250).all()
        search_in_analyses(all_analyses)

    return analysis, is_rc, clean_id, step_id


@router.put("/discussions/{discussion_id}")
async def update_discussion(
    discussion_id: str,
    body: UpdateDiscussionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    str_id = str(discussion_id).strip()
    is_reflection_candidate = (
        str_id.startswith("mr_")
        or str_id.startswith("rc_")
        or str_id.startswith("comment")
        or (body and getattr(body, "type", None) in ("reflection", "reflections", "mission_reflection"))
        or (body and getattr(body, "analysis_id", None) is not None)
    )

    if is_reflection_candidate:
        analysis, is_rc, raw_id, step_id = _resolve_reflection_target(
            str_id=str_id,
            body=body,
            current_user=current_user,
            db=db
        )

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis or reflection not found")

        # 1. Author / Admin Ownership check
        if analysis.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="You can only edit your own reflections")

        # 2. Paid / Pro Account Requirement check
        sub_status = getattr(current_user, 'subscription_status', '') or ''
        is_subscribed = bool(sub_status.lower() in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(current_user, 'is_admin', False))
        if not is_subscribed:
            raise HTTPException(
                status_code=403,
                detail="Editing reflections is exclusive to Lavoo Pro members. Please upgrade your account to edit reflections."
            )

        # 3. Content moderation check
        if body.content and _contains_derogatory_content(body.content):
            raise HTTPException(
                status_code=422,
                detail="Your reflection content contains language that isn't allowed in the Lavoo Build Room."
            )

        # 4. Apply update to user_progress
        up_raw = analysis.user_progress
        if isinstance(up_raw, str):
            try:
                user_progress = json.loads(up_raw)
            except Exception:
                user_progress = {}
        elif isinstance(up_raw, dict):
            user_progress = up_raw
        else:
            user_progress = {}

        new_content = (body.content or "").strip()

        if is_rc:
            updated_comment = False
            if "roadmap_comments" in user_progress and isinstance(user_progress["roadmap_comments"], dict):
                for t_id, comments in user_progress["roadmap_comments"].items():
                    if isinstance(comments, list):
                        for c in comments:
                            if isinstance(c, dict) and (
                                c.get("id") == raw_id
                                or c.get("id") == str_id
                                or str_id.endswith(str(c.get("id") or ""))
                                or (raw_id and str(c.get("id") or "") in raw_id)
                                or (t_id == step_id and len(comments) == 1)
                            ):
                                c["text"] = new_content
                                updated_comment = True
            if not updated_comment:
                if step_id and "roadmap_comments" in user_progress and isinstance(user_progress["roadmap_comments"], dict):
                    comms = user_progress["roadmap_comments"].get(step_id, [])
                    if isinstance(comms, list) and comms:
                        comms[0]["text"] = new_content
        else:
            if "reflections" not in user_progress or not isinstance(user_progress["reflections"], dict):
                user_progress["reflections"] = {}
            if step_id:
                user_progress["reflections"][step_id] = new_content
                if "_action_" in step_id:
                    try:
                        action_num = step_id.split("_action_")[-1]
                        user_progress["reflections"][action_num] = new_content
                        user_progress["reflections"][int(action_num)] = new_content
                    except Exception:
                        pass
                elif step_id.isdigit():
                    user_progress["reflections"][f"{analysis.id}_action_{step_id}"] = new_content

        analysis.user_progress = user_progress
        flag_modified(analysis, "user_progress")
        analysis.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(analysis)

        # 5. Invalidate caches so reflection updates instantly
        global _MISSION_REFLECTIONS_CACHE
        _MISSION_REFLECTIONS_CACHE["data"] = []
        _MISSION_REFLECTIONS_CACHE["expires_at"] = 0
        await delete_cached("community:discussions:*")
        await delete_cached(f"community:public_post:{str_id}")

        full_title = (body.title or "").strip() or (new_content[:80] if new_content else "Reflection")
        return {
            "success": True,
            "data": {
                "id": str_id,
                "type": "mission_reflection",
                "title": full_title,
                "mission_task": full_title,
                "analysis_goal": analysis.business_goal,
                "analysis_id": analysis.id,
                "step_id": step_id,
                "content": new_content,
                "excerpt": new_content[:160],
                "tags": [],
                "like_count": 0,
                "reply_count": 0,
                "likes": 0,
                "replies": 0,
                "pinned": False,
                "is_pinned": False,
                "hot": False,
                "view_count": 0,
                "has_liked": False,
                "liked_by_user": False,
                "chops_gifted": 0,
                "author": {
                    "id": current_user.id,
                    "name": current_user.name or "Member",
                    "initials": (current_user.name or "M")[:2].upper(),
                    "gradient": _AUTHOR_GRADIENTS[current_user.id % len(_AUTHOR_GRADIENTS)],
                    "role": getattr(current_user, 'role', '') or 'Founder',
                    "total_chops": current_user.total_chops or 0,
                },
                "channel": "reflections",
                "created_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
                "timeAgo": analysis.updated_at.isoformat() if analysis.updated_at else None,
                "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
            }
        }

    try:
        disc_id = int(str_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")

    d = db.query(CommunityDiscussion).filter_by(id=disc_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 1. Author / Admin Ownership check
    if d.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    
    # 2. Paid / Pro Account Requirement check
    sub_status = getattr(current_user, 'subscription_status', '') or ''
    is_subscribed = bool(sub_status.lower() in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(current_user, 'is_admin', False))
    if not is_subscribed:
        raise HTTPException(
            status_code=403,
            detail="Editing posts is exclusive to Lavoo Pro members. Please upgrade your account to edit discussions."
        )

    # 3. Content moderation check
    if body.title and _contains_derogatory_content(body.title):
        raise HTTPException(
            status_code=422,
            detail="Your post title contains language that isn't allowed in the Lavoo Build Room."
        )
    if body.content and _contains_derogatory_content(body.content):
        raise HTTPException(
            status_code=422,
            detail="Your post content contains language that isn't allowed in the Lavoo Build Room."
        )

    # 4. Apply updates
    if body.title is not None:
        d.title = body.title.strip()
    if body.content is not None:
        d.content = body.content.strip()
    if body.tags is not None:
        d.tags = body.tags
    if body.visibility in ("public", "tagged_only"):
        d.visibility = body.visibility
    if body.type is not None:
        _all_valid_types = {'discussion', 'reflection'} | _TOPIC_SLUGS
        raw_type = body.type.strip().lower()
        if raw_type in _all_valid_types:
            d.post_type = raw_type

    if body.channel_id is not None and body.channel_id != d.channel_id:
        new_ch = db.query(CommunityChannel).filter_by(id=body.channel_id).first()
        if new_ch:
            old_ch = db.query(CommunityChannel).filter_by(id=d.channel_id).first()
            if old_ch and old_ch.post_count > 0:
                old_ch.post_count -= 1
            new_ch.post_count = (new_ch.post_count or 0) + 1
            d.channel_id = new_ch.id

    d.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(d)
    await delete_cached("community:discussions:*")
    await delete_cached(f"community:public_post:{disc_id}")

    liked = {l.discussion_id for l in db.query(DiscussionLike).filter_by(user_id=current_user.id).all()} if current_user else set()
    saved = {b.discussion_id for b in db.query(DiscussionBookmark).filter_by(user_id=current_user.id).all()} if current_user else set()

    return {
        "success": True,
        "data": _discussion_dict(d, liked_ids=liked, saved_ids=saved, current_user=current_user)
    }


@router.put("/reflections/{reflection_id}")
async def update_reflection_endpoint(
    reflection_id: str,
    body: UpdateDiscussionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Direct alias for editing a mission reflection"""
    return await update_discussion(discussion_id=reflection_id, body=body, current_user=current_user, db=db)


@router.delete("/discussions/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    str_id = str(discussion_id).strip()
    is_reflection_candidate = (
        str_id.startswith("mr_")
        or str_id.startswith("rc_")
        or str_id.startswith("comment")
    )
    if is_reflection_candidate:
        analysis, is_rc, raw_id, step_id = _resolve_reflection_target(
            str_id=str_id,
            current_user=current_user,
            db=db
        )
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis or reflection not found")
        if analysis.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="You can only delete your own reflections")

        up_raw = analysis.user_progress
        if isinstance(up_raw, str):
            try:
                user_progress = json.loads(up_raw)
            except Exception:
                user_progress = {}
        elif isinstance(up_raw, dict):
            user_progress = up_raw
        else:
            user_progress = {}

        if is_rc:
            if "roadmap_comments" in user_progress and isinstance(user_progress["roadmap_comments"], dict):
                for t_id, comments in list(user_progress["roadmap_comments"].items()):
                    if isinstance(comments, list):
                        user_progress["roadmap_comments"][t_id] = [
                            c for c in comments
                            if isinstance(c, dict)
                            and c.get("id") != raw_id
                            and c.get("id") != str_id
                            and not str_id.endswith(str(c.get("id") or ""))
                        ]
        else:
            if "reflections" in user_progress and isinstance(user_progress["reflections"], dict):
                if step_id:
                    user_progress["reflections"].pop(step_id, None)
                    if "_action_" in step_id:
                        try:
                            action_num = step_id.split("_action_")[-1]
                            user_progress["reflections"].pop(action_num, None)
                        except Exception:
                            pass
                    elif step_id.isdigit():
                        user_progress["reflections"].pop(f"{analysis.id}_action_{step_id}", None)

        analysis.user_progress = user_progress
        flag_modified(analysis, "user_progress")
        analysis.updated_at = datetime.now(timezone.utc)
        db.commit()

        global _MISSION_REFLECTIONS_CACHE
        _MISSION_REFLECTIONS_CACHE["data"] = []
        _MISSION_REFLECTIONS_CACHE["expires_at"] = 0
        await delete_cached("community:discussions:*")
        return {"success": True, "message": "Reflection deleted successfully"}

    try:
        disc_id = int(str_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")

    d = db.query(CommunityDiscussion).filter_by(id=disc_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Post not found")
    if d.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    ch = db.query(CommunityChannel).filter_by(id=d.channel_id).first()
    if ch and ch.post_count > 0:
        ch.post_count -= 1
    db.delete(d)
    db.commit()
    await delete_cached(f"community:discussions:user:{current_user.id}:ch:{d.channel_id}:lim:20:off:0")
    await delete_cached(f"community:discussions:user:{current_user.id}:ch:None:lim:20:off:0")
    return {"success": True}


@router.delete("/reflections/{reflection_id}")
async def delete_reflection_endpoint(
    reflection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Direct alias for deleting a mission reflection"""
    return await delete_discussion(discussion_id=reflection_id, current_user=current_user, db=db)


@router.post("/discussions/{discussion_id}/pin")
async def pin_discussion(
    discussion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Post not found")
    # Anyone can pin/unpin any post
    d.is_pinned = not d.is_pinned
    db.commit()
    return {"success": True, "pinned": d.is_pinned}


@router.post("/discussions/{discussion_id}/like")
async def like_discussion(
    discussion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    existing = db.query(DiscussionLike).filter_by(user_id=current_user.id, discussion_id=discussion_id).first()
    if existing:
        # Unlike
        db.delete(existing)
        d.like_count = max(0, (d.like_count or 0) - 1)
        db.commit()
        await delete_cached("community:discussions:*")
        await delete_cached(f"community:public_post:{discussion_id}")
        recent_likes_rows = (
            db.query(User.id, User.name, User.username)
            .join(DiscussionLike, DiscussionLike.user_id == User.id)
            .filter(DiscussionLike.discussion_id == discussion_id)
            .order_by(DiscussionLike.created_at.desc())
            .limit(3)
            .all()
        )
        recent_likers = [
            {"id": r[0], "name": r[1] or "Member", "username": r[2] or ""}
            for r in recent_likes_rows
        ]
        return {"success": True, "liked": False, "like_count": d.like_count, "recent_likers": recent_likers}

    db.add(DiscussionLike(user_id=current_user.id, discussion_id=discussion_id))
    d.like_count = (d.like_count or 0) + 1
    db.commit()
    await delete_cached("community:discussions:*")
    await delete_cached(f"community:public_post:{discussion_id}")

    # Notify post owner (skip when liking own post)
    try:
        if d.user_id and d.user_id != current_user.id:
            actor_name = current_user.name or 'Someone'
            _notify_community(
                db, d.user_id, "community_cooked", f"{actor_name} thinks you cooked.",
                f"{actor_name} thinks you cooked with your post '{d.title[:60]}'",
                f"/dashboard/community/post/{discussion_id}",
            )
    except Exception as notif_err:
        logger.warning(f"Cooked notification creation failed: {notif_err}")

    _log_activity(db, current_user.id, "cooked", discussion_id, "discussion", d.title)

    recent_likes_rows = (
        db.query(User.id, User.name, User.username)
        .join(DiscussionLike, DiscussionLike.user_id == User.id)
        .filter(DiscussionLike.discussion_id == discussion_id)
        .order_by(DiscussionLike.created_at.desc())
        .limit(3)
        .all()
    )
    recent_likers = [
        {"id": r[0], "name": r[1] or "Member", "username": r[2] or ""}
        for r in recent_likes_rows
    ]
    return {"success": True, "liked": True, "like_count": d.like_count, "recent_likers": recent_likers}


@router.post("/discussions/{discussion_id}/gift_chops")
async def gift_chops_to_discussion(
    discussion_id: int,
    body: GiftChopsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if (current_user.total_chops or 0) < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient chops")

    current_user.total_chops = (current_user.total_chops or 0) - body.amount

    if d.user_id and d.user_id != current_user.id:
        author = db.query(User).filter_by(id=d.user_id).first()
        if author:
            author.total_chops = (author.total_chops or 0) + body.amount

    d.chops_gifted = (d.chops_gifted or 0) + body.amount
    db.commit()

    # Notify post owner (skip when gifting self)
    try:
        if d.user_id and d.user_id != current_user.id:
            _notify_community(
                db, d.user_id, "community_chops",
                f"{current_user.name or 'Someone'} gifted you {body.amount} Chops!",
                f"You received {body.amount} Chops for your post '{d.title[:60]}'",
                f"/dashboard/community/post/{discussion_id}",
            )
    except Exception as notif_err:
        logger.warning(f"Gift chops notification creation failed: {notif_err}")

    _log_activity(db, current_user.id, "gifted_chops", discussion_id, "discussion", d.title)
    return {"success": True, "chops_gifted": d.chops_gifted, "remaining_chops": current_user.total_chops}


@router.post("/discussions/{discussion_id}/spice")
async def spice_discussion(
    discussion_id: int,
    body: SpiceDiscussionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    content_text = (body.content or "").strip()
    if not content_text:
        raise HTTPException(status_code=400, detail="Spice insight content cannot be empty")

    if _contains_derogatory_content(content_text):
        raise HTTPException(
            status_code=422,
            detail="Your spice contains language that isn't allowed in the Lavoo Build Room. Please review your content and try again."
        )

    # Increment spice count on original discussion
    d.spice_count = (d.spice_count or 0) + 1

    # Create new discussion referencing original post as a quoted post
    spiced_post = CommunityDiscussion(
        channel_id=d.channel_id,
        user_id=current_user.id,
        title=d.title[:80],
        content=content_text,
        tags=d.tags or [],
        post_type="spiced",
        quoted_discussion_id=d.id,
    )
    db.add(spiced_post)

    # Award user chops for spicing / contributing insight
    current_user.total_chops = (current_user.total_chops or 0) + 10
    db.commit()
    db.refresh(spiced_post)

    # Notify original post owner (unless spicing own post)
    try:
        if d.user_id and d.user_id != current_user.id:
            _notify_community(
                db, d.user_id, "community_spice", f"{current_user.name or 'Someone'} spiced your post",
                content_text[:120], f"/dashboard/community/post/{d.id}",
            )
    except Exception as notif_err:
        logger.warning(f"Spice notification creation failed: {notif_err}")

    _log_activity(db, current_user.id, "spiced", d.id, "discussion", d.title)
    await delete_cached(f"community:discussions:user:{current_user.id}:ch:{d.channel_id}:lim:20:off:0")
    await delete_cached(f"community:discussions:user:{current_user.id}:ch:None:lim:20:off:0")

    liked = {spiced_post.id} if db.query(DiscussionLike).filter_by(user_id=current_user.id, discussion_id=spiced_post.id).first() else set()
    return {
        "success": True,
        "data": _discussion_dict(spiced_post, liked),
        "original_spice_count": d.spice_count,
    }


@router.post("/discussions/{discussion_id}/replies")
async def reply_to_discussion(
    discussion_id: int,
    body: CreateReplyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # Validate parent_reply_id belongs to the same discussion
    parent_reply_id = body.parent_reply_id
    if parent_reply_id is not None:
        parent = db.query(DiscussionReply).filter_by(id=parent_reply_id, discussion_id=discussion_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent reply not found")

    tagged_ids = body.tagged_user_ids or []
    if not tagged_ids:
        found_usernames = re.findall(r'@([a-zA-Z0-9_]+)', body.content)
        if found_usernames:
            matching = db.query(User.id).filter(func.lower(User.username).in_([u.lower() for u in found_usernames])).all()
            tagged_ids = [m[0] for m in matching]

    reply = DiscussionReply(
        discussion_id=discussion_id,
        user_id=current_user.id,
        content=body.content.strip(),
        parent_reply_id=parent_reply_id,
        tagged_user_ids=tagged_ids
    )
    db.add(reply)
    # Count all replies (including nested) so comment badge is accurate
    d.reply_count = (d.reply_count or 0) + 1
    current_user.total_chops = (current_user.total_chops or 0) + 5

    # Trigger Voo bot 10-minute answer timer for questions (paid author accounts only)
    author_user = db.query(User).filter_by(id=d.user_id).first() if d.user_id else None
    author_sub = (getattr(author_user, 'subscription_status', '') or '').strip().lower() if author_user else ''
    author_is_paid = bool(author_sub in ("active", "trialing", "pro", "premium", "lifetime")) or bool(getattr(author_user, 'is_admin', False) if author_user else False)

    is_pending_question = getattr(d, "voo_status", "untracked") == "pending_replies"
    is_untracked_question = (
        getattr(d, "voo_status", "untracked") == "untracked"
        and _is_question_discussion(getattr(d, "post_type", "") or "", d.title or "", d.content or "")
    )
    if (
        (is_pending_question or is_untracked_question)
        and author_is_paid
        and current_user.id != d.user_id
        and not getattr(current_user, "is_bot", False)
        and not getattr(d, "is_resolved", False)
        and getattr(d, "voo_status", "untracked") not in ("completed", "skipped")
    ):
        interval_minutes = int(os.getenv("VOO_BOT_INTERVAL_MINUTES", "10"))
        d.voo_status = "scheduled"
        d.voo_scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
        logger.info(f"[voo-bot] Scheduled Voo answer for discussion {discussion_id} in {interval_minutes}m (at {d.voo_scheduled_for})")

    db.commit()
    db.refresh(reply)
    await delete_cached(f"community:public_post:{discussion_id}")
    await delete_cached("community:discussions:*")

    # Notify post owner (skip when replying to own post)
    try:
        if d.user_id and d.user_id != current_user.id:
            _notify_community(
                db, d.user_id, "community_reply", f"{current_user.name or 'Someone'} replied to your post",
                body.content.strip()[:120], f"/dashboard/community?discussionId={discussion_id}",
            )

        # Notify tagged users in reply
        if tagged_ids:
            for tagged_id in set(tagged_ids):
                if tagged_id != current_user.id and tagged_id != d.user_id:
                    _notify_community(
                        db, tagged_id, "user_tagged", "You were tagged in a reply!",
                        f"{current_user.name} tagged you in a reply on: \"{d.title[:60]}\"",
                        f"/dashboard/community?discussionId={discussion_id}",
                    )

        db.commit()
    except Exception as notif_err:
        logger.warning(f"Notification creation failed: {notif_err}")

    # Voo Follow-up trigger check (Spec Section 5)
    voo_user = ensure_voo_bot_user(db)
    if current_user.id != voo_user.id:
        is_replying_to_voo = False
        if parent_reply_id is not None:
            parent_rep = db.query(DiscussionReply).filter_by(id=parent_reply_id).first()
            if parent_rep and parent_rep.user_id == voo_user.id:
                is_replying_to_voo = True

        tags_voo = bool(re.search(r"@voo\b", body.content, re.IGNORECASE))
        if is_replying_to_voo or tags_voo:
            logger.info(f"[voo-followup] Queuing follow-up task for discussion {discussion_id}, reply {reply.id} by user {current_user.id}")
            background_tasks.add_task(_process_voo_followup_task, discussion_id, reply.id, current_user.id)

    _log_activity(db, current_user.id, "replied", discussion_id, "discussion", d.title)
    return {"success": True, "data": {
        "id": reply.id, "content": reply.content, "like_count": 0,
        "parent_reply_id": reply.parent_reply_id,
        "author": {
            "id": current_user.id,
            "name": current_user.name,
            "username": getattr(current_user, 'username', '') or '',
            "role": getattr(current_user, 'role', '') or '',
            "is_bot": getattr(current_user, 'is_bot', False) or False,
            "total_chops": current_user.total_chops or 0,
        },
        "created_at": reply.created_at.isoformat() if reply.created_at else None,
        "sub_replies": [],
    }}


@router.patch("/discussions/{discussion_id}/resolve")
async def resolve_discussion(
    discussion_id: int,
    body: Optional[ResolveDiscussionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks a question discussion as resolved.
    Awards +20 Chops to the author for their decision note,
    and +20 Chops to the author of the chosen reply (Voo earns 0).
    Resolving does NOT lock the thread; members and Voo can continue replying.
    """
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    if d.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author can mark this discussion as resolved")
    
    d.is_resolved = True
    d.voo_status = "completed"

    author_chops_awarded = 20
    if body and body.decision_note:
        d.decision_note = body.decision_note.strip()
    current_user.total_chops = (current_user.total_chops or 0) + author_chops_awarded

    chosen_reply_awarded = 0
    if body and body.chosen_reply_id:
        d.chosen_reply_id = body.chosen_reply_id
        chosen_rep = db.query(DiscussionReply).filter_by(id=body.chosen_reply_id, discussion_id=discussion_id).first()
        if chosen_rep:
            voo_user = ensure_voo_bot_user(db)
            if chosen_rep.user_id != voo_user.id:
                rep_author = db.query(User).filter_by(id=chosen_rep.user_id).first()
                if rep_author:
                    rep_author.total_chops = (rep_author.total_chops or 0) + 20
                    chosen_reply_awarded = 20
                    try:
                        _notify_community(
                            db, rep_author.id, "chops_received", "You earned 20 Chops!",
                            f"Your reply on '{d.title[:40]}' was marked as the chosen solution.",
                            f"/dashboard/community?discussionId={discussion_id}"
                        )
                    except Exception as ne:
                        logger.warning(f"[resolve] Notification failed: {ne}")

    db.commit()
    await delete_cached(f"community:public_post:{discussion_id}")
    await delete_cached("community:discussions:*")
    logger.info(f"[voo-bot] Discussion {discussion_id} marked as resolved by user {current_user.id} (decision_note={bool(body and body.decision_note)}, chosen_reply={bool(body and body.chosen_reply_id)})")
    return {
        "success": True,
        "message": "Discussion marked as resolved",
        "is_resolved": True,
        "chops_awarded": author_chops_awarded,
        "chosen_reply_chops_awarded": chosen_reply_awarded
    }


@router.post("/discussions/{discussion_id}/replies/{reply_id}/like")
async def like_reply(
    discussion_id: int,
    reply_id: int,
    body: LikeReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reply = db.query(DiscussionReply).filter_by(id=reply_id, discussion_id=discussion_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    if body.action == "like":
        reply.like_count = (reply.like_count or 0) + 1
    else:
        reply.like_count = max(0, (reply.like_count or 0) - 1)
    db.commit()
    return {"success": True, "like_count": reply.like_count}


@router.post("/discussions/{discussion_id}/replies/{reply_id}/gift_chops")
async def gift_chops_to_reply(
    discussion_id: int,
    reply_id: int,
    body: GiftChopsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reply = db.query(DiscussionReply).filter_by(id=reply_id, discussion_id=discussion_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    if reply.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot gift chops to yourself")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if (current_user.total_chops or 0) < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient chops")
    current_user.total_chops = (current_user.total_chops or 0) - body.amount
    author = db.query(User).filter_by(id=reply.user_id).first()
    if author:
        author.total_chops = (author.total_chops or 0) + body.amount
    db.commit()

    # Notify reply owner (skip when gifting self)
    try:
        if reply.user_id and reply.user_id != current_user.id:
            _notify_community(
                db, reply.user_id, "community_chops",
                f"{current_user.name or 'Someone'} gifted you {body.amount} Chops!",
                f"You received {body.amount} Chops for your reply",
                f"/dashboard/community/post/{discussion_id}",
            )
    except Exception as notif_err:
        logger.warning(f"Reply gift chops notification creation failed: {notif_err}")

    return {"success": True, "remaining_chops": current_user.total_chops}


@router.delete("/discussions/{discussion_id}/replies/{reply_id}")
async def delete_reply(
    discussion_id: int,
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(DiscussionReply).filter_by(id=reply_id, discussion_id=discussion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reply not found")
    if r.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own replies")
    d = db.query(CommunityDiscussion).filter_by(id=discussion_id).first()
    if d and (d.reply_count or 0) > 0:
        d.reply_count = d.reply_count - 1
    db.delete(r)
    db.commit()
    return {"success": True}


# ─── Events ──────────────────────────────────────────────────────────────────

@router.get("/events/my")
async def get_my_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    regs = db.query(EventRegistration).filter_by(user_id=current_user.id).all()
    registered = {r.event_id for r in regs}
    events = [_event_dict(r.event, registered) for r in regs if r.event]
    return {"success": True, "data": events}


@router.get("/events")
async def get_events(
    type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        q = db.query(CommunityEvent).filter_by(is_published=True)
        if type and type.lower() != "all":
            q = q.filter(CommunityEvent.event_type == type)
        events = q.order_by(CommunityEvent.scheduled_at.asc()).all()
        # Batch-fetch registrations to avoid N+1
        event_ids = [ev.id for ev in events]
        registered = {r.event_id for r in db.query(EventRegistration.event_id).filter(
            EventRegistration.user_id == current_user.id,
            EventRegistration.event_id.in_(event_ids)
        ).all()} if event_ids else set()
        return {"success": True, "data": [_event_dict(ev, registered) for ev in events]}
    except Exception as e:
        logger.error(f"Get events error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")


@router.post("/events/{event_id}/register")
async def register_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ev = db.query(CommunityEvent).filter_by(id=event_id, is_published=True).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    if ev.max_attendees and ev.attendee_count >= ev.max_attendees:
        raise HTTPException(status_code=400, detail="Event is fully booked")

    existing = db.query(EventRegistration).filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        return {"success": True, "message": "Already registered"}

    db.add(EventRegistration(user_id=current_user.id, event_id=event_id))
    ev.attendee_count = (ev.attendee_count or 0) + 1
    db.commit()
    _log_activity(db, current_user.id, "registered_event", event_id, "event", ev.title)
    return {"success": True, "message": f"Registered for {ev.title}"}


@router.post("/events/{event_id}/unregister")
async def unregister_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reg = db.query(EventRegistration).filter_by(user_id=current_user.id, event_id=event_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Not registered")

    ev = db.query(CommunityEvent).filter_by(id=event_id).first()
    db.delete(reg)
    if ev and ev.attendee_count > 0:
        ev.attendee_count -= 1
    db.commit()
    return {"success": True, "message": "Unregistered from event"}


# ─── User Activity, Profile, Leaderboard ────────────────────────────────────

@router.get("/activity")
async def get_my_activity(
    limit: int = Query(12, le=100),
    type_filter: Optional[str] = Query(None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tf = type_filter.lower().strip() if type_filter else "all"
    all_events = []

    def clean_t(txt: Optional[str]) -> str:
        if not txt:
            return "a post"
        cleaned = re.sub(r"['\"]+", "", txt).strip()
        return cleaned if cleaned else "a post"

    # 1. Fetch User's Discussions (Posts & Reflections)
    if tf in ("all", "post", "discussions", "reflection", "reflections"):
        discs = db.query(CommunityDiscussion).filter_by(user_id=current_user.id).all()
        for d in discs:
            post_type_val = getattr(d, 'post_type', None) or 'discussion'
            title_text = clean_t(d.title or d.content[:80])
            
            if post_type_val == 'reflection':
                if tf not in ("all", "reflection", "reflections"):
                    continue
                action_title = f"Shared a reflection: {title_text}"
                type_str = "reflection"
                points = 50
            else:
                if tf not in ("all", "post", "discussions"):
                    continue
                action_title = f"Started a discussion: {title_text}"
                type_str = "post"
                points = 15

            all_events.append({
                "id": f"disc_{d.id}",
                "title": action_title,
                "type": type_str,
                "points": points,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "dt": d.created_at or datetime.min,
                "target_id": d.id,
                "target_type": "discussion",
                "target_name": title_text,
            })

    # 2. Fetch User's Replies
    if tf in ("all", "reply", "replies"):
        replies = db.query(DiscussionReply, CommunityDiscussion)\
            .join(CommunityDiscussion, DiscussionReply.discussion_id == CommunityDiscussion.id)\
            .filter(DiscussionReply.user_id == current_user.id).all()
        
        for reply, d in replies:
            title_text = clean_t(d.title)
            all_events.append({
                "id": f"reply_{reply.id}",
                "title": f"Replied to a post: {title_text}",
                "type": "reply",
                "points": 5,
                "created_at": reply.created_at.isoformat() if reply.created_at else None,
                "dt": reply.created_at or datetime.min,
                "target_id": d.id,
                "target_type": "discussion",
                "target_name": title_text,
            })

    # 3. Fetch User's Cooked Posts (Likes)
    if tf in ("all", "like", "cooked", "cook"):
        likes = db.query(DiscussionLike, CommunityDiscussion)\
            .join(CommunityDiscussion, DiscussionLike.discussion_id == CommunityDiscussion.id)\
            .filter(DiscussionLike.user_id == current_user.id).all()

        for like, d in likes:
            title_text = clean_t(d.title)
            all_events.append({
                "id": f"like_{like.id}",
                "title": f"You cooked a post: {title_text}",
                "type": "like",
                "points": 2,
                "created_at": like.created_at.isoformat() if like.created_at else None,
                "dt": like.created_at or datetime.min,
                "target_id": d.id,
                "target_type": "discussion",
                "target_name": title_text,
            })

    # 4. Fetch User's Bookmarks (DiscussionBookmark & SavedItem)
    if tf in ("all", "bookmark", "bookmarks", "save", "saved"):
        direct_bms = db.query(DiscussionBookmark, CommunityDiscussion)\
            .join(CommunityDiscussion, DiscussionBookmark.discussion_id == CommunityDiscussion.id)\
            .filter(DiscussionBookmark.user_id == current_user.id).all()

        for bm, d in direct_bms:
            title_text = clean_t(d.title)
            all_events.append({
                "id": f"bm_{bm.id}",
                "title": f"Saved a post: {title_text}",
                "type": "bookmark",
                "points": 3,
                "created_at": bm.created_at.isoformat() if bm.created_at else None,
                "dt": bm.created_at or datetime.min,
                "target_id": d.id,
                "target_type": "discussion",
                "target_name": title_text,
            })

        saved_items = db.query(SavedItem).filter_by(user_id=current_user.id).all()
        for item in saved_items:
            title_text = f"Saved item #{item.item_id}"
            target_id = item.item_id
            if item.item_type in ("discussion", "post"):
                d = db.query(CommunityDiscussion).filter_by(id=item.item_id).first()
                if d and d.title:
                    title_text = clean_t(d.title)
                    target_id = d.id

            all_events.append({
                "id": f"saved_{item.id}",
                "title": f"Saved a post: {title_text}",
                "type": "bookmark",
                "points": 3,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "dt": item.created_at or datetime.min,
                "target_id": target_id,
                "target_type": item.item_type,
                "target_name": title_text,
            })

    # 5. Fetch CommunityActivities for additional events (e.g. spiced)
    if tf in ("all", "post", "discussions"):
        activities = db.query(CommunityActivity).filter(
            CommunityActivity.user_id == current_user.id,
            CommunityActivity.action_type.in_(["spiced", "spice", "gifted_chops", "chops"])
        ).all()

        for a in activities:
            title_text = clean_t(a.target_name)
            act_type = (a.action_type or "post").lower()

            if act_type in ("spiced", "spice"):
                act_title = f"You spiced a post: {title_text}"
                pts = 10
            else:
                act_title = f"Gifted Chops to a post: {title_text}"
                pts = 5

            all_events.append({
                "id": f"act_{a.id}",
                "title": act_title,
                "type": "post",
                "points": pts,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "dt": a.created_at or datetime.min,
                "target_id": a.target_id,
                "target_type": a.target_type or "discussion",
                "target_name": title_text,
            })

    seen = set()
    unique_events = []
    for ev in all_events:
        key = (ev["type"], ev["target_id"], ev["title"])
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    unique_events.sort(key=lambda x: x["dt"], reverse=True)

    for ev in unique_events:
        ev.pop("dt", None)

    return {"success": True, "data": unique_events[:limit]}


@router.get("/profile")
async def get_my_community_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels_joined = db.query(ChannelMember).filter_by(user_id=current_user.id).count()
    posts_count = db.query(CommunityDiscussion).filter_by(user_id=current_user.id).count()
    events_count = db.query(EventRegistration).filter_by(user_id=current_user.id).count()
    replies_count = db.query(DiscussionReply).filter_by(user_id=current_user.id).count()

    higher_users = db.query(User).filter(User.total_chops > (current_user.total_chops or 0)).count()
    rank = higher_users + 1

    badges = []
    if posts_count > 0:
        badges.append({"name": "First Post", "icon": "MessageSquare", "color": "bg-blue-100 text-blue-600"})
    if replies_count >= 1:
        badges.append({"name": "Contributor", "icon": "ThumbsUp", "color": "bg-green-100 text-green-600"})
    if (current_user.total_chops or 0) >= 20:
        badges.append({"name": "Active Builder", "icon": "Calendar", "color": "bg-orange-100 text-orange-600"})
    if (current_user.total_chops or 0) >= 100:
        badges.append({"name": "Top Builder", "icon": "Award", "color": "bg-purple-100 text-purple-600"})

    return {"success": True, "data": {
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "total_chops": current_user.total_chops or 0,
        "totalPoints": current_user.total_chops or 0,
        "rank": rank,
        "streak": 7,
        "channels_joined": channels_joined,
        "posts": posts_count,
        "replies": replies_count,
        "events_registered": events_count,
        "badges": badges,
    }}


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(10, le=500),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    top_users = db.query(User).filter(
        User.is_active == True,
        (User.is_bot == False) | (User.is_bot.is_(None)),
        func.lower(User.username) != "voo",
        func.lower(User.username) != "vooangle",
        func.lower(User.name) != "voo",
        func.lower(User.name) != "voo angle",
        func.lower(User.name) != "voo's angle",
        User.email != "voo@lavoo.io"
    ).order_by(User.total_chops.desc(), User.created_at.asc()).limit(limit).all()

    return {"success": True, "data": [{
        "rank": idx + 1,
        "user_id": u.id,
        "name": u.name,
        "username": u.username,
        "total_chops": u.total_chops or 0,
        "referral_count": u.referral_count or 0,
        "joined_at": u.created_at.isoformat() if u.created_at else None,
    } for idx, u in enumerate(top_users)]}


# ─── Saved Items ─────────────────────────────────────────────────────────────

@router.get("/saved")
async def get_saved_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bms = db.query(DiscussionBookmark, CommunityDiscussion)\
        .join(CommunityDiscussion, DiscussionBookmark.discussion_id == CommunityDiscussion.id)\
        .filter(DiscussionBookmark.user_id == current_user.id)\
        .order_by(DiscussionBookmark.created_at.desc()).all()

    formatted = []
    seen_ids = set()

    for bm, d in bms:
        seen_ids.add(d.id)
        clean_t = re.sub(r"['\"]+", "", d.title).strip() if d.title else "a post"
        ch_name = d.channel.name or d.channel.slug if d.channel else "community"
        formatted.append({
            "id": f"bm_{bm.id}",
            "item_id": d.id,
            "item_type": "discussion",
            "title": clean_t,
            "channel": ch_name,
            "created_at": bm.created_at.isoformat() if bm.created_at else None,
        })

    items = db.query(SavedItem).filter_by(user_id=current_user.id)\
        .order_by(SavedItem.created_at.desc()).all()
    
    for item in items:
        if item.item_id in seen_ids:
            continue
        title = f"Saved item #{item.item_id}"
        channel = "community"
        if item.item_type in ("discussion", "post"):
            d = db.query(CommunityDiscussion).filter_by(id=item.item_id).first()
            if d and d.title:
                clean_t = re.sub(r"['\"]+", "", d.title).strip()
                title = clean_t if clean_t else "a post"
                if d.channel:
                    channel = d.channel.name or d.channel.slug
        formatted.append({
            "id": item.id,
            "item_id": item.item_id,
            "item_type": item.item_type,
            "title": title,
            "channel": channel,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {"success": True, "data": formatted}


@router.post("/saved")
async def save_item(
    body: SaveItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_subscribed = bool(current_user and getattr(current_user, 'subscription_status', None) in ("active", "trialing"))
    if not is_subscribed:
        raise HTTPException(
            status_code=403,
            detail="Bookmarking posts is a premium feature. Upgrade to Lavoo Pro to save posts to your personal library."
        )

    existing = db.query(SavedItem).filter_by(user_id=current_user.id, item_id=body.item_id, item_type=body.item_type).first()
    if existing:
        return {"success": True, "message": "Already saved", "id": existing.id}

    saved = SavedItem(user_id=current_user.id, item_id=body.item_id, item_type=body.item_type)
    db.add(saved)
    
    bm_existing = db.query(DiscussionBookmark).filter_by(user_id=current_user.id, discussion_id=body.item_id).first()
    if not bm_existing and body.item_type in ("discussion", "post"):
        db.add(DiscussionBookmark(user_id=current_user.id, discussion_id=body.item_id))

    db.commit()
    db.refresh(saved)

    target_title = "a post"
    if body.item_type in ("discussion", "post"):
        d = db.query(CommunityDiscussion).filter_by(id=body.item_id).first()
        if d and d.title:
            target_title = d.title

    _log_activity(db, current_user.id, "saved", body.item_id, body.item_type, target_title)
    await delete_cached(f"community:discussions:user:{current_user.id}:*")
    return {"success": True, "data": {"id": saved.id, "item_id": saved.item_id, "item_type": saved.item_type}}


@router.delete("/saved/{item_id}")
async def unsave_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    saved = db.query(SavedItem).filter(
        SavedItem.user_id == current_user.id,
        or_(SavedItem.id == item_id, SavedItem.item_id == item_id)
    ).first()

    bm = db.query(DiscussionBookmark).filter(
        DiscussionBookmark.user_id == current_user.id,
        DiscussionBookmark.discussion_id == item_id
    ).first()
    if bm:
        db.delete(bm)

    if saved:
        db.delete(saved)

    db.commit()
    await delete_cached(f"community:discussions:user:{current_user.id}:*")
    return {"success": True, "message": "Item unsaved"}


@router.get("/users/{user_identifier}/profile")
async def get_user_profile(
    user_identifier: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if user_identifier.isdigit():
        user = db.query(User).filter_by(id=int(user_identifier)).first()
    else:
        user = db.query(User).filter(func.lower(User.username) == user_identifier.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id
    is_owner = (current_user.id == user.id) if current_user else False
    hide_metrics = getattr(user, 'hide_public_metrics', False) and not is_owner

    posts_count = db.query(func.count(CommunityDiscussion.id)).filter(CommunityDiscussion.user_id == user_id).scalar() or 0
    replies_count = db.query(func.count(DiscussionReply.id)).filter(DiscussionReply.user_id == user_id).scalar() or 0
    build_room_contributions = posts_count + replies_count

    pots_earned = db.query(func.count(DiscussionLike.id)).join(
        CommunityDiscussion, DiscussionLike.discussion_id == CommunityDiscussion.id
    ).filter(CommunityDiscussion.user_id == user_id).scalar() or 0

    chops_gifted_sum = db.query(func.coalesce(func.sum(CommunityDiscussion.chops_gifted), 0)).filter(
        CommunityDiscussion.user_id == user_id
    ).scalar() or 0

    # Import badge computer
    from api.routes.user.stats import _compute_badges
    badges = _compute_badges(
        analyses_count=0,
        streak=user.login_streak or 0,
        missions_done=0,
        chops=user.total_chops or 0,
        build_room_contributions=build_room_contributions,
        chops_gifted=chops_gifted_sum,
        signal_contributions=0
    )

    # Pinned posts
    pinned_posts = []
    pinned_ids = getattr(user, 'pinned_profile_post_ids', None) or []
    if pinned_ids:
        discussions = db.query(CommunityDiscussion).filter(
            CommunityDiscussion.id.in_(pinned_ids),
            CommunityDiscussion.user_id == user_id
        ).all()
        for d in discussions:
            pinned_posts.append({
                "id": d.id,
                "title": d.title,
                "content": d.content[:140] if d.content else "",
                "channel": d.channel.name if d.channel else "general",
                "like_count": d.like_count or 0,
                "reply_count": d.reply_count or 0,
                "created_at": d.created_at.isoformat() if d.created_at else None
            })

    # Enforce expertise 5-item limit
    raw_expertise = getattr(user, "expertise", None) or ["Product design", "Community", "No-code", "Brand", "Growth loops"]
    expertise_limited = raw_expertise[:5] if isinstance(raw_expertise, list) else []

    return {"success": True, "data": {
        "id": user.id,
        "name": user.name or "Member",
        "email": user.email if is_owner else None,
        "company_name": user.company_name or "Lavoo Creators",
        "industry": user.industry or "Software",
        "location": getattr(user, "location", None) or "Lagos, NG",
        "venture_stage": getattr(user, "venture_stage", None) or "Pre-revenue",
        "bio": getattr(user, "bio", None),
        "role": getattr(user, "role", None) or "normal_user",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_staff": bool(getattr(user, "is_staff", False)),
        "total_chops": user.total_chops or 0,
        "post_count": posts_count,
        "subscription_status": user.subscription_status or "Free",
        "role": getattr(user, "role", "normal_user") or "normal_user",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_staff": bool(getattr(user, "is_staff", False) or getattr(user, "is_partner", False) or getattr(user, "role", None) in ("staff", "admin")),
        "hide_public_metrics": getattr(user, "hide_public_metrics", False),
        "metrics_hidden": hide_metrics,
        "metrics": {
            "is_hidden": hide_metrics,
            "decision_score": 88 if not hide_metrics else None,
            "contribution_count": build_room_contributions if not hide_metrics else None,
            "contribution_chops": user.total_chops or 0 if not hide_metrics else None,
            "chops_earned": user.total_chops or 0 if not hide_metrics else None,
            "day_streak": user.login_streak or 0 if not hide_metrics else None,
            "pots_earned": pots_earned if not hide_metrics else None,
        },
        "badges": badges[:5],
        "all_badges": badges,
        "expertise": expertise_limited,
        "open_to": getattr(user, "open_to", None) or ["Weekly decision swaps", "Co-founder conversations", "Beta testing partnerships", "Warm intros to creators"],
        "recent_wins": getattr(user, "recent_wins", None) or ["Crossed 40 activated beta founders", "Shipped the Build Room v2 prototype", "Featured as top contributor this month"],
        "pinned_posts": pinned_posts,
        "joined_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
    }}


@router.get("/users/search")
async def search_community_users(
    q: str = Query("", min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        search_str = f"%{q.strip().lower()}%"
        users = db.query(User).filter(
            or_(
                func.lower(User.name).like(search_str),
                func.lower(User.username).like(search_str),
                func.lower(User.email).like(search_str)
            )
        ).limit(10).all()

        results = []
        for u in users:
            username_val = u.username or re.sub(r'[^a-zA-Z0-9]', '', u.name.lower() if u.name else "user")
            results.append({
                "id": u.id,
                "name": u.name or "Member",
                "username": username_val,
                "avatar_url": u.avatar_url,
                "company_name": u.company_name or "Lavoo Creators"
            })

        return {"success": True, "users": results}
    except Exception as e:
        logger.error(f"Error searching community users: {e}")
        return {"success": True, "users": []}
