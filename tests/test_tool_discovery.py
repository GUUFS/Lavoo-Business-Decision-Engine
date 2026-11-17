"""
Tool discovery (decision_engine/tool_discovery.py): tools an analysis
suggests that the catalog doesn't have are logged, looked up in an outside
directory, filled in from their own website and added to ai_tools; every
name ends with a status and a reason. Outside calls (Wikidata, websites,
the LLM) are replaced by fakes here.
"""
import asyncio
import json

import pytest

from database.pg_models import AITool, ToolDiscovery
from decision_engine import tool_discovery as td

PAGE = {"url": "https://www.tally.so/", "title": "Tally | The simplest way to create forms",
        "text": "Tally lets you build forms for free. Integrates with Notion, Zapier and Slack."}

FILLED = {
    "is_business_software": True, "official_name": "Tally Forms", "summary": "Free form builder.",
    "description": "Tally is a form builder. It makes forms and surveys without code.",
    "main_category": "AI Productivity Tools", "sub_category": "form-builder",
    "ai_categories": ["forms", "surveys"], "pricing": "Free: unlimited forms | Pro: $29 a month",
    "key_features": ["Unlimited forms: no limit on the free plan"], "pros": ["Free: generous free plan"],
    "cons": [], "who_should_use": ["Small businesses: collect leads"],
    "compatibility_integration": ["Notion: send answers to a Notion database"],
}


@pytest.fixture
def fakes(monkeypatch):
    """Outside calls replaced: Wikidata, web pages, the LLM, embeddings."""
    state = {"wikidata": {"website": PAGE["url"], "description": "online form builder",
                          "directory": "wikidata", "directory_url": "https://www.wikidata.org/wiki/Q1"},
             "fields": dict(FILLED), "guess": None, "page_error": None}

    async def lookup(name, client):
        return state["wikidata"]

    async def fetch(url, client):
        if state["page_error"]:
            raise ValueError(state["page_error"])
        return dict(PAGE)

    async def ask(analyzer, prompt, max_tokens=1400):
        return state["fields"]

    async def guess(analyzer, name):
        return state["guess"]

    monkeypatch.setattr(td, "lookup_wikidata", lookup)
    monkeypatch.setattr(td, "fetch_page", fetch)
    monkeypatch.setattr(td, "_ask_llm", ask)
    monkeypatch.setattr(td, "_llm_website_guess", guess)
    monkeypatch.setattr(td, "_embedding_for", lambda columns: None)
    return state


def _catalog_tool(db, name):
    """A tool already in the catalog."""
    tool = AITool(name=name, description=f"{name} description", main_category="AI Productivity Tools")
    db.add(tool)
    db.flush()
    return tool


def _logged(db, name="Tally"):
    """A pending discovery row."""
    row = ToolDiscovery(name=name, name_key=td.normalize_name(name), status="pending", times_suggested=1, attempts=0)
    db.add(row)
    db.flush()
    return row


def _run(db, row):
    """discover_one with the fakes (no analyzer or HTTP client needed)."""
    asyncio.run(td.discover_one(db, row, analyzer=None, client=None))


def test_collects_every_suggested_tool_name_once():
    data = {
        "action_plans": [{"toolkit": {"tool_name": "Tally"}, "steps": [{"tools": [{"tool_name": "tally"}]}]}],
        "recommended_tool_stacks": [{"tools": ["Clay", "Email"]}],
        "single_tool_recommendation": {"tool_name": "Lemlist"},
    }
    assert td.suggested_tool_names(data) == ["Tally", "Clay", "Lemlist"]


def test_only_names_missing_from_the_catalog_are_logged_and_repeats_are_counted(db):
    _catalog_tool(db, "Zapier Discovery Test")
    rows = td.record_suggestions(db, ["Zapier Discovery Test", "Tallyformz Test"], analysis_id=7)
    assert [r.name for r in rows] == ["Tallyformz Test"]
    td.record_suggestions(db, ["tallyformz test"], analysis_id=8)
    row = db.query(ToolDiscovery).filter_by(name_key="tallyformz test").one()
    assert row.times_suggested == 2 and row.first_analysis_id == 7 and row.last_analysis_id == 8


def test_found_tool_is_added_with_the_catalogs_column_formats(db, fakes):
    row = _logged(db, "Tallyz Unique")
    _run(db, row)
    assert row.status == "added", row.reason
    tool = db.get(AITool, row.tool_id)
    assert tool.name == "Tally Forms" and tool.source == "discovered" and tool.url == PAGE["url"]
    assert json.loads(tool.key_features) == ["Unlimited forms: no limit on the free plan"]
    assert json.loads(tool.cons) == [] and tool.ratings == 0.0
    assert row.directory == "wikidata" and "Wikidata" in row.reason


def test_not_a_business_product_is_rejected_with_the_reason(db, fakes):
    fakes["fields"] = {"is_business_software": False, "reject_reason": "a person, not a product"}
    row = _logged(db, "Some Person Unique")
    _run(db, row)
    assert row.status == "rejected" and "a person" in row.reason
    assert row.tool_id is None


def test_no_directory_entry_and_no_confirmed_website_is_not_found(db, fakes):
    fakes["wikidata"] = None
    row = _logged(db, "Nowhere Tool Unique")
    _run(db, row)
    assert row.status == "not_found" and "couldn't name an official website" in row.reason


def test_llm_website_is_only_trusted_when_the_page_names_the_tool(db, fakes):
    fakes["wikidata"], fakes["guess"] = None, "https://example-wrong-site.com/"
    row = _logged(db, "Zyxwv Unique")          # PAGE doesn't mention this name
    _run(db, row)
    assert row.status == "not_found" and "doesn't mention the tool's name" in row.reason


def test_a_failure_keeps_the_exact_error_and_counts_the_attempt(db, fakes):
    fakes["page_error"] = "https://www.tally.so/ answered HTTP 503"
    row = _logged(db, "Failing Tool Unique")
    _run(db, row)
    assert row.status == "failed" and row.attempts == 1
    assert "HTTP 503" in row.reason and "Attempt 1 of 3" in row.reason


def test_private_addresses_are_never_fetched():
    assert not asyncio.run(td._is_public_http_url("http://127.0.0.1/admin"))
    assert not asyncio.run(td._is_public_http_url("file:///etc/passwd"))
