"""T02-server tests: flights mock, image route refuses generation, chat-without-key. No real network."""

import json

import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server.server as srv

client = TestClient(srv.app)

FLIGHT_PARAMS = {
    "from": "DXB",
    "to": "LHR",
    "depart": "2026-12-12",
    "passengers": "1",
    "cabin": "economy",
}

REQUIRED_FLIGHT_KEYS = {
    "id",
    "airline",
    "flightNo",
    "date",
    "fromCode",
    "fromTime",
    "toCode",
    "toTime",
    "duration",
    "stops",
    "price",
    "currency",
    "cabin",
}


def test_flights_mock_shape(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "")
    r = client.get("/api/flights", params=FLIGHT_PARAMS)
    assert r.status_code == 200, r.text
    flights = r.json()
    assert 5 <= len(flights) <= 8
    for f in flights:
        assert REQUIRED_FLIGHT_KEYS <= set(f), f
        assert f["currency"] == "AED"
        assert f["cabin"] == "Economy"
    cheapest = min(flights, key=lambda f: f["price"])
    assert cheapest.get("bestPrice") is True


def test_flights_mock_deterministic(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "")
    a = client.get("/api/flights", params=FLIGHT_PARAMS).json()
    b = client.get("/api/flights", params=FLIGHT_PARAMS).json()
    assert a == b


def test_image_route_does_not_generate():
    r = client.post("/api/images", json={"prompt": "a Dubai beach at sunset"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "failed"
    assert body["error"] == "Image generation is not part of this app"
    assert client.get(f"/api/images/{body['id']}").json()["status"] == "failed"


def test_image_unknown_job():
    r = client.get("/api/images/does-not-exist")
    assert r.status_code == 404


def test_chat_without_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    r = client.post("/api/chat", json={"messages": [{"role": "user", "text": "hi"}]})
    assert r.status_code == 503
    assert "OpenAI key missing" in r.text


def test_chat_tools_include_video():
    """Chat tools include video and image names. Neither starts an outside generator."""
    tools = {t["function"]["name"]: t["function"] for t in srv.TOOLS}
    assert set(tools) >= {"generate_image", "generate_video", "search_flights", "get_weather"}
    params = tools["generate_video"]["parameters"]
    assert params["required"] == ["prompt"]
    assert "video" in tools["generate_video"]["description"].lower()


def _fake_openai(monkeypatch, name, arguments):
    """Stub openai.OpenAI so /api/chat needs no network."""
    call = SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))
    message = SimpleNamespace(content=None, tool_calls=[call])
    completions = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(message=message)])
    )
    monkeypatch.setattr("openai.OpenAI", lambda api_key=None: SimpleNamespace(chat=SimpleNamespace(completions=completions)))


def test_chat_video_action_with_mocked_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _fake_openai(monkeypatch, "generate_video", {"prompt": "a Dubai sunset"})
    r = client.post("/api/chat", json={"messages": [{"role": "user", "text": "Make a video of a Dubai sunset"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action"] == {"type": "video", "prompt": "a Dubai sunset"}
    assert "video" in body["text"].lower()


@pytest.mark.parametrize("cabin,label", [("economy", "Economy"), ("business", "Business"), ("first", "First")])
def test_mock_cabin_display_preserves_query_contract(monkeypatch, cabin, label):
    monkeypatch.setenv("SERPAPI_KEY", "")
    response = client.get("/api/flights", params={**FLIGHT_PARAMS, "cabin": cabin})
    assert response.status_code == 200
    assert all(flight["cabin"] == label for flight in response.json())


@pytest.mark.parametrize("cabin,label", [("economy", "Economy"), ("business", "Business"), ("first", "First")])
def test_serpapi_cabin_display(monkeypatch, cabin, label):
    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    received = []

    def fake_get(url, params, timeout):
        received.append(params)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "best_flights": [{"price": 1234, "total_duration": "7h 25m", "flights": [{
                "airline": "Emirates", "flight_number": "EK 007", "departure_time": "08:30", "arrival_time": "15:55",
            }]}],
        })

    monkeypatch.setattr("httpx.get", fake_get)
    response = client.get("/api/flights", params={**FLIGHT_PARAMS, "cabin": cabin})
    assert response.status_code == 200
    assert response.json()[0]["cabin"] == label
    # Display casing must not alter request validation or supplier parameters.
    if cabin != "economy":
        assert received[0]["travel_class"] == label


def test_image_route_rejects_a_second_call():
    body = {"prompt": "retry the same Dubai beach prompt"}
    first = client.post("/api/images", json=body).json()
    second = client.post("/api/images", json=body).json()
    assert first["status"] == "failed" and second["status"] == "failed"
    assert first["id"] != second["id"]
