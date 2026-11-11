"""
Removes dashes from the AI's text and puts in normal punctuation.
"2–4 weeks" becomes "2 to 4 weeks", and "Fix this — now" becomes
"Fix this, now". Normal hyphens like "follow-up" are kept.
"""
import re
from typing import Any

# "2–4 weeks", "$500 - $2,000" -> "2 to 4 weeks", "$500 to $2,000"
_RANGE_RE = re.compile(r"(\d[\d,.%kKmM]*)\s*(?:[—–]|\s-\s)\s*([$£₦]?\d)")
# A dash at the very start of a value, e.g. "- Do this" or "— Do this"
_LEADING_RE = re.compile(r"^\s*[—–-]+\s+")
# A clause-joining dash: any em/en dash, or a hyphen with spaces both sides
_CLAUSE_RE = re.compile(r"\s*[—–]\s*|\s+-\s+")


def strip_dashes(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    # 1. Nothing to do if there are no dashes.
    if "—" not in text and "–" not in text and " - " not in text and not text.lstrip().startswith("-"):
        return text
    # 2. Number ranges: "2–4" becomes "2 to 4".
    text = _RANGE_RE.sub(r"\1 to \2", text)
    # 3. A dash at the start, like a bullet point: remove it.
    text = _LEADING_RE.sub("", text)
    # 4. A dash between two parts of a sentence becomes a comma.
    text = _CLAUSE_RE.sub(", ", text)
    # 5. Tidy up leftover double commas, ", ." and extra spaces.
    text = re.sub(r",\s*([,.;:!?])", r"\1", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def strip_dashes_deep(value: Any) -> Any:
    """Applies strip_dashes to every string inside a parsed JSON value.
    Dict keys are left untouched."""
    if isinstance(value, str):
        return strip_dashes(value)
    if isinstance(value, list):
        return [strip_dashes_deep(v) for v in value]
    if isinstance(value, dict):
        return {k: strip_dashes_deep(v) for k, v in value.items()}
    return value


# A step label at the start of a tool's text: "Step 3: ", "Steps 2 and 4 - ".
_STEP_LABEL_RE = re.compile(r"^\s*steps?\s*\d+(?:\s*(?:,|&|and|-|–|—|to)\s*\d+)*\s*[:.\-–—)]\s*", re.I)


def strip_step_label(text: str) -> str:
    """Removes a leading "Step 3:" label from a tool's text. The text is
    shown under its own step already, and inside a workflow the steps have
    their own numbers, so the label reads as a wrong number."""
    if not text or not isinstance(text, str):
        return text
    # 1. Drop the label.
    cleaned = _STEP_LABEL_RE.sub("", text).strip()
    # 2. Start with a capital letter again ("its ..." -> "Its ...").
    return cleaned[:1].upper() + cleaned[1:]
