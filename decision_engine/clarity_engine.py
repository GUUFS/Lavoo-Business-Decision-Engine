"""
The micromodel: decides whether to ask a founder clarifying questions
before their checkup, without calling an LLM.

HOW IT GETS SMARTER WITH EVERY CHECKUP
--------------------------------------
  1. A founder types a prompt. The micromodel looks for the most similar
     TRUSTED example it has seen before (see "trusted" below).
       - Very similar (0.85+):  it copies that example's decision.
       - Fairly similar (0.55+): it thinks for itself, but borrows the
         example's wording for its questions.
       - Nothing similar:        it thinks for itself only.
  2. The decision is saved (clarity_corpus, source 'live'), with the
     diagnosis it leads to (link_analysis).
  3. The checkup then teaches it in one of two ways:
       a) The founder ANSWERS the questions -> this checkup becomes a
          trusted example straight away.
       b) The founder SKIPS, or the micromodel was unsure -> within 3
          hours the LLM teacher (clarity_teacher.py) answers the same
          prompt, and the LLM's answer becomes a trusted example.
          It also checks 3 random checkups it WAS sure about, to catch
          confident mistakes.
  4. The next founder with a similar prompt gets the learned answer (step 1).
So every checkup either is an example or produces one.

TRUSTED = an LLM answer a person hasn't marked "wrong"
          (micromodel_person_check.py), or a checkup a founder answered.
          A founder's answer counts for more than a slightly closer LLM
          answer (USER_PREFERENCE_MARGIN). Its own unchecked guesses are
          never copied, so its mistakes don't spread.

HOW WE KNOW IT IS GETTING SMARTER: the weekly exam (micromodel_exam.py)
uses decide(), which makes the decision without saving it.
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

# Trusted rows: LLM answers a person hasn't marked 'wrong', and checkups a
# founder answered. clarity_teacher.py and training_data.py use the same rule.
_TRUSTED_FILTER = ("((source IN ('llm_seed', 'llm_teacher') AND COALESCE(person_verdict, '') <> 'wrong') "
                   "OR (source = 'live' AND outcome = 'answered'))")
# A user-answered example wins over a closer LLM example when it is at most
# this much less similar: real signals are weighted above the LLM's.
USER_PREFERENCE_MARGIN = 0.03


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


def _find_trusted_neighbors(db: Session, embedding: list[float], k: int = 5,
                            exclude_text: Optional[str] = None) -> list[dict]:
    """The k most similar trusted examples, closest first. exclude_text
    leaves out examples with exactly that prompt (the weekly exam uses it, so an
    exam question can't just copy the LLM's answer to the very same prompt)."""
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
          AND (CAST(:exclude AS TEXT) IS NULL OR lower(submission_text) <> lower(CAST(:exclude AS TEXT)))
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :k
    """)
    rows = db.execute(sql_query, {"k": k, "exclude": exclude_text}).mappings().all()
    return [dict(r) for r in rows]


def _pick_neighbor(neighbors: list[dict]) -> tuple[Optional[dict], float, str]:
    """The example to learn from: the closest one, unless a user-answered
    example is within USER_PREFERENCE_MARGIN of it (a real user's answer is
    worth more than the LLM's guess). Returns (example, similarity, note)."""
    # 1. Nothing found.
    if not neighbors:
        return None, 0.0, ""
    best = neighbors[0]
    best_sim = float(best["similarity_score"])
    # 2. Already a user example, or no close user example: keep the closest.
    if best["source"] == "live":
        return best, best_sim, ""
    for n in neighbors[1:]:
        sim = float(n["similarity_score"])
        if n["source"] == "live" and best_sim - sim <= USER_PREFERENCE_MARGIN:
            # 3. A user's answered example almost as close: prefer it.
            return n, sim, (f"A user-answered example ({sim:.2f}) is used instead of a slightly closer "
                            f"LLM example ({best_sim:.2f}): real answers count for more.")
    return best, best_sim, ""


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


def decide(submission_text: str, db: Session, user_id: Optional[int] = None,
           exclude_same_prompt: bool = False) -> dict[str, Any]:
    """The micromodel's decision for a prompt, WITHOUT saving it. Returns
    needs_clarification, questions, decision_path, confidence, similarity,
    neighbor, reasoning, history and embedding. exclude_same_prompt: don't
    copy an example with this exact prompt (for the weekly exam)."""
    # 1. Think about the prompt, using what we know about this user.
    history = user_history(db, user_id)
    reasoning = reason(submission_text, history=history)

    # 2. Find the trusted example to learn from (users' answers preferred).
    embedding = _generate_embedding(submission_text)
    neighbors = _find_trusted_neighbors(db, embedding, k=5,
                                        exclude_text=submission_text if exclude_same_prompt else None)
    neighbor, similarity, preference_note = _pick_neighbor(neighbors)
    if preference_note:
        reasoning["trace"].append(preference_note)

    # 3. Decide whether to ask, and what.
    decision_path, needs_clarification, questions = _decide(submission_text, reasoning, neighbor, similarity, embedding)
    questions = questions[:MAX_QUESTIONS]
    if not questions:
        needs_clarification = False

    # 4. How sure it is. The teacher job checks the least sure ones first.
    if decision_path == "neighbor":
        confidence = round(similarity, 3)
    else:
        confidence = round(reasoning["confidence"] * 0.7 + similarity * 0.3, 3)
    return {"needs_clarification": needs_clarification, "questions": questions, "decision_path": decision_path,
            "confidence": confidence, "similarity": similarity, "neighbor": neighbor, "reasoning": reasoning,
            "history": history, "embedding": embedding}


def get_clarifying_questions(
    submission_text: str, db: Session, user_id: Optional[int] = None
) -> dict[str, Any]:
    """Main entry point. Returns:
    needs_clarification: should we ask questions?
    questions:           the questions to show
    corpus_id:           sent back with the analysis so we can save the answers
                         (and link the diagnosis), even when nothing is asked
    reasoning:           the micromodel's notes on why it decided this"""
    # 1-3. The decision (see decide()).
    d = decide(submission_text, db, user_id=user_id)
    reasoning, neighbor, similarity, history, embedding = (d["reasoning"], d["neighbor"], d["similarity"],
                                                          d["history"], d["embedding"])
    decision_path, needs_clarification, questions, confidence = (d["decision_path"], d["needs_clarification"],
                                                                d["questions"], d["confidence"])

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
    skip. Only the user's own row can be updated, and only a row that asked
    questions (the app now sends corpus_id for every checkup, to link the
    diagnosis; a checkup with no questions has nothing to answer or skip)."""
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
            WHERE id = :id AND source = 'live' AND user_id = :uid AND needs_clarification
        """),
        {"outcome": outcome, "answers": json.dumps(pairs) if pairs else None, "id": corpus_id, "uid": user_id},
    )
    db.commit()


def link_analysis(db: Session, corpus_id: Optional[int], analysis_id: Optional[int], user_id: Optional[int]) -> None:
    """Records which diagnosis this checkup decision led to, so asking can be
    judged by the outcome (micromodel_outcomes.did_asking_help). Only the
    user's own live row; never breaks the analysis."""
    # 1. Nothing to link.
    if not corpus_id or not analysis_id or not user_id:
        return
    # 2. Link it; a failure is logged and ignored.
    try:
        db.execute(text("""
            UPDATE clarity_corpus SET analysis_id = :aid
            WHERE id = :id AND source = 'live' AND user_id = :uid
        """), {"aid": analysis_id, "id": corpus_id, "uid": user_id})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[clarity_engine] couldn't link corpus {corpus_id} to analysis {analysis_id}: {e}")
