"""Routes: Gmail test-account routes (OAuth, read, send)."""
from __future__ import annotations

from fastapi import FastAPI

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from ..mail import MailNotLinked
from .models import SendIn
def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/mail/status")
    async def mail_status(req: Request):
        return S(req).mail.status()

    @app.get("/agents/mail/oauth/start")
    async def mail_start(req: Request):
        try:
            return RedirectResponse(S(req).mail.auth_url())
        except MailNotLinked as err:
            raise HTTPException(409, str(err)) from err

    @app.get("/agents/mail/oauth/callback")
    async def mail_callback(req: Request, code: str = "", state: str = ""):
        try:
            S(req).mail.finish(code, state)
        except Exception as err:  # noqa: BLE001
            raise HTTPException(400, f"Sign-in failed: {type(err).__name__}") from err
        return RedirectResponse(f"{S(req).cfg.public_url}/?mail=linked")

    @app.post("/agents/mail/unlink")
    async def mail_unlink(req: Request):
        S(req).mail.unlink()
        return S(req).mail.status()

    @app.get("/agents/mail/messages")
    async def mail_list(req: Request, q: str = "in:inbox", limit: int = 25):
        try:
            return {"mode": "gmail", "messages": await S(req).mail.list(q, limit)}
        except MailNotLinked:
            return {"mode": "demo", "messages": []}

    @app.get("/agents/mail/messages/{mid}")
    async def mail_get(mid: str, req: Request):
        try:
            return await S(req).mail.get(mid)
        except MailNotLinked as err:
            raise HTTPException(409, str(err)) from err

    @app.post("/agents/mail/send")
    async def mail_send(body: SendIn, req: Request):
        try:
            return await S(req).mail.send(body.to, body.subject, body.body, body.confirmed)
        except PermissionError as err:
            raise HTTPException(428, str(err)) from err
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        except MailNotLinked as err:
            raise HTTPException(409, str(err)) from err
