"""
Bootstrap (and re-runnable enrichment) script for clarity_corpus — see
decision_engine/clarity_engine.py's module docstring for the overall
design. Calls the already-calibrated clarifying-questions LLM prompt
(decision_engine.agentic_analyzer.generate_clarifying_questions) OFFLINE,
once per prompt here, to generate high-quality (submission, gap-types,
questions) examples. These become the corpus's starting precedent so the
LIVE zero-LLM engine (clarity_engine.get_clarifying_questions) has real
judgments to match new submissions against from day one, instead of
starting with an empty table and only heuristics/templates to fall back on.

Run manually: PYTHONPATH=. ./venv/bin/python decision_engine/seed_clarity_corpus.py
Idempotent-ish: skips a prompt if its exact text is already in the corpus
(doesn't re-call the LLM for something already seeded), so it's safe to
re-run after adding new prompts to SEED_PROMPTS below.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api.main  # noqa: E402 — resolves the circular import, same pattern used throughout this session
from database.pg_connections import SessionLocal  # noqa: E402
from database.pg_models import ClarityCorpus  # noqa: E402
from decision_engine.agentic_analyzer import create_analyzer  # noqa: E402
from decision_engine.clarity_heuristics import detect_gap_types  # noqa: E402
from sqlalchemy import text  # noqa: E402

# Diverse across problem type (diagnostic, decision, pricing, retention,
# hiring, cash flow, operations) and specificity (vague one-liners through
# fully-specified prompts) so the corpus has real precedent to match
# against regardless of what a user actually types.
SEED_PROMPTS = [
    # Vague diagnostic
    "Sales dropped and I don't know why",
    "People visit my store but nobody buys",
    "I'm busy all day but not making money",
    "Customers buy once and never come back",
    "My ads aren't working anymore",
    "I'm losing customers and I don't know why",
    "Nothing I post online gets any engagement",
    "My team is always busy but we never ship anything",
    # Decision / prioritization, unnamed options
    "I have too many ideas and don't know which one to focus on first",
    "I don't know whether to expand or stay small",
    "Should I raise my prices or not?",
    "I can't decide what to build next",
    # Hiring / team / cash flow
    "I'm thinking about hiring my first employee but not sure if I can afford it",
    "I want to raise my prices but I'm scared of losing customers",
    "Cash flow is tight and I don't know what to cut",
    "I'm overwhelmed and need to delegate but don't know what to hand off",
    # Well-specified (should NOT trigger clarification)
    "My Shopify store sells handmade candles, gets about 2,000 visits a month, converts at 0.8%, and I've already tried dropping prices 20% with no change in conversion.",
    "My online store gets 500 visits a week but only converts at 1%, and I don't know whether it's the product, the price, or the website.",
    "I run a 3-person marketing agency charging $2,000/month per client, have 6 clients, and I'm turning away leads because we're at capacity.",
    "My SaaS has 400 paying users at $29/month, churn is 8% monthly, and I've already tried an onboarding email sequence with no improvement.",
    # Partially specified (one gap, not two)
    "My ad spend keeps going up but conversions are flat — I run a D2C skincare brand on Meta ads.",
    "I run a small bakery in Lagos. Revenue has been flat for 3 months and I don't know what to fix first.",
]


async def seed():
    db = SessionLocal()
    try:
        analyzer = create_analyzer(db)
        from decision_engine.recommender_db import model as st_model, _model_lock

        existing = {
            r[0] for r in db.execute(text("SELECT submission_text FROM clarity_corpus")).all()
        }

        inserted = 0
        for prompt in SEED_PROMPTS:
            if prompt in existing:
                print(f"skip (already seeded): {prompt[:60]!r}")
                continue

            result = await analyzer.generate_clarifying_questions(prompt)
            gap_types = detect_gap_types(prompt)
            # Align the LLM's free-form questions to our gap_type slots so
            # the live engine can reuse them per-gap (see clarity_engine's
            # neighbor_questions matching) — best-effort positional
            # alignment since the LLM doesn't itself know our gap taxonomy.
            questions = [
                {
                    "id": q["id"],
                    "question": q["question"],
                    "gap_type": gap_types[i] if i < len(gap_types) else (gap_types[0] if gap_types else "missing_business_type"),
                }
                for i, q in enumerate(result["questions"])
            ]

            with _model_lock:
                embedding = st_model.encode(prompt).tolist()
            embedding_str = f"[{','.join(map(str, embedding))}]"

            row = ClarityCorpus(
                submission_text=prompt,
                needs_clarification=result["needs_clarification"],
                gap_types=gap_types,
                questions=questions,
                source="llm_seed",
            )
            db.add(row)
            db.flush()
            db.execute(
                text("UPDATE clarity_corpus SET embedding = CAST(:emb AS vector) WHERE id = :id"),
                {"emb": embedding_str, "id": row.id},
            )
            db.commit()
            inserted += 1
            print(f"seeded: {prompt[:60]!r} -> needs_clarification={result['needs_clarification']} gap_types={gap_types}")

        print(f"\nDone. Inserted {inserted} new rows, skipped {len(SEED_PROMPTS) - inserted} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed())
