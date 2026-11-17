"""
Did asking questions lead to better advice?

WHY: a founder answering the micromodel's questions only shows the
questions were bearable. It doesn't show that asking was the right call.

HOW IT WORKS:
  1. Every checkup is linked to the diagnosis it produced
     (clarity_engine.link_analysis fills clarity_corpus.analysis_id).
  2. Checkups are put in four groups by what happened:
       - asked, founder answered
       - asked, founder skipped
       - asked, nothing came back
       - not asked
  3. For each group: how many checkups, how many founders went on to
     complete at least one action from the diagnosis ("acted"), and the
     diagnosis's own confidence score on average.
  4. If "asked and answered" founders act more often than "not asked" ones,
     asking helps. Until each group has MIN_PER_GROUP checkups, the numbers
     are too small to compare, and the page says so.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

# Below this many checkups in a group, comparing groups is just noise.
MIN_PER_GROUP = 20

# SQL: true when the founder completed at least one action from the diagnosis
# (business_analyses.user_progress = {"completed_actions": [...], ...}).
_FOUNDER_ACTED = """
    COALESCE(jsonb_array_length(
        CASE WHEN jsonb_typeof(CAST(ba.user_progress AS jsonb) -> 'completed_actions') = 'array'
             THEN CAST(ba.user_progress AS jsonb) -> 'completed_actions' END
    ), 0) > 0
"""


def did_asking_help(db: Session, days: int = 28) -> dict:
    """The four groups for the last `days` days, as plain counts."""
    # 1. Count each group (only checkups linked to a diagnosis).
    rows = db.execute(text(f"""
        SELECT CASE WHEN NOT c.needs_clarification THEN 'not_asked'
                    WHEN c.outcome = 'answered'      THEN 'answered'
                    WHEN c.outcome = 'skipped'       THEN 'skipped'
                    ELSE 'no_reply' END                    AS grp,
               count(*)                                    AS checkups,
               count(*) FILTER (WHERE {_FOUNDER_ACTED})    AS acted,
               avg(ba.confidence_score)                    AS avg_confidence
        FROM clarity_corpus c
        JOIN business_analyses ba ON ba.id = c.analysis_id
        WHERE c.source = 'live' AND c.created_at > now() - make_interval(days => :days)
        GROUP BY 1
    """), {"days": days}).mappings().all()

    # 2. How many checkups in the period, and how many are linked at all.
    totals = db.execute(text("""
        SELECT count(*) AS checkups, count(analysis_id) AS linked
        FROM clarity_corpus WHERE source = 'live' AND created_at > now() - make_interval(days => :days)
    """), {"days": days}).mappings().one()

    # 3. Every group appears, even an empty one.
    groups = {name: {"checkups": 0, "acted": 0, "avg_confidence": None}
              for name in ("answered", "skipped", "no_reply", "not_asked")}
    for r in rows:
        groups[r["grp"]] = {"checkups": r["checkups"], "acted": r["acted"],
                            "avg_confidence": round(float(r["avg_confidence"]), 1) if r["avg_confidence"] is not None else None}

    # 4. Big enough to compare "asked and answered" with "not asked"?
    enough = groups["answered"]["checkups"] >= MIN_PER_GROUP and groups["not_asked"]["checkups"] >= MIN_PER_GROUP
    return {"days": days, "checkups": totals["checkups"], "linked": totals["linked"], "groups": groups,
            "enough_to_compare": enough, "min_per_group": MIN_PER_GROUP}
