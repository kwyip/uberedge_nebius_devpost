import json
from unittest.mock import MagicMock, patch

import pytest

import nebius_agents


def _response(text, model="model", tokens=10):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({
        "model": model,
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": tokens, "completion_tokens": 5, "total_tokens": tokens + 5},
    }).encode()
    return response


def _tavily_response():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({
        "results": [{
            "title": "Official event page",
            "url": "https://example.org/event",
            "content": "The public event begins at 6 PM.",
            "score": 0.9,
        }]
    }).encode()
    return response


@pytest.fixture(autouse=True)
def isolated_tavily(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)


def test_requires_nebius_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NEBIUS_API_KEY"):
        nebius_agents.plan_shift("verified candidates")


def test_rejects_insecure_remote_endpoint(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("NEBIUS_BASE_URL", "http://example.com/v1")
    with pytest.raises(RuntimeError, match="HTTPS"):
        nebius_agents.plan_shift("verified candidates")


def test_four_scouts_then_super_and_trace(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("NEMOTRON_FAST_MODEL", "nemotron-fast")
    monkeypatch.setenv("NEMOTRON_REASONING_MODEL", "nemotron-super")
    monkeypatch.delenv("NEBIUS_USE_DEEP_REVIEW", raising=False)
    responses = [_response("scout report") for _ in range(4)] + [_response("final worker plan")]
    with patch("nebius_agents.urllib.request.urlopen", side_effect=responses) as urlopen:
        recommendation, model = nebius_agents.plan_shift("verified candidates")

    assert (recommendation, model) == ("final worker plan", "nemotron-super")
    assert urlopen.call_count == 5
    trace = nebius_agents.get_last_trace()
    assert trace["provider"] == "Nebius Token Factory"
    assert trace["web_research"]["status"] == "not_configured"
    assert trace["successful_scouts"] == 4
    assert trace["status"] == "completed"
    assert len(trace["agents"]) == 5
    assert all("test-key" not in json.dumps(agent) for agent in trace["agents"])


def test_tavily_evidence_is_sent_to_nemotron_and_traced(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "nebius-secret")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-secret")
    responses = [_tavily_response()] + [_response("scout") for _ in range(4)] + [_response("plan")]
    with patch("nebius_agents.urllib.request.urlopen", side_effect=responses) as urlopen:
        recommendation, _ = nebius_agents.plan_shift("Boston shift on 2026-08-17")

    assert recommendation == "plan"
    assert urlopen.call_count == 6
    tavily_request = urlopen.call_args_list[0].args[0]
    assert tavily_request.full_url == "https://api.tavily.com/search"
    assert tavily_request.headers["Authorization"] == "Bearer tavily-secret"
    nemotron_body = json.loads(urlopen.call_args_list[-1].args[0].data)
    assert "https://example.org/event" in nemotron_body["messages"][1]["content"]
    trace = nebius_agents.get_last_trace()
    assert trace["web_research"]["status"] == "completed"
    assert trace["web_research"]["result_count"] == 1
    assert "tavily-secret" not in json.dumps(trace)


def test_tavily_failure_does_not_block_council(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    responses = [OSError("search unavailable")] + [_response("scout") for _ in range(4)] + [_response("plan")]
    with patch("nebius_agents.urllib.request.urlopen", side_effect=responses):
        recommendation, _ = nebius_agents.plan_shift("verified candidates")
    assert recommendation == "plan"
    assert nebius_agents.get_last_trace()["web_research"]["status"] == "failed"


def test_council_tolerates_one_scout_failure(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    responses = [OSError("temporary scout failure")] + [_response("scout") for _ in range(3)] + [_response("plan")]
    with patch("nebius_agents.urllib.request.urlopen", side_effect=responses):
        recommendation, _ = nebius_agents.plan_shift("verified candidates")
    assert recommendation == "plan"
    trace = nebius_agents.get_last_trace()
    assert trace["successful_scouts"] == 3
    assert sum(agent["status"] == "failed" for agent in trace["agents"]) == 1


def test_optional_ultra_review(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("NEBIUS_USE_DEEP_REVIEW", "1")
    monkeypatch.setenv("NEMOTRON_DEEP_MODEL", "nemotron-ultra")
    responses = [_response("scout") for _ in range(4)] + [_response("draft"), _response("reviewed")]
    with patch("nebius_agents.urllib.request.urlopen", side_effect=responses):
        recommendation, model = nebius_agents.plan_shift("verified candidates")
    assert (recommendation, model) == ("reviewed", "nemotron-ultra")
    assert nebius_agents.get_last_trace()["deep_review"] is True
