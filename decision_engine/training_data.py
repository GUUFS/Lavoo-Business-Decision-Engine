"""
Training data for a Lavoo model of our own.

The micromodel learns today by memory: trusted examples it copies or
borrows from (clarity_engine). To go further, toward a business model that
answers without calling the outside LLM, we fine-tune an open model on
what the outside LLM and our users have already taught us (distillation).
This module turns that knowledge into fine-tuning files, in the chat JSONL
format most fine-tuning tools accept (one {"messages": [...]} per line):

  questions: a checkup prompt -> the clarifying questions to ask (or none).
             From trusted examples: the LLM's own answers (llm_seed,
             llm_teacher) and live decisions users answered that the LLM
             teacher didn't overrule.
  checkups:  a checkup prompt -> the full checkup the LLM wrote
             (bottleneck, constraints, what to stop, plans, roadmap).

training_summary tells the admin how many examples each has and how far
each is from a size worth fine-tuning on.
"""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

# The instruction each example starts with (the fine-tuned model is given
# the same one when it is used).
QUESTIONS_SYSTEM = (
    "You are Lavoo's checkup assistant. Read a founder's business prompt and decide whether it is clear "
    "enough to analyse. If not, ask the few short questions that would make it clear. Reply with JSON: "
    '{"needs_clarification": true|false, "questions": ["..."]}.'
)
CHECKUPS_SYSTEM = (
    "You are Lavoo, a business decision engine. Read a founder's business prompt and reply with JSON: the "
    "primary bottleneck, the secondary constraints, what to stop doing, the strategic priority, the action "
    "plans and the execution roadmap."
)

# Rough sizes worth fine-tuning on (rules of thumb for a LoRA fine-tune of
# a 7-8B open model; more, and more varied, is better).
TARGETS = {"questions": 1000, "checkups": 2000}

# Trusted question examples the LLM teacher didn't overrule, newest first,
# one per distinct prompt.
_QUESTIONS_SQL = """
    SELECT DISTINCT ON (lower(trim(submission_text)))
           submission_text, needs_clarification, questions
    FROM clarity_corpus
    WHERE (source IN ('llm_seed', 'llm_teacher')
           OR (source = 'live' AND outcome = 'answered' AND teacher_agreed IS NOT FALSE))
      AND length(trim(submission_text)) > 0
    ORDER BY lower(trim(submission_text)),
             (source IN ('llm_seed', 'llm_teacher')) DESC, created_at DESC
"""

# Finished checkups with a bottleneck and plans.
_CHECKUPS_SQL = """
    SELECT business_goal, primary_bottleneck, secondary_constraints, what_to_stop,
           strategic_priority, action_plans, execution_roadmap
    FROM business_analyses
    WHERE primary_bottleneck IS NOT NULL AND action_plans IS NOT NULL
      AND length(trim(business_goal)) > 0
    ORDER BY id DESC
"""


def _question_texts(questions) -> list[str]:
    """Just the question wording, from either stored shape."""
    out = []
    for q in questions or []:
        text_ = q.get("question") if isinstance(q, dict) else q
        if isinstance(text_, str) and text_.strip():
            out.append(text_.strip())
    return out


def _example(system: str, prompt: str, answer: dict) -> str:
    """One JSONL line: system, user prompt, assistant JSON answer."""
    return json.dumps({"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt.strip()},
        {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
    ]}, ensure_ascii=False)


def question_examples(db: Session) -> list[str]:
    """The questions dataset, one JSONL line per prompt."""
    lines = []
    for row in db.execute(text(_QUESTIONS_SQL)).mappings():
        # 1. The answer the model should learn to give.
        questions = _question_texts(row["questions"]) if row["needs_clarification"] else []
        answer = {"needs_clarification": bool(row["needs_clarification"]) and bool(questions), "questions": questions}
        # 2. As one chat example.
        lines.append(_example(QUESTIONS_SYSTEM, row["submission_text"], answer))
    return lines


def checkup_examples(db: Session) -> list[str]:
    """The checkups dataset, one JSONL line per finished checkup."""
    lines = []
    for row in db.execute(text(_CHECKUPS_SQL)).mappings():
        # 1. The parts of the checkup the model should learn to write.
        answer = {
            "primary_bottleneck": row["primary_bottleneck"],
            "secondary_constraints": row["secondary_constraints"],
            "what_to_stop": row["what_to_stop"],
            "strategic_priority": row["strategic_priority"],
            "action_plans": row["action_plans"],
            "execution_roadmap": row["execution_roadmap"],
        }
        # 2. As one chat example.
        lines.append(_example(CHECKUPS_SYSTEM, row["business_goal"], answer))
    return lines


def export_jsonl(db: Session, dataset: str) -> tuple[str, int]:
    """(file text, example count) for "questions" or "checkups"."""
    # 1. Pick the dataset.
    if dataset == "checkups":
        lines = checkup_examples(db)
    elif dataset == "questions":
        lines = question_examples(db)
    else:
        raise ValueError(f"Unknown dataset {dataset!r}: use 'questions' or 'checkups'")
    # 2. One example per line.
    return "\n".join(lines) + ("\n" if lines else ""), len(lines)


def training_summary(db: Session) -> dict:
    """Example counts per dataset and progress toward a size worth
    fine-tuning on."""
    # 1. Count each dataset with the same queries the export uses.
    counts = {
        "questions": db.execute(text(f"SELECT count(*) FROM ({_QUESTIONS_SQL}) q")).scalar() or 0,
        "checkups": db.execute(text(f"SELECT count(*) FROM ({_CHECKUPS_SQL}) c")).scalar() or 0,
    }
    # 2. Progress toward each target.
    return {name: {
        "examples": counts[name],
        "target": TARGETS[name],
        "ready": counts[name] >= TARGETS[name],
        "progress_pct": min(100, round(100 * counts[name] / TARGETS[name])),
    } for name in counts}
