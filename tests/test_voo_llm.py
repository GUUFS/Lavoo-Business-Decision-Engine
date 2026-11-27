"""Unit tests for Voo LLM provider routing, Responses API extraction, and citation cleanup."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from api.routes.community.community import (
    _call_voo_llm,
    _clean_text_extras,
    _extract_responses_text,
)


def test_extract_responses_text_prefers_output_text_and_falls_back_to_output_blocks():
    assert _extract_responses_text(SimpleNamespace(output_text="  hello json  ", output=[])) == "hello json"
    nested = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(type="reasoning", content=[]),
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(text='{"respond": true, "reply": "Line one"}')],
            ),
        ],
    )
    assert _extract_responses_text(nested) == '{"respond": true, "reply": "Line one"}'


def test_clean_text_extras_strips_web_citations_preserving_paragraphs():
    raw = "OpenAI released GPT-5 last month [[1]](https://example.com/a).\n\nYour Check-up score [[2]] stays separate."
    cleaned = _clean_text_extras(raw)
    assert cleaned == "OpenAI released GPT-5 last month.\n\nYour Check-up score stays separate."


def test_call_voo_llm_uses_grok_responses_with_web_search_by_default(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    monkeypatch.delenv("VOO_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("VOO_GROK_MODEL", raising=False)
    monkeypatch.delenv("VOO_GROK_WEB_SEARCH", raising=False)

    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(
        output_text='{"ok": true}',
        model="grok-4.3",
        output=[],
    )

    with patch("openai.OpenAI", return_value=mock_client) as mock_ctor:
        content, model = _call_voo_llm("sys prompt", "usr prompt", mode="followup", temperature=0.5, max_tokens=700)

    assert content == '{"ok": true}'
    assert model == "grok-4.3"
    mock_ctor.assert_called_once()
    assert mock_ctor.call_args.kwargs["base_url"] == "https://api.x.ai/v1"
    kwargs = mock_client.responses.create.call_args.kwargs
    assert kwargs["model"] == "grok-4.3"
    assert kwargs["instructions"] == "sys prompt"
    assert kwargs["input"] == "usr prompt"
    assert kwargs["tools"] == [{"type": "web_search"}]
    assert kwargs["max_output_tokens"] == 2500
    assert kwargs["store"] is False


def test_call_voo_llm_falls_back_to_nemotron_and_respects_provider_override(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    monkeypatch.setenv("VOO_LLM_PROVIDER", "nvidia")
    monkeypatch.delenv("VOO_NVIDIA_MODEL", raising=False)

    nv_client = MagicMock()
    nv_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"from": "nvidia"}'))]
    )

    with patch("openai.OpenAI", return_value=nv_client) as mock_ctor:
        content, model = _call_voo_llm("sys", "usr", mode="summary", max_tokens=300)

    assert content == '{"from": "nvidia"}'
    assert model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert mock_ctor.call_args.kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert nv_client.chat.completions.create.call_args.kwargs["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert nv_client.chat.completions.create.call_args.kwargs["max_tokens"] == 1500


def test_call_voo_llm_falls_back_when_primary_errors_or_returns_none(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    monkeypatch.delenv("VOO_LLM_PROVIDER", raising=False)

    nv_client = MagicMock()
    nv_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="fallback ok"))]
    )

    with patch("openai.OpenAI", return_value=nv_client):
        content, model = _call_voo_llm("sys", "usr", mode="angle")

    assert content == "fallback ok"
    assert model == "nvidia/nemotron-3-ultra-550b-a55b"
