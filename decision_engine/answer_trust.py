"""
Should a founder's answers teach the micromodel?

WHY: when a founder answers the micromodel's questions, that checkup becomes
a trusted example straight away, and other founders with a similar prompt
get its decision copied (clarity_engine.py). Before this file, nothing looked
at WHAT they answered. One account could submit prompts built to get a bad
decision, type junk into the boxes, and plant trusted examples that spread to
everyone else (memory poisoning of a self-learning model).

HOW IT WORKS (clarity_engine.update_outcome calls answers_trust_problem):
  1. Answers that look fake are not trusted: no words at all, keyboard mash,
     one key held down, placeholders like "test", the question copied back,
     the same long answer in every box, or instructions aimed at the AI
     ("ignore previous instructions").
  2. One account can only teach so much: after MAX_TRUSTED_ANSWERS_PER_DAY
     trusted answers in 24 hours, its next answers are not trusted.
  3. An untrusted answer is still saved and still counts as "answered" in
     the numbers, it just isn't copied for other founders. The LLM teacher
     re-checks it like a skipped checkup, so the prompt still gets a trusted
     answer, written by the LLM instead.
  Junk answers are also left out of the founder's own history; answers over
  the daily limit are kept there (they are probably real, just too many).
"""
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

# How many answered checkups one account can turn into trusted examples in 24 hours.
MAX_TRUSTED_ANSWERS_PER_DAY = 3

# Flag saved on an answer that went over the daily limit.
OVER_DAILY_LIMIT = "over_daily_limit"
# Flags for answers that look fake start with this ("junk: keyboard mash").
JUNK_PREFIX = "junk"

# Words people type to fill a box without answering.
_PLACEHOLDERS = {"test", "testing", "asdf", "blah", "blah blah", "xxx", "abc", "123", "lorem ipsum", "idk idk"}
# Letter runs from rolling a hand across the keyboard.
_MASH_RUNS = ("asdf", "sdfg", "qwer", "wert", "zxcv", "hjkl", "jkjk", "fdsa")
# Phrases aimed at the AI rather than answering the question.
_INSTRUCTIONS_RE = re.compile(
    r"ignore (all |the |any )?(previous|above|prior|earlier|your)? ?(instructions|rules|prompt)"
    r"|disregard (all |the |any )?(previous|above|prior|your)"
    r"|system prompt|you are now|developer mode|jailbreak"
    r"|<\s*/?\s*(script|system|instructions?)\b",
    re.IGNORECASE,
)
# One character typed five or more times in a row ("aaaaa", "!!!!!").
_HELD_KEY_RE = re.compile(r"(.)\1{4,}")
# A word of six or more letters with no vowel in it ("sdfghj").
_NO_VOWEL_WORD_RE = re.compile(r"\b[b-df-hj-np-tv-xz]{6,}\b", re.IGNORECASE)
# The same answer in every box only counts as fake when it is at least this long
# ("no" to three yes/no questions is a real answer).
_SAME_ANSWER_MIN_LENGTH = 15


def _plain(words: str) -> str:
    """Lower case, punctuation removed, single spaces, for comparing two texts."""
    # 1. Keep letters, digits and spaces only.
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", (words or "").lower())
    # 2. Squash the spaces.
    return " ".join(cleaned.split())


def why_one_answer_looks_fake(question: str, answer: str) -> str | None:
    """The reason one answer looks fake, or None when it looks like a real answer."""
    # 1. Nothing typed is a skip, not a fake answer.
    answer = (answer or "").strip()
    if not answer:
        return None
    lower = answer.lower()
    plain = _plain(answer)
    # 2. Instructions aimed at the AI.
    if _INSTRUCTIONS_RE.search(answer):
        return "instructions to the AI"
    # 3. No letters or numbers at all ("...", "???").
    if not plain:
        return "no words"
    # 4. One key held down.
    if _HELD_KEY_RE.search(lower):
        return "one key held down"
    # 5. Keyboard mash.
    if _NO_VOWEL_WORD_RE.search(answer) or any(run in lower.replace(" ", "") for run in _MASH_RUNS):
        return "keyboard mash"
    # 6. A placeholder instead of an answer.
    if plain in _PLACEHOLDERS or plain.startswith("lorem ipsum"):
        return "placeholder"
    # 7. The question typed back as the answer.
    if plain == _plain(question):
        return "copied the question"
    # 8. Looks real.
    return None


def why_answers_look_fake(pairs: list[dict]) -> str | None:
    """The reason a checkup's answers look fake, or None when they look real.
    pairs is [{"question", "answer"}], as update_outcome builds it."""
    # 1. Any one fake answer makes the whole checkup untrusted.
    answered = [p for p in pairs or [] if (p.get("answer") or "").strip()]
    for p in answered:
        reason = why_one_answer_looks_fake(p.get("question", ""), p.get("answer", ""))
        if reason:
            return reason
    # 2. The same long answer pasted into every box.
    if len(answered) >= 2:
        all_answers = {_plain(p["answer"]) for p in answered}
        if len(all_answers) == 1 and len(next(iter(all_answers))) >= _SAME_ANSWER_MIN_LENGTH:
            return "same answer to every question"
    # 3. Looks real.
    return None


def trusted_answers_today(db: Session, user_id: int, leave_out_id: int | None = None) -> int:
    """How many of this account's answered checkups became trusted examples in the last 24 hours."""
    # 1. Count this user's trusted answers from the last day (not counting the checkup being saved).
    return db.execute(text("""
        SELECT count(*) FROM clarity_corpus
        WHERE user_id = :uid AND source = 'live' AND outcome = 'answered'
          AND answer_trusted IS NOT FALSE
          AND created_at > now() - interval '24 hours'
          AND (CAST(:leave_out AS INTEGER) IS NULL OR id <> CAST(:leave_out AS INTEGER))
    """), {"uid": user_id, "leave_out": leave_out_id}).scalar() or 0


def answers_trust_problem(db: Session, user_id: int, corpus_id: int | None, pairs: list[dict]) -> str | None:
    """Why these answers should NOT teach the micromodel ("junk: <reason>" or
    OVER_DAILY_LIMIT), or None when they can become a trusted example."""
    # 1. Answers that look fake.
    reason = why_answers_look_fake(pairs)
    if reason:
        return f"{JUNK_PREFIX}: {reason}"
    # 2. This account has already taught the micromodel enough today.
    if trusted_answers_today(db, user_id, leave_out_id=corpus_id) >= MAX_TRUSTED_ANSWERS_PER_DAY:
        return OVER_DAILY_LIMIT
    # 3. Trusted.
    return None
