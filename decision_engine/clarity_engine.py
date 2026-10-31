"""
Zero-LLM clarifying-questions engine. Replaces a live LLM call
(agentic_analyzer.generate_clarifying_questions) with: embed the
submission, look up its nearest neighbors in clarity_corpus by cosine
similarity (pgvector), and decide + word questions from precedent —
falling back to the heuristic gap-detection + template bank
(clarity_heuristics.py / clarity_templates.py) when no neighbor is close
enough. The LLM's judgment lives in the corpus (source='llm_seed' /
'llm_teacher' rows, written offline — see scripts/seed_clarity_corpus.py
and the periodic teacher job), never on this request path.

Every live decision is logged back into the corpus (source='live') so the
corpus keeps growing with real traffic, and so the periodic teacher job can
find the low-confidence cases most worth having the LLM weigh in on.
"""
import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import ClarityCorpus
from decision_engine.clarity_heuristics import detect_gap_types
from decision_engine.clarity_templates import pick_variant

logger = logging.getLogger(__name__)

# A neighbor below this similarity isn't a real match — the engine falls
# back to pure heuristics/templates rather than borrowing a precedent for
# an unrelated submission. 0.55 is a starting point (cosine similarity on
# MiniLM sentence embeddings for genuinely related short business
# sentences typically lands 0.5-0.8+); the periodic teacher job targets
# exactly the submissions that fall below this, so the threshold's
# practical effect should shrink over time as the corpus fills in.
NEIGHBOR_CONFIDENCE_THRESHOLD = 0.55
MAX_QUESTIONS = 3


def _generate_embedding(text_in: str) -> list[float]:
    # Reuses the SAME SentenceTransformer singleton + lock already used by
    # decision_engine/recommender_db.py — loading a second copy would cost
    # ~10s of extra startup and duplicate memory for no benefit.
    from decision_engine.recommender_db import model as _st_model, _model_lock
    with _model_lock:
        return _st_model.encode(text_in).tolist()


def _find_nearest_neighbors(db: Session, embedding: list[float], k: int = 5) -> list[dict]:
    # Same safe string-formatting pattern as vector_recommender.py: the
    # embedding is always a list of floats from model.encode(), never raw
    # user text, so direct interpolation (required — pgvector's type can't
    # go through normal parameter binding) carries no injection risk.
    embedding_str = f"[{','.join(map(str, embedding))}]"
    sql_query = text(f"""
        SELECT
            id, submission_text, needs_clarification, gap_types, questions,
            source, outcome,
            1 - (embedding <=> '{embedding_str}'::vector) AS similarity_score
        FROM clarity_corpus
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :k
    """)
    rows = db.execute(sql_query, {"k": k}).mappings().all()
    return [dict(r) for r in rows]


def _log_live_decision(
    db: Session,
    submission_text: str,
    embedding: list[float],
    needs_clarification: bool,
    gap_types: list[str],
    questions: list[dict],
    confidence: Optional[float],
    user_id: Optional[int],
) -> int:
    embedding_str = f"[{','.join(map(str, embedding))}]"
    row = ClarityCorpus(
        submission_text=submission_text,
        needs_clarification=needs_clarification,
        gap_types=gap_types,
        questions=questions,
        source="live",
        confidence=confidence,
        user_id=user_id,
    )
    db.add(row)
    db.flush()
    # embedding has no ORM type (see ClarityCorpus.embedding's comment) —
    # set it via raw SQL against the row just flushed, same as the
    # string-vector pattern used for reads above.
    db.execute(
        text("UPDATE clarity_corpus SET embedding = CAST(:emb AS vector) WHERE id = :id"),
        {"emb": embedding_str, "id": row.id},
    )
    db.commit()
    return row.id


def get_clarifying_questions(
    submission_text: str, db: Session, user_id: Optional[int] = None
) -> dict[str, Any]:
    """Main entry point — same return shape as
    agentic_analyzer.generate_clarifying_questions:
    {"needs_clarification": bool, "questions": [{"id", "question"}]},
    plus "corpus_id" so the caller can round-trip it to /analyze and let
    the outcome (answered/skipped) be logged back against this exact
    decision."""
    embedding = _generate_embedding(submission_text)
    neighbors = _find_nearest_neighbors(db, embedding, k=5)
    top_similarity = neighbors[0]["similarity_score"] if neighbors else 0.0

    gap_types = detect_gap_types(submission_text)

    best_neighbor = neighbors[0] if neighbors and top_similarity >= NEIGHBOR_CONFIDENCE_THRESHOLD else None

    if best_neighbor is not None:
        # A close/confident neighbor's OWN judgment takes priority over the
        # live heuristic — it's either real user outcome data or an
        # LLM-authored precedent, both more reliable than a few regex/
        # keyword checks run on this text alone. This matters concretely:
        # the heuristic can false-negative (e.g. treating "3 months" as a
        # satisfying "number" when it's just a duration, not a business
        # metric) and without this priority a neighbor that correctly knew
        # better would get silently overridden by that false negative.
        needs_clarification = bool(best_neighbor["needs_clarification"])
        if needs_clarification:
            neighbor_questions = list(best_neighbor["questions"] or [])
            if neighbor_questions:
                # Reuse the neighbor's own real questions directly — this
                # is the non-generic path, borrowing actual LLM/real-user
                # precedent wording rather than a template.
                questions = [
                    {"id": q.get("id") or f"q{i+1}", "question": q.get("question"), "gap_type": q.get("gap_type")}
                    for i, q in enumerate(neighbor_questions[:MAX_QUESTIONS])
                    if q.get("question")
                ]
            elif gap_types:
                # Neighbor says yes but stored no questions (shouldn't
                # normally happen) — fall back to this submission's own
                # gap_types + templates rather than ask nothing.
                questions = [
                    {"id": f"q{i+1}", "question": pick_variant(g, submission_text), "gap_type": g}
                    for i, g in enumerate(gap_types[:MAX_QUESTIONS])
                    if pick_variant(g, submission_text)
                ]
            else:
                questions = []
        else:
            questions = []
    elif gap_types:
        # No confident neighbor — fall back to pure heuristics + templates.
        needs_clarification = True
        questions = [
            {"id": f"q{i+1}", "question": pick_variant(g, submission_text), "gap_type": g}
            for i, g in enumerate(gap_types[:MAX_QUESTIONS])
            if pick_variant(g, submission_text)
        ]
    else:
        needs_clarification = False
        questions = []

    if not questions:
        needs_clarification = False

    corpus_id = _log_live_decision(
        db, submission_text, embedding, needs_clarification, gap_types,
        questions, top_similarity, user_id,
    )

    logger.info(
        f"[clarity_engine] submission={submission_text[:60]!r} "
        f"gap_types={gap_types} top_similarity={top_similarity:.3f} "
        f"needs_clarification={needs_clarification} corpus_id={corpus_id}"
    )

    # Strip internal gap_type field before returning — frontend contract
    # only expects {id, question}.
    public_questions = [{"id": q["id"], "question": q["question"]} for q in questions]
    return {
        "needs_clarification": needs_clarification,
        "questions": public_questions,
        "corpus_id": corpus_id,
    }


def update_outcome(db: Session, corpus_id: int, outcome: str) -> None:
    """outcome: 'answered' or 'skipped'. Called from /analyze(/stream) once
    we know which happened — see api/routes/decision_engine/analyzer.py."""
    if not corpus_id:
        return
    db.execute(
        text("UPDATE clarity_corpus SET outcome = :outcome WHERE id = :id AND source = 'live'"),
        {"outcome": outcome, "id": corpus_id},
    )
    db.commit()
