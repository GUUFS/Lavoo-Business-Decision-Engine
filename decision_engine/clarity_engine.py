"""
The micromodel: decides whether to ask the user clarifying questions,
without calling an LLM.

For each prompt it:
  1. Thinks about the prompt itself (clarity_reasoner.py).
  2. Finds the most similar "trusted" past example. Trusted means the LLM
     wrote it, or a real user answered its questions. Its own unchecked
     guesses are never copied, so mistakes don't spread.
  3. Decides using how similar that example is:
       0.85 or more:  copy the example
       0.55 to 0.85:  use its own thinking, but borrow the example's wording
       below 0.55:    use its own thinking only
     An example is only copied or borrowed from when it's the same kind of
     prompt (creator vs business, same problem type), and a borrowed
     question is only used when it fits this prompt at least as well as the
     micromodel's own question (_precedent_fits, _fits_prompt_better).
  4. Saves the decision. Later, the teacher job (clarity_teacher.py) has the
     LLM check the weakest decisions, so the micromodel keeps improving.
"""
import json
import logging
import re
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import ClarityCorpus
from decision_engine.clarity_reasoner import build_questions, classify_question, extract_facts, reason

logger = logging.getLogger(__name__)

NEAR_DUPLICATE_THRESHOLD = 0.85
BLEND_THRESHOLD = 0.55
MAX_QUESTIONS = 3
# A borrowed question must be at least this close to the prompt, compared
# with the micromodel's own question (cosine similarity of their embeddings).
RELEVANCE_MARGIN = 0.02

_TRUSTED_FILTER = "(source IN ('llm_seed', 'llm_teacher') OR (source = 'live' AND outcome = 'answered'))"


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two embeddings (1 = same meaning, 0 = unrelated)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norm if norm else 0.0


def _generate_embedding(text_in: str) -> list[float]:
    # Reuses the SAME SentenceTransformer singleton + lock already used by
    # decision_engine/recommender_db.py — loading a second copy would cost
    # ~10s of extra startup and duplicate memory for no benefit.
    from decision_engine.recommender_db import model as _st_model, _model_lock
    with _model_lock:
        return _st_model.encode(text_in).tolist()


def _find_trusted_neighbors(db: Session, embedding: list[float], k: int = 5) -> list[dict]:
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
        WHERE embedding IS NOT NULL AND {_TRUSTED_FILTER}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :k
    """)
    rows = db.execute(sql_query, {"k": k}).mappings().all()
    return [dict(r) for r in rows]


def user_history(db: Session, user_id: Optional[int]) -> dict:
    """What this user already told us in earlier checkups, so we don't
    ask them what they sell every time."""
    if not user_id:
        return {}
    try:
        # 1. Best source: their past answers to "what do you sell?".
        rows = db.execute(text("""
            SELECT answers FROM clarity_corpus
            WHERE user_id = :uid AND source = 'live' AND outcome = 'answered' AND answers IS NOT NULL
            ORDER BY created_at DESC LIMIT 10
        """), {"uid": user_id}).all()
        for (answers,) in rows:
            for a in answers or []:
                if classify_question(a.get("question", "")) == "missing_business_type" and (a.get("answer") or "").strip():
                    return {"business": a["answer"].strip()[:120]}

        # 2. Otherwise: look for a business named in their past prompts.
        goals = db.execute(text("""
            SELECT business_goal FROM business_analyses
            WHERE user_id = :uid AND business_goal IS NOT NULL
            ORDER BY created_at DESC LIMIT 5
        """), {"uid": user_id}).all()
        for (goal,) in goals:
            # Only the user's own words, not the appended Q&A block.
            own = (goal or "").split("[Clarifying Questions & Answers]")[0]
            facts = extract_facts(own)
            named = facts["sells"] or facts["industry"]
            if named:
                return {"business": named[0]}
    # 3. If anything goes wrong, carry on as if they're a new user.
    except Exception as e:
        logger.warning(f"[clarity_engine] user_history failed for user {user_id}: {e}")
        db.rollback()
    return {}


def _precedent_questions_by_gap(neighbor: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    # Group the example's questions by the gap each one asks about.
    for q in neighbor.get("questions") or []:
        wording = (q.get("question") or "").strip()
        if not wording:
            continue
        gap = q.get("gap_type") or classify_question(wording)
        out.setdefault(gap, wording)
    return out


def _precedent_fits(facts: dict, neighbor: dict) -> tuple[bool, str]:
    """Is the stored example the same kind of prompt as this one? Same
    domain (creator or business) and same main problem type. Two prompts
    can read alike to the embedding model while needing different
    questions, e.g. a creator wanting positive impact and a shop owner
    wanting more sales. Returns (fits, reason)."""
    other = extract_facts(neighbor.get("submission_text") or "")
    if facts.get("domain") != other.get("domain"):
        return False, f"it's about a {other.get('domain')}, this prompt is about a {facts.get('domain')}"
    mine = (facts.get("problem_types") or ["general"])[0]
    theirs = (other.get("problem_types") or ["general"])[0]
    if mine != theirs:
        return False, f"it's a '{theirs}' problem, this prompt is a '{mine}' one"
    return True, ""


def _fits_prompt_better(prompt_embedding: list[float], own: str, borrowed: str) -> bool:
    """Use the example's wording only if it's at least as relevant to the
    user's prompt as the micromodel's own question."""
    own_score = _cosine(prompt_embedding, _generate_embedding(own))
    borrowed_score = _cosine(prompt_embedding, _generate_embedding(borrowed))
    return borrowed_score >= own_score - RELEVANCE_MARGIN


def _decide(
    submission_text: str, reasoning: dict, neighbor: Optional[dict], similarity: float,
    prompt_embedding: Optional[list[float]] = None,
) -> tuple[str, bool, list[dict]]:
    """Returns (decision_path, needs_clarification, questions).
    prompt_embedding: the prompt's embedding if already computed (saves
    work); otherwise it's computed when needed."""
    trace = reasoning["trace"]

    # 0. Only learn from an example that's the same kind of prompt.
    if neighbor and similarity >= BLEND_THRESHOLD:
        fits, why_not = _precedent_fits(reasoning["facts"], neighbor)
        if not fits:
            trace.append(
                f"The closest trusted precedent ({similarity:.2f}) isn't the same kind of prompt ({why_not}), so it isn't used."
            )
            neighbor = None

    # 1. Very similar trusted example (0.85+): copy its decision and questions.
    if neighbor and similarity >= NEAR_DUPLICATE_THRESHOLD:
        trace.append(
            f"A trusted precedent is a near match ({similarity:.2f}): \"{neighbor['submission_text'][:80]}\". Following its call."
        )
        if not neighbor["needs_clarification"]:
            return "neighbor", False, []
        questions = [
            {"id": f"q{i+1}", "question": q["question"], "gap_type": q.get("gap_type") or classify_question(q["question"])}
            for i, q in enumerate((neighbor.get("questions") or [])[:MAX_QUESTIONS])
            if q.get("question")
        ]
        if questions:
            return "neighbor", True, questions
        # Precedent says ask but stored no wording: fall through to the reasoner.

    # 2. Otherwise the micromodel's own thinking decides what to ask.
    questions = build_questions(reasoning)

    # 3. Fairly similar example (0.55 to 0.85): keep our questions, but use the
    #    example's wording where it asks about the same thing AND fits this
    #    prompt at least as well as our own wording.
    if neighbor and similarity >= BLEND_THRESHOLD and questions:
        borrowed = _precedent_questions_by_gap(neighbor)
        if prompt_embedding is None:
            prompt_embedding = _generate_embedding(submission_text)
        used = 0
        for q in questions:
            wording = borrowed.get(q["gap_type"])
            if wording and _fits_prompt_better(prompt_embedding, q["question"], wording):
                q["question"] = wording
                used += 1
        trace.append(
            f"Closest trusted precedent ({similarity:.2f}) supplied wording for {used} of {len(questions)} question(s)."
        )
        return "blend", True, questions

    # 4. No useful example: our own thinking only. (A neighbor dropped in
    #    step 0 has already explained itself in the trace.)
    if neighbor and similarity >= BLEND_THRESHOLD:
        trace.append(f"Nothing is missing, so the closest precedent ({similarity:.2f}) isn't needed.")
    elif neighbor:
        trace.append(f"Closest trusted precedent is too far ({similarity:.2f}) to borrow from.")
    return "reasoner", bool(questions), questions


def _log_live_decision(
    db: Session,
    submission_text: str,
    embedding: list[float],
    needs_clarification: bool,
    gap_types: list[str],
    questions: list[dict],
    confidence: Optional[float],
    user_id: Optional[int],
    reasoning: dict,
    decision_path: str,
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
        reasoning=reasoning,
        decision_path=decision_path,
    )
    db.add(row)
    db.flush()
    # embedding has no ORM type (see ClarityCorpus.embedding's comment) —
    # set it via raw SQL against the row just flushed.
    db.execute(
        text("UPDATE clarity_corpus SET embedding = CAST(:emb AS vector) WHERE id = :id"),
        {"emb": embedding_str, "id": row.id},
    )
    db.commit()
    return row.id


def get_clarifying_questions(
    submission_text: str, db: Session, user_id: Optional[int] = None
) -> dict[str, Any]:
    """Main entry point. Returns:
    needs_clarification: should we ask questions?
    questions:           the questions to show
    corpus_id:           sent back with the analysis so we can save the answers
    reasoning:           the micromodel's notes on why it decided this"""
    # 1. Think about the prompt, using what we know about this user.
    history = user_history(db, user_id)
    reasoning = reason(submission_text, history=history)

    # 2. Find the most similar trusted example.
    embedding = _generate_embedding(submission_text)
    neighbors = _find_trusted_neighbors(db, embedding, k=5)
    neighbor = neighbors[0] if neighbors else None
    similarity = float(neighbor["similarity_score"]) if neighbor else 0.0

    # 3. Decide whether to ask, and what.
    decision_path, needs_clarification, questions = _decide(submission_text, reasoning, neighbor, similarity, embedding)
    questions = questions[:MAX_QUESTIONS]
    if not questions:
        needs_clarification = False

    # How sure we are about this decision. The teacher job checks the
    # least sure ones first.
    if decision_path == "neighbor":
        confidence = round(similarity, 3)
    else:
        confidence = round(reasoning["confidence"] * 0.7 + similarity * 0.3, 3)

    # 4. Save the decision and why it was made, so we can learn from it later.
    stored_reasoning = {
        "facts": reasoning["facts"],
        "trace": reasoning["trace"],
        "reasoner_confidence": reasoning["confidence"],
        "precedent_id": neighbor["id"] if neighbor else None,
        "precedent_similarity": round(similarity, 3),
        "history_used": bool(history),
    }
    gap_types = [q["gap_type"] for q in questions] if needs_clarification else [g["type"] for g in reasoning["gaps"]]

    corpus_id = _log_live_decision(
        db, submission_text, embedding, needs_clarification, gap_types,
        questions, confidence, user_id, stored_reasoning, decision_path,
    )

    logger.info(
        f"[clarity_engine] submission={submission_text[:60]!r} path={decision_path} "
        f"gaps={gap_types} similarity={similarity:.3f} confidence={confidence} "
        f"needs_clarification={needs_clarification} corpus_id={corpus_id}"
    )

    # 5. Send the questions to the frontend (it only needs id and question).
    public_questions = [{"id": q["id"], "question": q["question"]} for q in questions]
    return {
        "needs_clarification": needs_clarification,
        "questions": public_questions,
        "corpus_id": corpus_id,
        "reasoning": reasoning["trace"],
    }


def update_outcome(db: Session, corpus_id: int, clarifications, user_id: Optional[int]) -> None:
    """Saves the user's answers. If every answer is empty, it counts as a
    skip. Only the user's own row can be updated."""
    if not corpus_id or not user_id:
        return
    # 1. Collect each question and its answer, tidied up.
    pairs = []
    for c in clarifications or []:
        if isinstance(c, dict):
            q, a = (c.get("question") or "").strip(), (c.get("answer") or "").strip()
        else:
            q, a = (getattr(c, "question", "") or "").strip(), (getattr(c, "answer", "") or "").strip()
        if q:
            pairs.append({"question": q, "answer": re.sub(r"\s+", " ", a)[:1000]})
    # 2. Answered if at least one box has text, otherwise skipped.
    outcome = "answered" if any(p["answer"] for p in pairs) else "skipped"

    # 3. Save it, but only on this user's own row.
    db.execute(
        text("""
            UPDATE clarity_corpus SET outcome = :outcome, answers = CAST(:answers AS JSON)
            WHERE id = :id AND source = 'live' AND user_id = :uid
        """),
        {"outcome": outcome, "answers": json.dumps(pairs) if pairs else None, "id": corpus_id, "uid": user_id},
    )
    db.commit()
