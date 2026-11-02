"""
Extra notes sent to the LLM with the user's prompt:

  - If the user answered our questions: "treat these answers as facts".
  - If the user has done checkups before: a short summary of them (the
    problem found and how far they got with the mission), so the new
    analysis builds on it instead of starting from zero.

Only the LLM sees these notes. The saved prompt stays as the user wrote it.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from database.pg_models import BusinessAnalysis

logger = logging.getLogger(__name__)

MAX_PAST_ANALYSES = 3


def _as_obj(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value


def _history_lines(db: Session, user_id: int) -> list[str]:
    past = (
        db.query(BusinessAnalysis)
        .filter(BusinessAnalysis.user_id == user_id)
        .order_by(BusinessAnalysis.created_at.desc())
        .limit(MAX_PAST_ANALYSES)
        .all()
    )
    lines = []
    for a in past:
        # 1. The main problem that checkup found. Skip it if there is none.
        bottleneck = _as_obj(a.primary_bottleneck, {}) or {}
        title = (bottleneck.get("title") or "").strip()
        if not title:
            continue
        # 2. How far they got with that mission.
        progress = _as_obj(a.user_progress, {}) or {}
        done = len(_as_obj(progress.get("completed_actions"), []) or [])
        total = len(_as_obj(a.execution_roadmap, []) or []) or (a.estimated_days or 0)
        activated = bool((_as_obj(progress.get("mission_config"), {}) or {}).get("activated_at"))
        resolved = len(_as_obj(progress.get("resolved_constraints"), []) or [])

        # 3. Write one line, e.g. "2026-10-01: bottleneck "X"; mission stopped at 3 of 7 days."
        when = a.created_at.date().isoformat() if a.created_at else "earlier"
        if not activated:
            status = "mission never started"
        elif total and done >= total:
            status = f"mission completed ({done} of {total} days)"
        else:
            status = f"mission stopped at {done} of {total or '?'} days"
        extra = f"; {resolved} constraint(s) marked resolved" if resolved else ""
        lines.append(f"- {when}: bottleneck \"{title}\"; {status}{extra}.")
    return lines


def build_founder_context(db: Session, user_id: Optional[int], has_answers: bool) -> str:
    parts = []
    # 1. If they answered our questions, tell the LLM to treat the answers as facts.
    if has_answers:
        parts.append(
            "[How to use the Clarifying Questions & Answers]: those are the founder's own answers. "
            "Treat them as confirmed facts. Anchor the diagnosis and every recommendation on them, "
            "and never contradict them."
        )
    # 2. If they've done checkups before, add a short summary of them.
    if user_id:
        try:
            lines = _history_lines(db, user_id)
        except Exception as e:
            logger.warning(f"[founder_context] history lookup failed for user {user_id}: {e}")
            db.rollback()
            lines = []
        if lines:
            parts.append(
                "[Founder History] (earlier Lavoo checkups by this same founder, newest first. "
                "Build on what they completed; if a mission stalled, don't hand back the same plan without "
                "addressing why it stalled. Only use this where it is relevant to the new challenge, and "
                "don't refer to this section by name.)\n" + "\n".join(lines)
            )
    return "\n\n".join(parts)
