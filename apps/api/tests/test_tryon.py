"""Still-photo try-on — fixture path + status; no live provider calls in CI."""
import os

import pytest
from fastapi.testclient import TestClient

from app import main, tryon


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("TRYON_FIXTURE", "1")
    return TestClient(main.app)


def test_tryon_status_reports_fixture(monkeypatch):
    monkeypatch.setenv("TRYON_FIXTURE", "1")
    cfg = tryon.tryon_configured()
    assert cfg["fixture"] is True and cfg["ready"] is True


def test_tryon_requires_adult_confirm(client):
    files = {"person": ("me.png", tryon._FIXTURE_PNG, "image/png")}
    data = {"title": "Green shirt", "product_image_url": "https://encrypted-tbn0.gstatic.com/shopping?q=x"}
    r = client.post("/api/tryon", files=files, data=data)
    assert r.status_code == 400


def test_tryon_fixture_preview(client, monkeypatch):
    monkeypatch.setattr(tryon, "fetch_product_image", lambda url: tryon._FIXTURE_PNG)
    files = {"person": ("me.png", tryon._FIXTURE_PNG, "image/png")}
    data = {
        "title": "Green shirt",
        "product_image_url": "https://encrypted-tbn0.gstatic.com/shopping?q=x",
        "confirmed_adult": "1",
    }
    r = client.post("/api/tryon", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["provenance"] == "demo_fixture" and body["demo"] is True and body["image_base64"]


def test_fetch_product_image_rejects_bad_host():
    with pytest.raises(ValueError):
        tryon.fetch_product_image("https://evil.example/x.png")
