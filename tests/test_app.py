import json
from unittest.mock import patch

from app import app


def test_healthz():
    with app.test_client() as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_platform_is_generic_and_secret_free(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "private-nebius")
    monkeypatch.setenv("TAVILY_API_KEY", "private-tavily")
    with app.test_client() as client:
        response = client.get("/api/v1/platform")
    serialized = json.dumps(response.json)
    assert response.status_code == 200
    assert response.json["application_host"] == "selected-cloud"
    assert response.json["map_service"] == "selected-map-service"
    assert response.json["nebius_configured"] is True
    assert response.json["tavily_configured"] is True
    assert "private-nebius" not in serialized
    assert "private-tavily" not in serialized


def test_plan_rejects_invalid_prompt():
    with app.test_client() as client:
        response = client.post("/api/v1/plan", json={"prompt": ""})
    assert response.status_code == 400


def test_plan_returns_council_trace():
    trace = {"provider": "Nebius Token Factory", "status": "completed"}
    with patch("app.plan_shift", return_value=("Cautious plan", "nemotron-super")), \
         patch("app.get_last_trace", return_value=trace):
        with app.test_client() as client:
            response = client.post("/api/v1/plan", json={"prompt": "Verified candidate"})
    assert response.status_code == 200
    assert response.json["recommendation"] == "Cautious plan"
    assert response.json["trace"] == trace
