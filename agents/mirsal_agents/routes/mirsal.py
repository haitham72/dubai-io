"""Routes: @mirsal chat skills: fact check, ideas, stickers, plan, command."""
from __future__ import annotations

from fastapi import FastAPI

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from ..chat_skills import image_ideas
from ..contacts import Contact
from ..engine import Conversation
from .models import CommandIn, SkillIn, _ctx
def register(app: FastAPI, S, user) -> None:
    @app.post("/agents/mirsal/factcheck")
    async def factcheck(body: SkillIn, req: Request):
        target = body.target or (body.context[-1].text if body.context else "")
        try:
            out = await S(req).factcheck.check(target, _ctx(body), body.images)
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        await S(req).tracer.record("mirsal", skill="factcheck", verdict=out.get("verdict"), mode=out.get("mode"),
                                   photos=out.get("photos", 0))
        return out

    @app.post("/agents/mirsal/image-ideas")
    async def ideas(body: SkillIn, req: Request):
        return await image_ideas(S(req).idea_llm, _ctx(body), body.request)

    @app.post("/agents/mirsal/look")
    async def look(body: SkillIn, req: Request):
        from ..skills.look import look as look_at
        question = body.target or (body.context[-1].text if body.context else "")
        try:
            out = await look_at(S(req).factcheck.llm, question, _ctx(body), body.images)
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        await S(req).tracer.record("mirsal", skill="look", mode=out.get("mode"),
                                   photos=out.get("photos", 0))
        return out

    @app.post("/agents/mirsal/stickers")
    async def sticker_pack(body: SkillIn, req: Request):
        pack = S(req).stickers.pick(_ctx(body), exclude=body.exclude)
        if not pack:
            raise HTTPException(404, "No sticker packs found")
        return {**pack, "urls": [f"/agents/stickers/file/{pack['id']}/{f}" for f in pack["stickers"]]}

    @app.post("/agents/mirsal/plan")
    async def plan(body: SkillIn, req: Request):
        contacts = [Contact(str(c["id"]), str(c["name"])) for c in body.contacts if c.get("id") and c.get("name")]
        out = await S(req).planner.plan(user(req), _ctx(body), contacts, body.chatPartner, request=body.request,
                                        keep_members=body.members)
        await S(req).tracer.record("mirsal", skill="plan", title=out.get("title") or out.get("ask", "")[:80],
                                   steps=[st["kind"] for st in out.get("steps", [])])
        return out

    @app.post("/agents/mirsal/command")
    async def command(body: CommandIn, req: Request):
        """A typed "@mirsal open/read/reply …" decided by the same intent engine as voice (one turn, offline-safe).
        Callers send contacts most-recent first, so "my last chat" is the first one. Paid actions still come back
        as `confirm` (the caller sends the person to the normal flow); sends come back as `undo`."""
        s = S(req)
        contacts = [Contact(str(c["id"]), str(c["name"])) for c in body.contacts if c.get("id") and c.get("name")]
        conv = Conversation(s.decider, contacts, s.policy)
        eng = conv.begin()
        eng.partial(body.text[:500], 0.0)
        events = await conv.finish(1.0)
        await s.tracer.record("mirsal", skill="command", text=body.text[:200], events=[e.wire() for e in events])
        return {"events": [e.wire() for e in events]}
