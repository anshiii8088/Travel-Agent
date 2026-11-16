import json

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_phase7_plan_status_and_preferences_roundtrip():
    payload = {
        "origin": "Kochi",
        "destination": "Munnar",
        "start_date": "2026-12-01",
        "days": 2,
        "travellers": 2,
        "budget": 5000,
        "currency": "INR",
        "preferences": {
            "travel_style": "Balanced",
            "interests": ["Nature"],
            "dietary_preferences": "Vegetarian",
            "preferred_transport": "Cab",
        },
    }

    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] in {"COMPLETED", "APPROVAL_REQUIRED", "LIMIT_REACHED", "ERROR"}
    assert "session_id" in result

    sid = result["session_id"]
    status_resp = client.get(f"/api/plan/{sid}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["session_id"] == sid

    prefs_resp = client.get("/api/preferences")
    assert prefs_resp.status_code == 200

    chat_resp = client.post("/api/chat", json={"session_id": sid, "message": "What should I pack?"})
    assert chat_resp.status_code == 200
    assert "response" in chat_resp.json()

    logs_resp = client.get(f"/api/logs/{sid}")
    assert logs_resp.status_code == 200
    assert "logs" in logs_resp.json()


def test_phase7_sse_stream_emits_session_events():
    payload = {
        "origin": "Kochi",
        "destination": "Munnar",
        "start_date": "2026-12-01",
        "days": 2,
        "travellers": 2,
        "budget": 5000,
        "currency": "INR",
        "preferences": {
            "travel_style": "Balanced",
            "interests": ["Nature"],
            "dietary_preferences": "Vegetarian",
            "preferred_transport": "Cab",
        },
    }

    plan = client.post("/api/plan", json=payload)
    session_id = plan.json()["session_id"]

    stream = client.get(f"/api/plan/{session_id}/stream")
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers.get("content-type", "")
    body = stream.text
    assert "event:" in body.lower() or "data:" in body.lower()
    assert "session_id" in body
