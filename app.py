"""Sanitized public API for the Uberedge hackathon submission."""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from nebius_agents import get_last_trace, plan_shift


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "uberedge-public-demo"}


@app.get("/api/v1/platform")
def platform():
    """Describe integrations without returning credentials or vendor-private details."""
    return {
        "agent_runtime": "nebius-nemotron-opportunity-council",
        "inference_provider": "Nebius Token Factory",
        "web_research": "Tavily",
        "nebius_configured": bool(os.getenv("NEBIUS_API_KEY")),
        "tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
        "application_host": "selected-cloud",
        "map_service": "selected-map-service",
        "frontend": "public-placeholder",
    }


@app.post("/api/v1/plan")
def create_plan():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return jsonify({"error": "prompt must be a string"}), 400
    prompt = prompt.strip()
    if not prompt or len(prompt) > 6000:
        return jsonify({"error": "prompt must contain 1 to 6000 characters"}), 400

    try:
        recommendation, model = plan_shift(prompt)
    except RuntimeError as error:
        status = 503 if "not configured" in str(error).lower() else 502
        return jsonify({"error": str(error)}), status

    return {
        "recommendation": recommendation,
        "model": model,
        "agent": "nebius-nemotron-opportunity-council",
        "trace": get_last_trace(),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5173)
