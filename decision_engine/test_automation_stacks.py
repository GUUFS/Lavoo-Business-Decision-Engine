"""
Automation Stack Demo — tests Stage 3B in isolation against the live database.
Runs 3 different business queries to demonstrate dynamic tool stack recommendations.

Usage (from project root):
    uv run --with python-dotenv python decision_engine/test_automation_stacks.py

Or if uv is managing the venv:
    PYTHONPATH=. uv run python decision_engine/test_automation_stacks.py
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(".env.local")

from database.pg_connections import SessionLocal
from decision_engine.agentic_analyzer import AgenticAnalyzer
from decision_engine.recommender_db import recommend_automation_stacks

# ---------------------------------------------------------------------------
# Demo queries — 3 distinct business personas
# ---------------------------------------------------------------------------

DEMO_SCENARIOS = [
    {
        "label": "E-Commerce Store Owner",
        "query": (
            "I run an online store selling handmade skincare products. "
            "I want to automate my social media content, customer follow-up emails, "
            "and product listing descriptions to save time and grow sales."
        ),
        "action_plans": [
            {
                "id": 1,
                "title": "Automate social media content creation and scheduling",
                "what_to_do": [
                    "Create a weekly content calendar for product posts and stories",
                    "Use AI tools to generate captions, hashtags, and product descriptions in bulk",
                    "Schedule posts across Instagram, TikTok, and Pinterest automatically",
                ],
            },
            {
                "id": 2,
                "title": "Set up post-purchase email automation",
                "what_to_do": [
                    "Trigger a thank-you email sequence after every order",
                    "Send automated review request at day 7 and reorder reminder at day 30",
                ],
            },
            {
                "id": 3,
                "title": "Generate SEO product listings at scale",
                "what_to_do": [
                    "Use AI writing tools to produce optimised product descriptions",
                    "A/B test different title formats to improve search ranking",
                ],
            },
        ],
        "primary_bottleneck": "Manual content creation blocking consistent brand presence",
        "secondary_constraints": [
            "No automated customer follow-up system",
            "Product listings lack SEO optimisation",
        ],
    },
    {
        "label": "Freelance Video Editor",
        "query": (
            "I am a freelance video editor with 8 clients. "
            "I spend too much time on admin — writing proposals, sending invoices, "
            "and updating my portfolio. I want to automate these so I can focus on editing."
        ),
        "action_plans": [
            {
                "id": 1,
                "title": "Automate client proposal and contract delivery",
                "what_to_do": [
                    "Build a proposal template triggered when a lead fills an intake form",
                    "Auto-send contract for e-signature once proposal is accepted",
                ],
            },
            {
                "id": 2,
                "title": "Automate invoicing and payment reminders",
                "what_to_do": [
                    "Generate and send invoice automatically on project completion",
                    "Schedule payment reminder emails at 3-day and 7-day overdue intervals",
                ],
            },
            {
                "id": 3,
                "title": "Keep portfolio updated automatically",
                "what_to_do": [
                    "Set up workflow to publish completed project thumbnails to portfolio site",
                    "Auto-generate case study text from project brief using AI writing tool",
                ],
            },
        ],
        "primary_bottleneck": "Admin overhead consuming 30% of billable hours",
        "secondary_constraints": [
            "Inconsistent invoicing and follow-up process",
            "Portfolio rarely updated, losing inbound leads",
        ],
    },
    {
        "label": "Digital Marketing Agency",
        "query": (
            "I run a small digital marketing agency with 4 team members serving 12 clients. "
            "I need to automate client reporting, content scheduling across platforms, "
            "and internal task tracking so we can take on more clients without burning out."
        ),
        "action_plans": [
            {
                "id": 1,
                "title": "Automate monthly client performance reports",
                "what_to_do": [
                    "Pull data from Google Analytics and ad platforms automatically",
                    "Generate branded PDF report and email to client on the 1st of each month",
                ],
            },
            {
                "id": 2,
                "title": "Centralise and automate cross-platform content scheduling",
                "what_to_do": [
                    "Use a unified scheduling tool to manage all client social accounts",
                    "Set up AI to repurpose long-form content into platform-specific formats",
                ],
            },
            {
                "id": 3,
                "title": "Automate project and task management for the team",
                "what_to_do": [
                    "Create task templates for recurring client deliverables",
                    "Set automated reminders and handoff notifications between team members",
                ],
            },
        ],
        "primary_bottleneck": "Manual reporting and task coordination capping client capacity",
        "secondary_constraints": [
            "No unified content scheduling system across clients",
            "Team communication relies on manual Slack updates",
        ],
    },
]


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _separator(title: str = "") -> None:
    line = "=" * 70
    if title:
        print(f"\n{line}")
        print(f"  {title}")
        print(line)
    else:
        print(line)


def _print_stack(idx: int, stack: dict) -> None:
    tools = stack.get("tools", [])
    tool_names = [t.get("tool_name", "?") for t in tools]

    print(f"\n  Stack {idx}: {stack.get('stack_name', 'Unnamed')}")
    print(f"  Tools   : {' + '.join(tool_names)}")
    print(f"  Summary : {stack.get('workflow_summary', stack.get('summary', ''))}")
    print(f"  Logic   : {stack.get('automation_logic', '')}")

    tool_roles = stack.get("tool_roles", [])
    if tool_roles:
        print("  Roles   :")
        for role in tool_roles:
            print(f"    [{role['tool_name']}] {role['role']}")
            print(f"      → {role['hands_off_to']}")

    setup_order = stack.get("setup_order", [])
    if setup_order:
        print("  Setup   :")
        for step in setup_order:
            print(f"    {step['position']}. {step['tool_name']} — {step['why']}")

    print(f"  Solves  : {stack.get('solves', '')}")
    print(f"  Effort  : {stack.get('estimated_effort', '?')}  |  Confidence: {stack.get('confidence', 0):.1f}%")


# ---------------------------------------------------------------------------
# Core test runner
# ---------------------------------------------------------------------------

async def run_scenario(analyzer: AgenticAnalyzer, session, scenario: dict, num: int) -> None:
    _separator(f"DEMO {num}: {scenario['label']}")
    print(f"\nQuery: {scenario['query']}\n")

    # Step 1 — algorithmic stack selection from DB
    print("[1/2] Running semantic search + greedy stack builder against DB...")
    raw_stacks = recommend_automation_stacks(
        user_query=scenario["query"],
        action_plans=scenario["action_plans"],
        top_k_stacks=3,
        max_tools_per_stack=4,
        db_session=session,
    )

    if not raw_stacks:
        print("  No stacks found — ensure ai_tools table is populated.")
        return

    candidate_names = [
        f"  • {s['stack_name']} → {[t['tool_name'] for t in s.get('tools', [])]}"
        for s in raw_stacks
    ]
    print(f"  Found {len(raw_stacks)} candidate stacks:")
    print("\n".join(candidate_names))

    # Step 2 — LLM enrichment
    print("\n[2/2] Running LLM enrichment agent (Grok)...")
    constraint_titles = scenario["secondary_constraints"]
    for stack in raw_stacks:
        if stack.get("tools") and constraint_titles:
            stack["solves"] = f"Helps reduce: {', '.join(constraint_titles[:3])}."

    enriched = await analyzer._enrich_stacks_with_llm(
        stacks=raw_stacks,
        user_query=scenario["query"],
        primary_bottleneck=scenario["primary_bottleneck"],
    )

    print(f"\n  Enriched {len(enriched)} stacks:\n")
    for i, stack in enumerate(enriched, start=1):
        _print_stack(i, stack)


async def main() -> None:
    session = SessionLocal()
    try:
        analyzer = AgenticAnalyzer(db_session=session)
        print("\nLAVOO Automation Stack Demo")
        print(f"Model : {analyzer.model}")
        print(f"DB    : connected ({session.bind.url.host if hasattr(session.bind, 'url') else 'ok'})")

        for num, scenario in enumerate(DEMO_SCENARIOS, start=1):
            await run_scenario(analyzer, session, scenario, num)

        _separator()
        print("\nDemo complete.")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
