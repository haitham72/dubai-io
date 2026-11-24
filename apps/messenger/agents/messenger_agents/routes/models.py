"""Request models + the chat-context helper shared by the route modules."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from ..chat_skills import MAX_PHOTOS, Msg

class ResearchIn(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    force: bool = False

class SendIn(BaseModel):
    to: str = Field(max_length=320)
    subject: str = Field(max_length=300)
    body: str = Field(max_length=20000)
    confirmed: bool = False

class FactsIn(BaseModel):
    facts: list[str] = Field(max_length=50)

class TasksIn(BaseModel):
    tasks: list[dict] = Field(max_length=200)


class ChatMsg(BaseModel):
    sender: str = Field(max_length=80)
    text: str = Field(max_length=4000)


class SkillIn(BaseModel):
    context: list[ChatMsg] = Field(default_factory=list, max_length=30)
    request: str = Field(default="", max_length=500)
    target: str = Field(default="", max_length=4000)
    # Photos for the fact check: https URLs, data: URLs (sent from the browser, downscaled) or app paths ("/photos/x.jpg").
    images: list[Annotated[str, Field(max_length=6_000_000)]] = Field(default_factory=list, max_length=MAX_PHOTOS)
    exclude: str = Field(default="", max_length=80)
    contacts: list[dict] = Field(default_factory=list, max_length=500)
    chatPartner: str | None = Field(default=None, max_length=80)
    # Resolved participant ids an existing trip card already has. When given (even empty), the planner keeps
    # exactly these people across date changes instead of re-deriving them — nobody is asked twice.
    members: list[str] | None = Field(default=None, max_length=50)


class LeaveIn(BaseModel):
    start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    leaveDays: int = Field(ge=1, le=60)
    note: str = Field(default="", max_length=200)


class CommandIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    contacts: list[dict] = Field(default_factory=list, max_length=500)


def _ctx(body: SkillIn) -> list[Msg]:
    return [Msg(m.sender, m.text) for m in body.context][-10:]
