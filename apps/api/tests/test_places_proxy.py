"""Photo and static-map proxies keep the key server-side and reject arbitrary input."""
import pytest
from fastapi.testclient import TestClient

from app import google_maps, main


@pytest.fixture
def client(monkeypatch):
    async def photo(name, w):
        if not google_maps.PHOTO_NAME.match(name):
            raise ValueError
        return b"jpg", "image/jpeg"
    async def smap(center, pins, z, size=None):
        return b"png"
    monkeypatch.setattr(google_maps, "place_photo", photo)
    monkeypatch.setattr(google_maps, "static_map", smap)
    return TestClient(main.app)


def test_photo_proxy_accepts_only_place_photo_names(client):
    assert client.get("/api/places/photo", params={"name": "places/abc/photos/xyz"}).status_code == 200
    for bad in ("https://evil.example/x.jpg", "places/abc/photos/xyz/../../secret", "places/a b/photos/c"):
        assert client.get("/api/places/photo", params={"name": bad}).status_code == 400


def test_static_map_validates_coordinates(client):
    assert client.get("/api/staticmap", params={"c": "25.08,55.14", "m": "25.08,55.13|25.09,55.14"}).status_code == 200
    assert client.get("/api/staticmap", params={"c": "25.08,55.14", "m": "999,1"}).status_code == 400
    assert client.get("/api/staticmap", params={"c": "drop table"}).status_code == 422


def test_key_never_appears_in_search_output_shape():
    # the browser receives a photo *name*, never a URL carrying the key
    assert "key=" not in google_maps.PLACE_FIELDS
