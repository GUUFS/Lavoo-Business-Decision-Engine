"""
Training data (decision_engine/training_data.py): trusted micromodel
examples become fine-tuning lines (prompt -> questions); examples the LLM
teacher overruled, and skipped ones, are left out.
"""
import json

from database.pg_models import ClarityCorpus
from decision_engine.training_data import export_jsonl, training_summary


def _corpus(db, text_, source, outcome=None, needs=True, agreed=None):
    """One micromodel/LLM example."""
    db.add(ClarityCorpus(submission_text=text_, source=source, outcome=outcome, needs_clarification=needs,
                         gap_types=[], questions=[{"id": "q1", "question": f"Who buys {text_}?"}] if needs else [],
                         teacher_agreed=agreed))
    db.flush()


def test_questions_dataset_keeps_trusted_examples_only(db):
    _corpus(db, "train-a candles shop", "llm_teacher")
    _corpus(db, "train-b bakery", "live", outcome="answered")
    _corpus(db, "train-c gym", "live", outcome="answered", agreed=False)   # LLM overruled it
    _corpus(db, "train-d tutoring", "live", outcome="skipped")              # user skipped
    _corpus(db, "train-e clear prompt", "llm_seed", needs=False)
    body, count = export_jsonl(db, "questions")
    examples = {json.loads(line)["messages"][1]["content"]: json.loads(line) for line in body.splitlines()}
    assert {"train-a candles shop", "train-b bakery", "train-e clear prompt"} <= set(examples)
    assert "train-c gym" not in examples and "train-d tutoring" not in examples
    answer = json.loads(examples["train-a candles shop"]["messages"][2]["content"])
    assert answer == {"needs_clarification": True, "questions": ["Who buys train-a candles shop?"]}
    assert json.loads(examples["train-e clear prompt"]["messages"][2]["content"])["questions"] == []
    assert count == len(body.splitlines())


def test_summary_counts_match_the_export(db):
    _corpus(db, "train-f florist", "llm_teacher")
    summary = training_summary(db)
    assert summary["questions"]["examples"] == export_jsonl(db, "questions")[1]
    assert summary["questions"]["target"] == 1000 and "checkups" in summary
