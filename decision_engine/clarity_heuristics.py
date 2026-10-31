"""
Cheap, zero-LLM signal extraction for the clarity engine (see
clarity_engine.py). These are the SAME criteria the clarifying-questions
LLM prompt was calibrated around (agentic_analyzer.py's
generate_clarifying_questions) — "does it say what the business sells/does",
"is there a concrete number/constraint/already-tried action", "is this a
decision between unnamed options" — just encoded as plain Python instead of
asked of a model. Each detector returns True when the SIGNAL IS PRESENT
(not when a gap exists) — the engine inverts these to decide what's missing.
"""
import re

# A digit NOT directly touching a letter on either side — avoids false
# positives like "D2C" or "B2B" (business-model shorthand, not a metric)
# counting as "the prompt gives a concrete number". Confirmed live: without
# the lookarounds, "I run a D2C skincare brand" was judged as already
# having a number and skipped asking for one.
_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d(?![A-Za-z])|%|\$|£|₦|naira|dollar|pound")

_BUSINESS_TYPE_WORDS = {
    "store", "shop", "business", "company", "startup", "app", "website",
    "service", "agency", "restaurant", "cafe", "bakery", "brand", "product",
    "shopify", "ecommerce", "e-commerce", "saas", "clinic", "salon",
    "studio", "firm", "practice", "marketplace", "platform",
}

_CHANNEL_WORDS = {
    "online", "in-person", "in person", "physical", "marketplace",
    "instagram", "facebook", "tiktok", "whatsapp", "website", "store front",
    "storefront", "b2b", "b2c", "wholesale", "retail",
}

_DECISION_WORDS = {
    "which", "whether", "should i", "or not", "or should",
    "choose", "choosing", "decide", "deciding", "prioritize",
    "prioritise", "pick between", "focus on first",
}

_ALREADY_TRIED_WORDS = {
    "already tried", "i've tried", "ive tried", "tried ", "attempted",
    "we tried", "still not", "still no", "even after",
}


def has_numbers(text: str) -> bool:
    return bool(_NUMBER_RE.search(text))


def names_business_type(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _BUSINESS_TYPE_WORDS)


def names_channel(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _CHANNEL_WORDS)


def is_decision_type(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _DECISION_WORDS)


def has_already_tried_signal(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _ALREADY_TRIED_WORDS)


def detect_gap_types(text: str) -> list[str]:
    """Returns which load-bearing gaps are MISSING from this text — the
    inverse of the detector functions above. Mirrors the LLM calibration's
    default rule: ask unless the query states both what the business
    sells/does and a concrete number/constraint/already-tried action,
    UNLESS it's a decision-between-options prompt, which is its own gap
    type regardless of the other two (you can't rank options you weren't
    told)."""
    gaps = []

    if is_decision_type(text) and not _names_specific_options(text):
        gaps.append("unnamed_options")

    if not (names_business_type(text) or names_channel(text)):
        gaps.append("missing_business_type")

    if not (has_numbers(text) or has_already_tried_signal(text)):
        gaps.append("missing_numbers_or_constraint")

    return gaps


def _names_specific_options(text: str) -> bool:
    """A decision-type prompt that already lists its own options (commas,
    'vs', numbered items) doesn't need the generic 'what are the options'
    question — only the genuinely unnamed case does."""
    lower = text.lower()
    return bool(re.search(r"\bvs\.?\b|\d\.\s|,\s*\w+.*,\s*\w+", lower))
