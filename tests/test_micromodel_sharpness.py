"""
Tests that the clarity micromodel asks questions that fit the prompt, and
that the teacher notices when it doesn't.

  - Creators and impact goals get creator questions (focus, platform,
    audience), never "what does your business sell?".
  - A stored example is only copied or borrowed from when it's the same kind
    of prompt, and borrowed wording must fit the prompt at least as well.
  - The teacher's "agreed" now requires matching questions, not just the
    same yes/no on asking.

Uses the real reasoner and the real embedding model; only the LLM is faked.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from database.pg_models import ClarityCorpus, ClarityTeacherCall
from decision_engine import clarity_teacher
from decision_engine.clarity_engine import _decide, _precedent_fits
from decision_engine.clarity_reasoner import build_questions, extract_facts, reason

CREATOR_PROMPT = (
    "I am a content creator. I create content across various aspects of life. I would want a way for "
    "the content i create to be one that would influence and affect people positively."
)


def questions_for(prompt):
    """The reasoner's own questions for a prompt (no stored examples)."""
    return build_questions(reason(prompt))


# ── The reasoner ────────────────────────────────────────────────────────────

def test_creator_impact_prompt_gets_focus_and_audience_questions():
    result = reason(CREATOR_PROMPT)
    assert result["facts"]["domain"] == "creator"
    assert result["facts"]["problem_types"][0] == "impact"
    asked = [q["question"] for q in build_questions(result)]
    assert len(asked) == 2
    assert "topics" in asked[0] and "help" in asked[0]                       # focus
    assert "follow or watch you" in asked[1] and "positive influence" in asked[1]
    assert not any("sell" in q or "indicator" in q for q in asked)


def test_creator_with_platform_is_asked_about_that_platform():
    asked = [q["question"] for q in questions_for(
        "I post on TikTok about personal finance and I want my videos to actually help people.")]
    assert any("on TikTok" in q and "positive influence" in q for q in asked)


def test_creator_with_numbers_and_timeline_needs_no_questions():
    assert questions_for("I'm a YouTuber with 2,000 subscribers and my views have dropped for 3 months.") == []


def test_influencer_pricing_question_is_about_brand_pay():
    asked = [q["question"] for q in questions_for("I'm an influencer and brands aren't paying me enough.")]
    assert len(asked) == 1 and "brands pay you per post" in asked[0]


def test_business_prompts_are_unchanged():
    asked = [q["question"] for q in questions_for("Sales dropped and I don't know why")]
    assert any("sell" in q for q in asked) and any("before the drop" in q for q in asked)


# ── Using stored examples ───────────────────────────────────────────────────

def test_example_from_a_different_kind_of_prompt_is_not_used():
    shop_example = {"id": 1, "submission_text": "I want more customers for my bakery in Lagos",
                    "needs_clarification": True,
                    "questions": [{"question": "What indicator would you use to measure success?",
                                   "gap_type": "missing_numbers_or_constraint"}]}
    fits, why = _precedent_fits(extract_facts(CREATOR_PROMPT), shop_example)
    assert not fits and "creator" in why

    result = reason(CREATOR_PROMPT)
    path, asks, questions = _decide(CREATOR_PROMPT, result, shop_example, 0.9)
    assert path == "reasoner" and asks
    assert not any("indicator" in q["question"] for q in questions)
    assert any("isn't the same kind of prompt" in t for t in result["trace"])


def test_borrowed_wording_that_fits_worse_is_rejected():
    creator_example = {"id": 2, "submission_text": "I'm a content creator and I want to inspire people positively",
                       "needs_clarification": True,
                       "questions": [{"question": "What indicator would you use to measure success?",
                                      "gap_type": "missing_numbers_or_constraint"}]}
    result = reason(CREATOR_PROMPT)
    path, _, questions = _decide(CREATOR_PROMPT, result, creator_example, 0.7)
    assert path == "blend"
    assert not any("indicator" in q["question"] for q in questions)


def test_borrowed_wording_that_fits_as_well_is_used():
    creator_example = {"id": 3, "submission_text": "I'm a content creator and I want to inspire people positively",
                       "needs_clarification": True,
                       "questions": [{"question": "Which platforms do you post on, how many followers do you have, "
                                                  "and what would a positive influence on your audience look like?",
                                      "gap_type": "missing_numbers_or_constraint"}]}
    result = reason(CREATOR_PROMPT)
    _, _, questions = _decide(CREATOR_PROMPT, result, creator_example, 0.7)
    assert any(q["question"].startswith("Which platforms do you post on") for q in questions)


# ── The teacher ─────────────────────────────────────────────────────────────

class FakeAnalyzer:
    """The teacher's LLM: answers every prompt with `verdict`."""

    def __init__(self, verdict):
        self.verdict = verdict

    async def generate_clarifying_questions(self, prompt):
        return self.verdict


def _live_decision(db, questions):
    """A blended live decision that asked `questions`, old enough to check."""
    row = ClarityCorpus(
        submission_text=CREATOR_PROMPT, needs_clarification=True, gap_types=[], source="live",
        questions=[{"id": f"q{i}", "question": q} for i, q in enumerate(questions)],
        decision_path="blend", confidence=0.8, created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db.add(row)
    db.flush()
    return row


def _run_teacher(db, verdict):
    """One teacher run with the fake LLM (no stored LLM answers to reuse)."""
    db.query(ClarityCorpus).filter(ClarityCorpus.source == "live", ClarityCorpus.submission_text != CREATOR_PROMPT) \
        .update({"teacher_reviewed_at": datetime.now(UTC)}, synchronize_session=False)
    db.query(ClarityCorpus).filter(ClarityCorpus.source.in_(["llm_seed", "llm_teacher"])).delete(synchronize_session=False)
    with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(verdict)):
        return asyncio.run(clarity_teacher.run_teacher_batch(db, limit=5))


LLM_CREATOR_VERDICT = {"needs_clarification": True, "questions": [
    {"question": "What specific topics or niche do you focus on, and who is your target audience?"},
    {"question": "Which platforms do you publish on, and how big is your audience there?"},
]}


def test_teacher_disagrees_when_the_question_is_off_topic(db):
    _live_decision(db, ["What indicator would you use to measure success?"])
    result = _run_teacher(db, LLM_CREATOR_VERDICT)
    call = db.query(ClarityTeacherCall).filter_by(run_id=result["run_id"]).one()
    assert call.micromodel_asked and call.llm_asked          # both said "ask"...
    assert call.question_match < clarity_teacher.QUESTION_MATCH_THRESHOLD
    assert call.agreed is False                              # ...but not the same questions
    assert call.micromodel_questions == ["What indicator would you use to measure success?"]


def test_teacher_agrees_when_the_questions_match(db):
    _live_decision(db, [q["question"] for q in build_questions(reason(CREATOR_PROMPT))])
    result = _run_teacher(db, LLM_CREATOR_VERDICT)
    call = db.query(ClarityTeacherCall).filter_by(run_id=result["run_id"]).one()
    assert call.question_match >= clarity_teacher.QUESTION_MATCH_THRESHOLD
    assert call.agreed is True


# ── Prompts the micromodel used to ask the wrong question for ───────────────

def texts(prompt):
    """Just the wording of the reasoner's questions for a prompt."""
    return [q["question"] for q in questions_for(prompt)]


def test_named_new_business_asks_budget_timeline_and_demand_not_current_numbers():
    qs = texts("I want to start a laundry pickup service for students in Abuja.")
    assert len(qs) == 1
    assert "laundry pickup service" in qs[0] and "budget" in qs[0] and "pay for it" in qs[0]
    assert "right now" not in qs[0] and "monthly revenue" not in qs[0]


def test_named_new_business_with_budget_and_timeline_needs_no_questions():
    assert texts("I want to start a laundry pickup service for students in Abuja. "
                         "I have N1.5m and want to launch in 2 months.") == []


def test_choice_between_ways_to_grow_asks_budget_not_team_hours():
    qs = texts("Should I hire a sales person or run ads?")
    assert any("budget" in q for q in qs)
    assert not any("hours a week" in q for q in qs)


def test_many_problems_at_once_asks_which_hurts_most():
    qs = texts("Everything is going wrong with my business. Marketing, cash, staff, product. Where do I start?")
    assert qs[0].startswith("Of marketing, cash, staff and product, which one is hurting the business most")
    assert not any("hours a week" in q for q in qs)


def test_busy_some_days_empty_others_asks_quiet_vs_busy_days():
    qs = texts("My restaurant is busy on weekends but empty Monday to Thursday.")
    assert len(qs) == 1 and "quiet day compared with a busy one" in qs[0]


def test_coach_is_not_asked_what_the_business_sells():
    qs = texts("I'm a coach. I want more clients.")
    assert not any("sell or do" in q for q in qs)


def test_website_reads_as_your_website():
    qs = texts("Should I sell on Jumia, Konga, or my own website?")
    assert not any("on Website" in q for q in qs)
