"""The closed action list (14 actions) the decision step chooses from, and how each one is allowed to run.

kind:
  in_app  — runs as soon as the decision is stable; reversible (re-decided if the person corrects themselves).
  outward — runs at end of speech, then waits out an undo window before it is final (sending to a person).
  paid    — runs only after a visible confirmation (it spends money or provider credits).
  none    — not a command; at end of speech the words go to the normal AI chat.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Kind = Literal["in_app", "outward", "paid", "none"]


@dataclass(frozen=True)
class Action:
    name: str
    kind: Kind
    description: str  # read by the decision model, so it describes the *request*, not the implementation
    needs: tuple[str, ...] = ()


ACTIONS: tuple[Action, ...] = (
    Action("open_screen", "in_app", "Open or show a part of the app: messages/chats, mail, calendar, weather, flights, stocks, files, research, or the AI assistant."),
    Action("open_chat", "in_app", "Open a conversation without sending anything: with one person or group, or the most recent one ('open my last chat').", ("contact",)),
    Action("send_message", "outward", "Send, text, tell, reply to or message a person or group something — including the most recent chat ('reply to the last chat saying …').", ("contact", "text")),
    Action("read_messages", "in_app", "Read out or catch up on messages in the app: 'read my messages', 'what did Mazen say', 'any new messages', 'what did the family group send'. Reading, not sending."),
    Action("compose_email", "in_app", "Write or send an email to someone: 'email Rashid that I'm late', 'send an email to … saying …'. Opens a filled-in email for the person to review and send.", ("text",)),
    Action("check_notifications", "in_app", "Check notifications or updates in the app: 'what's new', 'any updates', 'is my research ready', what Mirsal finished."),
    Action("get_weather", "in_app", "Weather, temperature or forecast for a place.", ("city",)),
    Action("search_flights", "paid", "Find or book flights between places.", ("to",)),
    Action("research_topic", "paid", "Research, look into, or compare something on the web and write a brief.", ("topic",)),
    Action("plan_trip", "paid", "Plan a trip, vacation or holiday: dates, leave, flights and budget, maybe with a person.", ("request",)),
    Action("plan_meeting", "in_app", "Prepare a calendar draft for a meeting, dinner or event. 'Plan for it' after a meeting proposal refers to that proposal. Never a travel itinerary; the person reviews and saves the draft.", ("request",)),
    Action("generate_image", "paid", "Create, draw or generate a picture or image.", ("prompt",)),
    Action("generate_video", "paid", "Create or generate a video, reel or clip.", ("prompt",)),
    Action("none", "none", "Not a command for the app: a general-knowledge question, small talk, thinking aloud, or unfinished. Questions about the person's own messages or updates are commands."),
)
BY_NAME = {a.name: a for a in ACTIONS}

# Screen ids are the app's ScreenId values; "messages" is the person's word for the chats screen.
SCREENS: dict[str, str] = {
    "messages": "chats", "mail": "mail", "calendar": "calendar", "weather": "weather", "flights": "flights",
    "stocks": "stocks", "files": "files", "research": "research", "ai": "ai",
}
SCREEN_HELP: dict[str, str] = {
    "messages": "messages, chats, conversations, inbox of chats, WhatsApp-style messages",
    "mail": "email, mail, Gmail, inbox of emails",
    "calendar": "calendar, schedule, agenda, meetings",
    "weather": "weather app",
    "flights": "flights app, trips, bookings",
    "stocks": "stocks, markets, portfolio, shares",
    "files": "files, documents, photos",
    "research": "research reports",
    "ai": "Mirsal AI assistant chat",
}
