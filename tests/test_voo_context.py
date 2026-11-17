"""
Voo (The Build Room) must read ordinary questions as being about the
member's own business, not about Lavoo:
  - the angle prompt uses the shared, current glossary (voo_glossary.txt)
    instead of an old pasted copy, and says when Lavoo facts may be used;
  - no example teaches "a vague question means how Lavoo works";
  - Lavoo posts and unrelated threads are kept out of an ordinary question's context.
"""
from api.routes.community import community
from api.routes.community.community import _mentions_lavoo, _shares_topic


def test_angle_prompt_uses_the_shared_glossary_and_the_reading_rule():
    community.VOO_ANGLE_SYSTEM_PROMPT = None          # rebuild from the files
    prompt = community.get_voo_angle_system_prompt()
    assert "{{GLOSSARY}}" not in prompt
    assert prompt.count("LAVOO PLATFORM GLOSSARY") == 1
    assert "Use it only for questions that name Lavoo" in prompt     # the current glossary file
    assert "WHAT A QUESTION IS ABOUT" in prompt
    assert '"the app", "the platform", "my users"' in prompt


def test_no_example_reads_a_vague_question_as_being_about_lavoo():
    community.VOO_ANGLE_SYSTEM_PROMPT = None
    prompt = community.get_voo_angle_system_prompt()
    assert 'I am reading this as \\"how does Lavoo work?\\"' not in prompt
    assert "I am reading this as your business being slow" in prompt


def test_followup_prompt_has_the_reading_rule():
    community.VOO_FOLLOWUP_SYSTEM_PROMPT = None
    assert "WHAT A QUESTION IS ABOUT" in community.get_voo_followup_system_prompt()


def test_lavoo_mentions_are_detected():
    assert _mentions_lavoo("Would you spend Chops on an extra Check-up?")
    assert not _mentions_lavoo("How do I get my first 100 customers for my bakery?")


def test_only_related_threads_count_as_context():
    assert _shares_topic("How to price skincare products", "Raising skincare products price this month")
    assert not _shares_topic("Would you use Chops for a Check-up?", "How do I hire my first salesperson?")
