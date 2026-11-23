"""Authenticated chat HTTP and the Origin-bound WebSocket."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.identity.deps import require_app_principal, require_ws_principal
from app.identity.models import VerifiedPrincipal
from app.messenger.store import ChatError, ChatStore

router = APIRouter()
_member = require_app_principal("messenger", frozenset({"messenger:chat"}))


def _chat(request: Request) -> ChatStore:
    return request.app.state.chat_store


def _http(exc: ChatError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


@router.post("/api/messenger/conversations")
def create_conversation(request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_member)):
    if body.get("recipients") or body.get("user_id"):
        raise HTTPException(422, "no_bulk_or_cold_send")
    try:
        conversation_id = _chat(request).create_conversation(
            principal.user_id,
            list(body.get("member_ids") or []),
            kind=str(body.get("kind") or "direct"),
            title=str(body.get("title") or ""),
        )
    except ChatError as exc:
        raise _http(exc) from exc
    _chat(request).link_user(principal.user_id)
    return {"id": conversation_id}


@router.get("/api/messenger/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, request: Request, after: int = 0, principal: VerifiedPrincipal = Depends(_member)):
    try:
        return {"messages": _chat(request).since(conversation_id, principal.user_id, after)}
    except ChatError as exc:
        raise _http(exc) from exc


@router.post("/api/messenger/conversations/{conversation_id}/messages")
def post_message(conversation_id: str, request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_member)):
    if "recipients" in body:
        raise HTTPException(422, "no_bulk")
    try:
        message = _chat(request).send(conversation_id, principal.user_id, str(body.get("client_msg_id") or ""), str(body.get("text") or ""))
    except ChatError as exc:
        raise _http(exc) from exc
    return message


@router.post("/api/messenger/conversations/{conversation_id}/messages/{message_id}/edit")
def edit_message(conversation_id: str, message_id: str, request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_member)):
    try:
        return _chat(request).edit(conversation_id, principal.user_id, message_id, str(body.get("text") or ""))
    except ChatError as exc:
        raise _http(exc) from exc


@router.post("/api/messenger/conversations/{conversation_id}/messages/{message_id}/delete")
def delete_message(conversation_id: str, message_id: str, request: Request, principal: VerifiedPrincipal = Depends(_member)):
    try:
        return _chat(request).delete(conversation_id, principal.user_id, message_id)
    except ChatError as exc:
        raise _http(exc) from exc


@router.post("/api/messenger/conversations/{conversation_id}/receipts")
def receipt(conversation_id: str, request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_member)):
    try:
        _chat(request).receipt(conversation_id, principal.user_id, str(body.get("message_id") or ""), str(body.get("kind") or ""))
    except ChatError as exc:
        raise _http(exc) from exc
    return {"ok": True}


@router.websocket("/api/messenger/ws")
async def socket(websocket: WebSocket):
    principal = require_ws_principal(
        websocket,
        app_id="messenger",
        required_capabilities=frozenset({"messenger:ws"}),
    )
    await websocket.accept()
    chat: ChatStore = websocket.app.state.chat_store
    chat.link_user(principal.user_id)
    await websocket.send_json({"op": "ready", "user_id": principal.user_id})
    try:
        while True:
            data = await websocket.receive_json()
            op = data.get("op")
            try:
                if op == "subscribe":
                    rows = chat.since(str(data.get("conversation_id") or ""), principal.user_id, int(data.get("last_seq") or 0))
                    for row in rows:
                        if row["sender_id"] != principal.user_id:
                            chat.receipt(row["conversation_id"], principal.user_id, row["id"], "delivered")
                    await websocket.send_json({"op": "replay", "messages": rows})
                elif op == "send":
                    if "recipients" in data:
                        await websocket.send_json({"op": "error", "code": "no_bulk"})
                        continue
                    message = chat.send(
                        str(data.get("conversation_id") or ""),
                        principal.user_id,
                        str(data.get("client_msg_id") or ""),
                        str(data.get("text") or ""),
                    )
                    await websocket.send_json({"op": "ack", "message": message})
                else:
                    await websocket.send_json({"op": "error", "code": "unknown_op"})
            except ChatError as exc:
                await websocket.send_json({"op": "error", "code": exc.code})
    except WebSocketDisconnect:
        return
