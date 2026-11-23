"""Messenger HTTP entrypoint. Run: uvicorn app.messenger.server:app --port 8070.

There is no image-generation route. Stickers are finished pack files or a
cut-out of a photo the user already has.
"""

from fastapi import FastAPI, HTTPException

from app.messenger.stickers import PackError, packs_root, resolve_sticker, load_manifest

app = FastAPI(title="Messenger")


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
