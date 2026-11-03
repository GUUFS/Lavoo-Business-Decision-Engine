import os
import sys

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import sqlalchemy
_real_create_engine = sqlalchemy.create_engine

def _mock_create_engine(*args, **kwargs):
    return _real_create_engine("sqlite:///:memory:")

sqlalchemy.create_engine = _mock_create_engine

import api.routes.community.community as community
from api.routes.community.community import (
    _load_voo_glossary,
    get_voo_angle_system_prompt,
    get_voo_followup_system_prompt,
    _validate_angle_data,
    _validate_followup_data,
    _clean_dashes,
    _clean_text_extras,
    _parse_json_response,
    ANGLE_PROMPT_VERSION,
    FOLLOWUP_PROMPT_VERSION,
)

print("=== 1. Testing System Prompts and Glossary Injection ===")
glossary = _load_voo_glossary()
assert len(glossary) > 100, "Glossary is too short!"
assert "[FILL IN]" not in glossary, "Glossary contains [FILL IN]!"
print(f"Glossary loaded successfully ({len(glossary)} chars, 0 [FILL IN] placeholders)")

angle_sys = get_voo_angle_system_prompt()
assert "{{GLOSSARY}}" not in angle_sys, "{{GLOSSARY}} was not replaced in Angle system prompt!"
assert len(angle_sys) > 1000, "Angle system prompt too short!"
print(f"Angle system prompt built successfully ({len(angle_sys)} chars, hash: {community.VOO_ANGLE_SYSTEM_PROMPT_HASH[:12]})")

followup_sys = get_voo_followup_system_prompt()
assert "{{GLOSSARY}}" not in followup_sys, "{{GLOSSARY}} was not replaced in Followup system prompt!"
assert len(followup_sys) > 1000, "Followup system prompt too short!"
print(f"Followup system prompt built successfully ({len(followup_sys)} chars, hash: {community.VOO_FOLLOWUP_SYSTEM_PROMPT_HASH[:12]})")

print("\n=== 2. Testing Cleaning and Dash Utilities ===")
dash_test = "This is a Check-up—and a test–done well."
cleaned = _clean_dashes(dash_test)
assert cleaned == "This is a Check-up, and a test, done well.", f"Unexpected dash clean: {cleaned}"
assert "Check-up" in cleaned, "Hyphen in Check-up was modified!"
print("Dash utility test passed: em and en dashes converted to ', ', hyphen preserved.")

greeting_test = "Hey @kingsley, here is the answer."
cleaned_greeting = _clean_text_extras(greeting_test, replier_handle="@kingsley")
assert not cleaned_greeting.lower().startswith("hey"), f"Greeting not stripped: {cleaned_greeting}"
print("Greeting stripping test passed.")

print("\n=== 3. Testing Angle Validation Guards ===")
# Valid angle payload
valid_angle_payload = {
    "respond": True,
    "question_type": "decision",
    "reasoning": "Sorting question. Member asks about pricing tiers.",
    "obvious_answer": "Charge more.",
    "angle_type": "reframe",
    "angle": "When founders struggle with pricing, they usually assume the price itself is wrong. More often, the problem is who they are presenting that price to and what outcome that person is paying to achieve. Test whether your current buyers actually have the problem your pricing solves before you rewrite your entire tier structure.",
    "test": "Ask your last three lost prospects why they walked away."
}

is_valid, err, cleaned_data = _validate_angle_data(
    data=valid_angle_payload,
    recent_raw_openings=["A completely different opening that does not repeat"],
    thread_replies_str="",
    post_type="Question",
    post_title="How should I price my consulting packages?",
    post_content="I am debating between hourly billing or value-based tiers."
)
assert is_valid, f"Expected valid angle to pass, but failed with: {err}"
print(f"Valid angle passed validation! Word count: {len(cleaned_data['angle'].split())}")

# Test guard 1: Lavoo guard (ordinary question with Lavoo mentioned in reply should fail)
lavoo_violation_payload = dict(valid_angle_payload)
lavoo_violation_payload["angle"] = "When founders struggle with pricing, they should use Lavoo Check-up to see where their weaknesses are and find their Missions before moving forward with any other business plans or decisions. This ensures that their business model is completely aligned with market requirements and client expectations across the board."
is_valid, err, _ = _validate_angle_data(
    data=lavoo_violation_payload,
    recent_raw_openings=[],
    thread_replies_str="",
    post_type="Question",
    post_title="How should I price my consulting packages?",
    post_content="I am debating between hourly billing or value-based tiers."
)
assert not is_valid and "Lavoo guard triggered" in err, f"Lavoo guard failed to catch violation! Got: {err}"
print(f"Lavoo guard correctly caught violation: {err}")

# Test guard 2: Stray letter guard (the 'L' bug)
stray_letter_payload = dict(valid_angle_payload)
stray_letter_payload["angle"] = "L When founders struggle with pricing, they usually assume the price itself is wrong. More often, the problem is who they are presenting that price to and what outcome that person is paying to achieve. Test whether your current buyers actually have the problem your pricing solves before you rewrite your entire tier structure."
is_valid, err, _ = _validate_angle_data(
    data=stray_letter_payload,
    recent_raw_openings=[],
    thread_replies_str="",
    post_type="Question",
    post_title="Pricing question",
    post_content="Details here"
)
assert not is_valid and "Stray letter guard" in err, f"Stray letter guard failed! Got: {err}"
print(f"Stray letter guard correctly caught 'L' artifact: {err}")

# Test guard 3: Question type validation
bad_qtype_payload = dict(valid_angle_payload)
bad_qtype_payload["question_type"] = "general"
is_valid, err, _ = _validate_angle_data(
    data=bad_qtype_payload,
    recent_raw_openings=[],
    thread_replies_str="",
    post_type="Question",
    post_title="Pricing question",
    post_content="Details here"
)
assert not is_valid and "Invalid question_type" in err, f"Question type check failed! Got: {err}"
print(f"Question type check correctly caught invalid type: {err}")

print("\n=== 4. Testing Follow-up Validation Guards ===")
# Valid follow-up payload
valid_followup_payload = {
    "respond": True,
    "reply_type": "clarifying",
    "reasoning": "Clarifying the pricing question with a concrete example.",
    "changes_original": False,
    "reply": "If you bill hourly, you punish yourself every time you work faster. Fixed fees tied to a single deliverable protect your margin and make the cost predictable for the client."
}

is_valid, err, cleaned_followup = _validate_followup_data(
    data=valid_followup_payload,
    original_angle_text=valid_angle_payload["angle"],
    conversation_str="@john: I prefer hourly billing.",
    post_type="Question",
    post_title="Pricing question",
    post_content="Details"
)
assert is_valid, f"Expected valid follow-up to pass, got: {err}"
print(f"Valid follow-up passed validation! Word count: {len(cleaned_followup['reply'].split())}")

# Sensitive data guard (phone number)
phone_violation_payload = dict(valid_followup_payload)
phone_violation_payload["reply"] = "You can call our team on 08031234567 to get personalized help with structuring your hourly consulting rates and invoices."
is_valid, err, _ = _validate_followup_data(
    data=phone_violation_payload,
    original_angle_text=valid_angle_payload["angle"],
    conversation_str="",
    post_type="Question",
    post_title="Pricing question",
    post_content="Details"
)
assert not is_valid and "Sensitive data guard" in err, f"Sensitive data guard failed! Got: {err}"
print(f"Sensitive data guard correctly caught phone number: {err}")

print("\n=== ALL VOO V2 UNIT & GUARD TESTS PASSED SUCCESSFULLY! ===")
