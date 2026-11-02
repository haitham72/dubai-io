"""Still-photo outfit try-on (contest demo). Live AR stays LATER.

Order: Vertex Virtual Try-On when configured → OpenAI image edit → honest failure.
Always returns bytes + provenance; never invents a success without a provider image.
"""
from __future__ import annotations

import base64
import io
import os
from typing import Any

import httpx

from .config import settings

# 1×1 PNG — only when TRYON_FIXTURE=1 (tests).
_FIXTURE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_THUMB_HOSTS = (
    "encrypted-tbn0.gstatic.com",
    "encrypted-tbn1.gstatic.com",
    "encrypted-tbn2.gstatic.com",
    "encrypted-tbn3.gstatic.com",
    "serpapi.com",
    "m.media-amazon.com",
)


class TryOnUnavailable(Exception):
    """No configured provider could produce a preview."""


def tryon_configured() -> dict[str, Any]:
    fixture = os.getenv("TRYON_FIXTURE", "").strip() in {"1", "true", "yes"}
    vertex = bool(os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_PROJECT"))
    return {
        "fixture": fixture,
        "vertex": vertex and bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or os.getenv("VERTEX_ACCESS_TOKEN")
            or os.getenv("GOOGLE_CLOUD_API_KEY")
        ),
        "openai": bool(settings.openai_api_key),
        "ready": fixture or bool(settings.openai_api_key) or (
            vertex and bool(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                or os.getenv("VERTEX_ACCESS_TOKEN")
                or os.getenv("GOOGLE_CLOUD_API_KEY")
            )
        ),
    }


def fetch_product_image(url: str, limit: int = 2_500_000) -> bytes:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    if not url.startswith("https://") or not any(host == h or host.endswith("." + h) for h in _THUMB_HOSTS):
        raise ValueError("product image host not allowed")
    with httpx.Client(timeout=12, follow_redirects=True) as http:
        r = http.get(url)
    r.raise_for_status()
    data = r.content
    if len(data) > limit or not data:
        raise ValueError("product image too large or empty")
    return data


def _vertex_tryon(person: bytes, garment: bytes) -> bytes:
    """Google Cloud virtual-try-on-001 (me-central1 preferred)."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_PROJECT") or ""
    region = os.getenv("VERTEX_LOCATION", "me-central1")
    if not project:
        raise TryOnUnavailable("VERTEX_PROJECT not set")

    person_b64 = base64.b64encode(person).decode("ascii")
    garment_b64 = base64.b64encode(garment).decode("ascii")
    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{region}/publishers/google/models/virtual-try-on-001:predict"
    )
    body = {
        "instances": [{
            "personImage": {"image": {"bytesBase64Encoded": person_b64}},
            "productImages": [{"image": {"bytesBase64Encoded": garment_b64}}],
        }],
        "parameters": {"sampleCount": 1},
    }

    token = os.getenv("VERTEX_ACCESS_TOKEN", "").strip()
    api_key = os.getenv("GOOGLE_CLOUD_API_KEY", "").strip()
    headers = {"Content-Type": "application/json"}
    params: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif api_key:
        params["key"] = api_key
    elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            import google.auth
            import google.auth.transport.requests

            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            creds.refresh(google.auth.transport.requests.Request())
            headers["Authorization"] = f"Bearer {creds.token}"
        except Exception as err:  # noqa: BLE001 — surface as unavailable
            raise TryOnUnavailable(f"ADC failed: {err}") from err
    else:
        raise TryOnUnavailable("No Vertex auth")

    with httpx.Client(timeout=90) as http:
        r = http.post(url, json=body, headers=headers, params=params)
    if r.status_code >= 400:
        raise TryOnUnavailable(f"Vertex try-on HTTP {r.status_code}")
    payload = r.json()
    preds = payload.get("predictions") or []
    if not preds:
        raise TryOnUnavailable("Vertex returned no image")
    b64 = (preds[0].get("bytesBase64Encoded")
           or (preds[0].get("image") or {}).get("bytesBase64Encoded")
           or "")
    if not b64:
        raise TryOnUnavailable("Vertex response missing image bytes")
    return base64.b64decode(b64)


def _openai_tryon(person: bytes, garment: bytes, title: str) -> bytes:
    """OpenAI image edit — labelled AI preview, not a size guide."""
    if not settings.openai_api_key:
        raise TryOnUnavailable("OPENAI_API_KEY not set")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=90.0)
    prompt = (
        "Virtual try-on preview: show the same person from the first photo wearing the clothing "
        f"item from the second photo ({title[:80]}). Keep the person's face, body shape and pose. "
        "Preserve garment colour and style. Photorealistic. No text overlay."
    )
    person_f = io.BytesIO(person)
    person_f.name = "person.png"
    garment_f = io.BytesIO(garment)
    garment_f.name = "garment.png"
    try:
        result = client.images.edit(
            model=os.getenv("TRYON_OPENAI_MODEL", "gpt-image-1"),
            image=[person_f, garment_f],
            prompt=prompt,
            size="1024x1536",
            n=1,
        )
    except Exception as err:  # noqa: BLE001
        raise TryOnUnavailable(f"OpenAI try-on failed: {err}") from err
    data = (result.data or [None])[0]
    if not data:
        raise TryOnUnavailable("OpenAI returned no image")
    if getattr(data, "b64_json", None):
        return base64.b64decode(data.b64_json)
    if getattr(data, "url", None):
        with httpx.Client(timeout=30) as http:
            img = http.get(data.url)
        img.raise_for_status()
        return img.content
    raise TryOnUnavailable("OpenAI image missing payload")


def run_tryon(person: bytes, garment: bytes, title: str) -> dict[str, Any]:
    if len(person) > 7_000_000 or len(garment) > 7_000_000:
        raise ValueError("image too large")
    if os.getenv("TRYON_FIXTURE", "").strip() in {"1", "true", "yes"}:
        return {
            "image": _FIXTURE_PNG,
            "media_type": "image/png",
            "provider": "fixture",
            "provenance": "demo_fixture",
            "caption": "AI preview · demo fixture · not a size guide",
        }

    errors: list[str] = []
    cfg = tryon_configured()
    if cfg["vertex"]:
        try:
            out = _vertex_tryon(person, garment)
            return {
                "image": out,
                "media_type": "image/png",
                "provider": "vertex_virtual_try_on",
                "provenance": "provider_confirmed",
                "caption": "AI preview · Google Virtual Try-On · results may be unexpected · not a size guide",
            }
        except TryOnUnavailable as err:
            errors.append(str(err))

    if cfg["openai"]:
        try:
            out = _openai_tryon(person, garment, title)
            return {
                "image": out,
                "media_type": "image/png",
                "provider": "openai_image",
                "provenance": "inferred",
                "caption": "AI preview · results may be unexpected · not a size guide",
            }
        except TryOnUnavailable as err:
            errors.append(str(err))

    raise TryOnUnavailable("; ".join(errors) or "No try-on provider configured")
