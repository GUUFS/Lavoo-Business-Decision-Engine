"""
Zero-LLM question wording for the clarity engine. Keyed by gap-type (see
clarity_heuristics.detect_gap_types), each with multiple phrasing variants
so the same gap doesn't always produce the identical sentence. A variant is
picked deterministically from a hash of the submission text, so the SAME
submission always gets the SAME wording (reproducible), but different
submissions spread across the variants rather than converging on one.

This is deliberately a fallback layer, not the primary source of wording —
clarity_engine.py prefers reusing a real question from a close corpus
neighbor (llm_seed/llm_teacher/answered-live rows) when one exists, and
only falls back to these templates when no neighbor is close enough. That's
what keeps questions from reading as generic once the corpus has real
precedent to draw from.
"""
import hashlib

TEMPLATES: dict[str, list[str]] = {
    "missing_business_type": [
        "What does your business sell or do, and through what channel (in-person, online store, marketplace)?",
        "What product or service are you offering, and how do customers currently reach you?",
    ],
    "missing_numbers_or_constraint": [
        "What's one concrete number here (revenue, conversion rate, customer count, etc.), or something you've already tried?",
        "Do you have a current number to anchor this (monthly revenue, traffic, price point), or has anything already been attempted?",
    ],
    "unnamed_options": [
        "What are the specific options you're choosing between?",
        "Which ideas or options are actually on the table right now?",
    ],
}


def pick_variant(gap_type: str, submission_text: str) -> str:
    variants = TEMPLATES.get(gap_type)
    if not variants:
        return ""
    idx = int(hashlib.sha256(submission_text.encode("utf-8")).hexdigest(), 16) % len(variants)
    return variants[idx]
