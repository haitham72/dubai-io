"""Messenger HTTP entrypoint. Run: uvicorn app.messenger.server:app --port 8070.

There is no image-generation route.
Stickers are finished pack files or a cut-out of a photo the user already has.
"""

from fastapi import FastAPI, HTTPException

from app.identity.router import create_identity_router
from app.messenger.routes_chat import router as chat_router
from app.messenger.stickers import PackError, load_manifest, packs_root, resolve_sticker
import app.messenger.capabilities  # noqa: F401  registers workspace.task.create

app = FastAPI(title="Messenger")
app.include_router(create_identity_router())
app.include_router(chat_router)


@app.get("/api/messenger/health")
def health() -> dict:
    return {"ok": True, "app": "messenger"}


@app.get("/api/messenger/packs")
def packs() -> dict:
    root = packs_root()
    manifest = load_manifest(root)
    return {
        "packs": [
            {"id": p["id"], "label": p.get("label"), "provenance": p.get("provenance"), "stickers": [s["id"] for s in p.get("stickers") or []]}
            for p in manifest.get("packs") or []
        ]
    }


@app.post("/api/messenger/packs/{pack_id}/stickers/{sticker_id}")
def send_pack_sticker(pack_id: str, sticker_id: str) -> dict:
    try:
        sent = resolve_sticker(packs_root(), pack_id, sticker_id)
    except PackError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"kind": sent["kind"], "packId": sent["packId"], "stickerId": sent["stickerId"], "label": sent["label"], "provenance": sent["provenance"]}



@app.get("/api/messenger/health")
def health() -> dict:
    return {"ok": True, "app": "messenger"}


@app.get("/api/messenger/packs")
def packs() -> dict:
    root = packs_root()
    manifest = load_manifest(root)
    return {
        "packs": [
            {"id": p["id"], "label": p.get("label"), "provenance": p.get("provenance"), "stickers": [s["id"] for s in p.get("stickers") or []]}
            for p in manifest.get("packs") or []
        ]
    }


@app.post("/api/messenger/packs/{pack_id}/stickers/{sticker_id}")
def send_pack_sticker(pack_id: str, sticker_id: str) -> dict:
    try:
        sent = resolve_sticker(packs_root(), pack_id, sticker_id)
    except PackError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"kind": sent["kind"], "packId": sent["packId"], "stickerId": sent["stickerId"], "label": sent["label"], "provenance": sent["provenance"]}
