"""MG-B4 packs and cut-out. Voice-on-real-messages waits for MG-B3."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.messenger.png import decode_png, encode_png
from app.messenger.server import app
from app.messenger.stickers import (
    PackError,
    cutout_any_subject,
    resolve_sticker,
    selfie_fallback,
)

ROOT = Path(__file__).resolve().parents[2] / "messenger" / "public" / "packs"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "messenger" / "stickers" / "object.png"
client = TestClient(app)


def _object_png() -> bytes:
    samples = bytearray()
    for i in range(16):
        samples += bytes((i * 10, 40, 80))
    return encode_png(4, 4, bytes(samples), 3)


def test_messenger_pack_sends_file_from_manifest():
    sent = resolve_sticker(ROOT, "demo-dot", "dot")
    assert sent["kind"] == "sticker"
    assert sent["packId"] == "demo-dot" and sent["stickerId"] == "dot"
    assert sent["label"] == "Demo data"
    assert sent["provenance"] == "demo_fixture"
    assert sent["bytes"] == (ROOT / "demo" / "dot.svg").read_bytes()
    body = client.post("/api/messenger/packs/demo-dot/stickers/dot")
    assert body.status_code == 200
    assert body.json()["kind"] == "sticker"
    assert body.json()["label"] == "Demo data"


def test_messenger_pack_unknown_id_returns_no_file():
    with pytest.raises(PackError):
        resolve_sticker(ROOT, "demo-dot", "missing")
    assert client.post("/api/messenger/packs/demo-dot/stickers/missing").status_code == 404


def test_messenger_cutout_any_subject_png_has_alpha():
    image = FIXTURE.read_bytes()
    _w, _h, channels, before = decode_png(image)
    assert channels == 3

    def matte(_image: bytes) -> bytes:
        alpha = bytearray(16)
        for i in (5, 6, 9, 10):
            alpha[i] = 255
        return bytes(alpha)

    result = cutout_any_subject(image, runner=matte)
    assert result["error"] is None and result["stored"] is True
    w, h, out_ch, after = decode_png(result["png"])
    assert (w, h, out_ch) == (4, 4, 4)
    for i in range(16):
        assert after[i * 4 : i * 4 + 3] == before[i * 3 : i * 3 + 3]
        expect = 255 if i in (5, 6, 9, 10) else 0
        assert after[i * 4 + 3] == expect


def test_messenger_cutout_missing_model_keeps_original():
    image = FIXTURE.read_bytes()
    result = cutout_any_subject(image, weight=None)
    assert result["error"] == "model_missing"
    assert result["stored"] is False
    assert result["png"] == image


def test_messenger_selfie_fallback_rejects_non_person():
    image = FIXTURE.read_bytes()
    result = selfie_fallback(image, person_detected=False)
    assert result["error"] == "subject_not_detected"
    assert result["stored"] is False
    assert result["png"] == image


def test_messenger_no_image_generation_route():
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not any("image" in path or "generat" in path for path in paths)
    assert "/api/images" not in paths
    folder = Path(__file__).resolve().parents[1] / "app" / "messenger"
    text = "\n".join(p.read_text(encoding="utf-8") for p in folder.glob("*.py")).lower()
    assert "api/images" not in text
    assert "higgs" not in text
