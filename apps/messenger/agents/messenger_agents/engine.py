"""Streaming intent engine: partial transcripts in, action events out. Pure logic (no network, no clock of its own) so the
live WebSocket session and the offline eval drive exactly the same code.

Events
  act      in-app action; runs now. A later revision of the same clause sends `cancel` for it, then a new `act`.
  undo     outward action (send to a person); the browser runs it after an undo window unless cancelled.
  confirm  paid action; the browser runs it only after the person confirms.
  ask      one short question; nothing runs. The answer arrives as the next utterance.
  cancel   withdraws an earlier event (a correction, or "cancel / never mind").
  chat     not a command; the words go to the normal AI chat.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass, field

from .catalog import BY_NAME, SCREENS
from .contacts import Contact, Match, mentions, resolve, similar
from .deciders import NOBODY, NO_SCREEN, UNKNOWN, Decider, Decision
from .router import plan_texts, route_utterance
from .meeting import meeting_args
from .text import CANCEL, LAST_CHAT, NO, REPLY, SEND_HEAD, YES, apply_correction, city, command_head, email_parts, flight_route, message_text, norm, prompt, send_parts, split_clauses, topic

SCREEN_LABEL = {"messages": "Messages", "mail": "Mail", "calendar": "Calendar", "weather": "Weather", "flights": "Flights",
                "stocks": "Stocks", "files": "Files", "research": "Research", "ai": "Messenger AI"}
_ACTION_LABEL = {"open_screen": "open an app", "open_chat": "open a chat", "send_message": "send a message",
                 "get_weather": "check the weather", "search_flights": "search flights", "research_topic": "research it",
                 "generate_image": "create an image", "generate_video": "create a video", "read_messages": "read your messages",
                 "check_notifications": "check your updates", "plan_trip": "plan a trip", "plan_meeting": "prepare a meeting draft", "compose_email": "write an email"}
_TRIP_WORDS = re.compile(r"\b(?:trip|vacation|holiday|getaway|travel)\b", re.I)


# In-app actions whose argument is free text at the end of the clause wait for the clause to close.
FREE_TEXT_ARGS = {"get_weather", "read_messages", "compose_email"}  # "read Arif's…" waits for the whole name


@dataclass
class Event:
    type: str
    t: float
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    action: str = ""
    args: dict = field(default_factory=dict)
    label: str = ""
    p: float = 0.0
    clause: str = ""
    source: str = ""
    ref: str = ""  # for cancel: the event it withdraws
    awaiting: str = ""  # the turn must stay open for dictation after this event ("reply")

    def wire(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in ("", {}, None)}


@dataclass
class Policy:
    threshold: float = 0.80        # act only when the top action's probability is at least this…
    margin: float = 0.30           # …and leads the runner-up by at least this
    contact_threshold: float = 0.6
    stable_s: float = 0.35         # a partial must stay unchanged this long before it is decided (eval/REPORT.md, phase 3)
    strict_namesakes: bool = True  # a first name with a near-namesake in the contacts asks
    max_decisions: int = 16        # per utterance (cost guard)


@dataclass
class _Clause:
    text: str = ""
    decision: Decision | None = None
    outcome: tuple | None = None
    event: Event | None = None
    final: bool = False


@dataclass
class Pending:
    """An open question: the action it belongs to and the clauses that were waiting behind it."""
    action: str
    clause: str
    candidates: tuple[Contact, ...] = ()
    rest: list[str] = field(default_factory=list)
    contact: Contact | None = None  # settled recipient when the question is for the words ("What should I say?")
    kind: str = "command"  # trip_intent / calendar_offer retain the original request across clarification


def _label(action: str, args: dict) -> str:
    match action:
        case "open_screen": return f"Opening {SCREEN_LABEL.get(args['name'], args['name'])}"
        case "open_chat": return f"Opening your chat with {args['name']}"
        case "send_message": return f"Sending to {args['name']}: “{args['text']}”"
        case "get_weather": return f"Weather in {args['city']}"
        case "search_flights": return f"Search flights to {args['to']}?"
        case "research_topic": return f"Deep research: {args['topic']}?"
        case "generate_image": return f"Create an image: {args['prompt']}?"
        case "generate_video": return f"Create a video: {args['prompt']}?"
        case "read_messages": return f"Reading {args['name']}'s messages" if args.get("name") else "Reading your new messages"
        case "check_notifications": return "Checking your updates"
        case "compose_email": return f"Email to {args['to'] or '…'} ready to review — press Send when it looks right"
        case "plan_trip": return f"Plan this trip{' with ' + args['name'] if args.get('name') else ''}: {args['request']}?"
        case "plan_meeting": return f"Meeting draft{' with ' + args['name'] if args.get('name') else ''} ready to review"
    return action


def _dictation_pending(clause: str, contact: Contact | None) -> bool:
    """A send head with no words to send yet ("reply with", "tell him", "tell Arif", "tell him that"):
    dictation is still coming, so the turn must stay open for it."""
    if not SEND_HEAD.match(clause):
        return False
    if re.search(r"\b(?:with|saying|that|to say|:)\s*$", clause):
        return True
    return not message_text(clause, contact.name if contact else None)


class IntentEngine:
    """One utterance. Feed `partial(text, t)`; call `tick(t)` regularly and `end(t)` when speech stops."""

    def __init__(self, decider: Decider, contacts: list[Contact], policy: Policy | None = None) -> None:
        self.decider, self.contacts, self.policy = decider, contacts, policy or Policy()
        self.text, self.changed_at = "", 0.0
        self.revision = 0
        self.clauses: list[_Clause] = []
        self.decisions: list[dict] = []  # every decision, for calibration and the trace
        self.plan: dict | None = None
        self.events: list[Event] = []
        self.pending: Pending | None = None
        self.ended = False
        self.withdrawn = False  # "never mind" withdrew the request: nothing goes to chat either
        self.last_contact: Contact | None = None  # "open Travel Buddies and send *them* …"
        self.last_message = ""
        self.last_message_contact = ""
        self._slot_words = {k for c in contacts for k in c.keys} | set(SCREENS) | {"mail", "email", "calendar", "chats"}

    def partial(self, text: str, t: float) -> None:
        text = " ".join(text.split())
        if text != self.text:
            self.text, self.changed_at = text, t
            self.revision += 1

    async def tick(self, t: float, final: bool = False) -> list[Event]:
        out: list[Event] = []
        if self.pending or self.ended:
            return out
        revision = self.revision
        if final:
            self.plan = await route_utterance(self.text, self.contacts)
        parts = plan_texts(self.plan) if final else split_clauses(self.text)
        # A revised STT transcript can remove a boundary. Withdraw any stale trailing act before re-deciding.
        for stale in self.clauses[len(parts):]:
            out += self._revise(stale, None, t)
        del self.clauses[len(parts):]
        for i, raw in enumerate(parts):
            while len(self.clauses) <= i:
                self.clauses.append(_Clause())
            st = self.clauses[i]
            closed = final or i < len(parts) - 1
            if not closed and t - self.changed_at < self.policy.stable_s:
                break
            if st.final or (st.text == raw and not final):
                continue
            if CANCEL.match(raw):
                self.withdrawn = True
                out += self._cancel_all(t, raw)
                st.text, st.final = raw, final
                continue
            corrected = apply_correction(raw, self._slot_words)
            if corrected.corrected and CANCEL.match(corrected.after):
                out += self._revise(st, None, t)
                st.text, st.final = raw, final
                self.withdrawn = True
                continue
            if st.text == raw and st.decision:
                d = st.decision  # unchanged words: re-apply the policy at end of speech, no new request
            else:
                if len(self.decisions) >= self.policy.max_decisions and not final:
                    break  # the cap only limits early decisions; the end of speech is always decided
                d = await self.decider.decide(corrected.text, self.text, self.contacts)
            at = t + d.latency_ms / 1000
            a, p, margin = Decision.top(d.action)
            self.decisions.append({"clause": corrected.text, "corrected": corrected.corrected, "action": a, "p": round(p, 4),
                                   "margin": round(margin, 4), "source": d.source, "final": final, "t": round(at, 3),
                                   "latencyMs": round(d.latency_ms, 1), "note": d.note})
            if self.revision != revision:
                # Transcription kept streaming during the request. Never apply an answer
                # to the old transcript; the next tick reads only the newest snapshot.
                self.decisions[-1]["stale"] = True
                self.events += out
                return out
            st.text, st.decision = raw, d
            evs = self._policy(st, corrected.text, d, closed, final, at)
            if evs and any(e.type == "act" and e.action in ("open_chat", "open_screen", "read_messages") for e in evs) \
                    and any(_dictation_pending(p, self.last_contact) for p in parts[i + 1:]):
                # The chat is open but the message is still being dictated — hold the turn for it.
                for e in evs:
                    if e.type == "act":
                        e.awaiting = "reply"
            out += evs
            if final:
                st.final = True
            if any(e.type == "ask" for e in evs):
                if self.pending:
                    self.pending.rest = parts[i + 1:]
                break
        if final:
            self.ended = True
            acted = [e for e in self.events + out if e.type in ("act", "undo", "confirm", "ask", "cancel")]
            if not acted and not self.withdrawn and self.text.strip():
                out.append(Event("chat", t, label=self.text, args={"text": self.text}))
        self.events += out
        return out

    async def end(self, t: float) -> list[Event]:
        return await self.tick(t, final=True)

    # ---------------------------------------------------------------- policy
    def _confident(self, p: float, margin: float) -> bool:
        return p >= self.policy.threshold and margin >= self.policy.margin

    def _policy(self, st: _Clause, clause: str, d: Decision, closed: bool, final: bool, t: float) -> list[Event]:
        a, p, margin = Decision.top(d.action)
        if a == "none" or not a:
            return self._revise(st, None, t) if st.event and closed else []
        if a == "plan_meeting" and not final:
            return []  # a draft references the complete proposal, never partial dictation
        if a == "plan_trip" and not _TRIP_WORDS.search(clause):
            if not final:
                return []
            self.pending = Pending(a, clause, kind="trip_intent")
            question = "Do you mean a trip plan for this visit?" if re.search(r"\bvisit\b", clause, re.I) else "Do you want me to plan a trip?"
            return [self._ask(t, a, clause, question, p, d, keep_pending=True)]
        if not self._confident(p, margin):
            if not final:
                return []
            ranked = sorted(d.action.items(), key=lambda kv: -kv[1])
            options = [_ACTION_LABEL[n] for n, _ in ranked if n in _ACTION_LABEL][:2]
            q = f"Should I {options[0]} or {options[1]}?" if len(options) == 2 else "What should I do?"
            return [self._ask(t, a, clause, q, p, d)]
        action = BY_NAME[a]
        args, question, match = self._args(a, clause, d)
        if question:
            if final or (action.kind == "in_app" and closed):
                if match and match.candidates:
                    self.pending = Pending(a, clause, match.candidates)
                elif match and match.contact:
                    # The recipient is settled ("What should I say to Arif?"): the answer is dictation.
                    self.pending = Pending(a, clause, (), contact=match.contact)
                return [self._ask(t, a, clause, question, p, d, keep_pending=True)]
            return []
        if action.kind == "in_app":
            if action.name in FREE_TEXT_ARGS and not closed:
                return []  # "weather in Abu…" — a free-text argument is only complete when its clause is
            outcome = (a, tuple(sorted(args.items())))
            if st.outcome == outcome:
                return []
            evs = self._revise(st, outcome, t)
            ev = Event("act", t, action=a, args=args, label=_label(a, args), p=round(p, 4), clause=clause, source=d.source)
            st.event = ev
            return evs + [ev]
        if not final:
            return []  # outward and paid actions wait for the end of speech
        kind = "undo" if action.kind == "outward" else "confirm"
        return [Event(kind, t, action=a, args=args, label=_label(a, args), p=round(p, 4), clause=clause, source=d.source)]

    def _revise(self, st: _Clause, outcome: tuple | None, t: float) -> list[Event]:
        """The person changed their mind mid-sentence: withdraw what this clause already did."""
        evs: list[Event] = []
        if st.event:
            evs.append(Event("cancel", t, ref=st.event.id, action=st.event.action, label="revised", clause=st.text))
        st.outcome, st.event = outcome, None
        return evs

    def _ask(self, t: float, a: str, clause: str, question: str, p: float, d: Decision, keep_pending: bool = False) -> Event:
        if not (keep_pending and self.pending):
            self.pending = Pending(a, clause)
        return Event("ask", t, action=a, label=question, p=round(p, 4), clause=clause, source=d.source)

    def _cancel_all(self, t: float, raw: str) -> list[Event]:
        return [Event("cancel", t, label="cancelled", clause=raw, args={"all": True})]

    def _args(self, a: str, clause: str, d: Decision) -> tuple[dict, str, Match | None]:
        if a == "plan_meeting":
            contact = self.last_contact
            named = mentions(clause, self.contacts)
            if named:
                match = resolve(clause, self.contacts, strict_namesakes=self.policy.strict_namesakes)
                if match.status == "ask":
                    return {}, match.question, match
                contact = match.contact
            context = self.last_message if contact and contact.id == self.last_message_contact else ""
            return meeting_args(clause, context, contact.id if contact else "", contact.name if contact else ""), "", None
        parts = send_parts(clause, [k for c in self.contacts for k in c.keys]) if a == "send_message" else None
        recipient = parts.recipient if parts else clause
        if a == "open_screen":
            sc, sp, _ = Decision.top(d.screen)
            if sc in (NO_SCREEN, "") or sp < 0.5:
                return {}, "Which part of the app?", None
            return {"screen": SCREENS[sc], "name": sc}, "", None
        if a in ("open_chat", "send_message", "read_messages", "plan_trip"):
            last = LAST_CHAT.search(recipient)
            if last and self.contacts and not mentions(recipient, self.contacts):
                # "my last chat": the browser sends contacts most-recent first. Not a guess between names.
                self.last_contact = self.contacts[0]
                if a in ("read_messages", "plan_trip"):
                    args = {"contactId": self.contacts[0].id, "name": self.contacts[0].name}
                    return ({**args, "request": clause} if a == "plan_trip" else args), "", None
                return self._contact_args(a, clause, self.contacts[0], last.group("core"))
        if a == "compose_email":
            parts = email_parts(clause)
            return (parts, "", None) if parts["to"] or parts["body"] else ({}, "Who should the email go to?", None)
        if a in ("open_chat", "send_message"):
            pick, pp, _ = Decision.top(d.contact)
            model_pick = None if pick in (NOBODY, UNKNOWN, "") else pick
            m = resolve(clause, self.contacts, model_pick, pp, self.policy.contact_threshold, self.policy.strict_namesakes)
            pronoun = re.search(r"\b(them|him|her)\b", recipient, re.I)
            if m.status == "ask" and not m.candidates and not m.phrase and pronoun:
                if self.last_contact:
                    return self._contact_args(a, clause, self.last_contact, pronoun.group(1))
                if a == "send_message" and self.contacts:
                    # "reply him …" out of nowhere: the last interacted chat. The undo card names them, so a
                    # wrong guess is still cancellable — asking every time was the rigidity.
                    self.last_contact = self.contacts[0]
                    return self._contact_args(a, clause, self.contacts[0], pronoun.group(1))
            if m.status == "ask" and a == "send_message" and self.last_contact and REPLY.match(clause) \
                    and not mentions(recipient, self.contacts) and not recipient:
                # "…and reply with …" names nobody: the reply goes to the chat this turn opened or read.
                return self._contact_args(a, clause, self.last_contact, self.last_contact.name)
            if m.status == "ask":
                if a == "send_message" and REPLY.match(clause) and not m.candidates \
                        and not mentions(recipient, self.contacts) and not self.last_contact and not recipient:
                    # "reply with hello" out of nowhere: "hello" is the message, not a missing contact.
                    return {}, "Who should I send it to?", Match("ask", phrase=m.phrase)
                return {}, m.question, m
            self.last_contact = m.contact
            return self._contact_args(a, clause, m.contact, m.phrase)
        if a == "get_weather":
            c = city(clause)
            return ({"city": c}, "", None) if c else ({}, "Which city?", None)
        if a == "search_flights":
            r = flight_route(clause)
            return ({**r, "utterance": clause}, "", None) if r.get("to") else ({}, "Where are you flying to?", None)
        if a == "research_topic":
            tp = topic(clause)
            return ({"topic": tp}, "", None) if len(tp.split()) >= 1 else ({}, "What should I research?", None)
        if a in ("read_messages", "plan_trip"):
            # An optional person: only an exact name counts (reading or planning never guesses a near-name).
            exact = mentions(re.sub(r"(\w)['’]s\b", r"\1", clause), self.contacts)  # "Mazen's messages" → Mazen
            if exact:
                self.last_contact = exact[0][1]  # "read Arif's … and reply yes" answers Arif
                args = {"contactId": exact[0][1].id, "name": exact[0][1].name}
            elif a == "plan_trip" and self.last_contact:
                # "reply to Arif that I'm free and also plan the trip" plans it with Arif. Paid, so it
                # still stops at a Confirm card naming them — nothing is filed silently.
                args = {"contactId": self.last_contact.id, "name": self.last_contact.name}
            else:
                args = {}
            if not exact and a == "read_messages" and re.search(r"\b(them|him|her)\b", clause, re.I) and self.last_contact:
                args = {"contactId": self.last_contact.id, "name": self.last_contact.name}
            return ({**args, "request": clause} if a == "plan_trip" else args), "", None
        if a == "check_notifications":
            return {}, "", None
        if a in ("generate_image", "generate_video"):
            pr = prompt(clause)
            return ({"prompt": pr}, "", None) if pr else ({}, "What should it show?", None)
        return {}, "What should I do?", None

    def _contact_args(self, a: str, clause: str, contact: Contact, phrase: str) -> tuple[dict, str, Match | None]:
        args = {"contactId": contact.id, "name": contact.name}
        if a == "send_message":
            parts = send_parts(clause, [k for c in self.contacts for k in c.keys])
            text = message_text(clause, parts.recipient if parts else phrase)
            # A confirmed near-miss surname belongs to the recipient, not the message ("Arif Kahn" → yes).
            surname = norm(contact.name).split()[1:]
            if parts and norm(parts.recipient) == contact.keys[-1] and surname and text.split() \
                    and similar(norm(text.split()[0]), surname[0]):
                text = " ".join(text.split()[1:])
            if not text:
                return {}, f"What should I say to {contact.name}?", Match("ask", contact=contact, phrase=phrase)
            args["text"] = text[0].upper() + text[1:]
            self.last_message = args["text"]
            self.last_message_contact = contact.id
        return args, "", None


# A turn that is only a command verb ("Open." — the speaker paused, end of speech cut the sentence): ask for the rest
# and carry the verb into the next turn, instead of sending a bare word to the chat model.
DANGLING = re.compile(r"^(?:please\s+|can you\s+|could you\s+)*(?P<verb>open(?:ed)?|show(?: me)?|go to|switch to|take me to|pull up|"
                       r"bring up|launch|check|read(?: me)?|send|sent|text|message|tell|told|(?:reply(?: to)?|replied)|write(?: to)?|wrote(?: to)?|e-?mail|search(?: for)?|"
                       r"find|plan)(?:\s+(?:the|my|a|an|me|to|an e-?mail|a message))*$", re.I)
CARRY_S = 20.0


def _dangling_question(verb: str) -> str:
    v = {"opened": "open", "replied": "reply", "told": "tell", "sent": "send"}.get(verb.lower(), verb.lower())
    if v in ("send", "sent", "text", "message", "tell", "told") or v.startswith(("reply", "write", "wrote")):
        return "To whom, and what should I say?"
    if v in ("email", "e-mail", "emailed"):
        return "Who should the email go to?"
    if v.startswith(("search", "find")):
        return "What should I look for?"
    return f"{verb.split()[0].capitalize()} what?"


class Conversation:
    """Utterances in a row. Holds the open question so "yes" or "Sara Ali" can answer it, and a dangling verb so
    "Open." … "my last chat" becomes one command."""

    # A chat opened or read recently stays the reply target for a following bare "reply with …" ("open my last
    # chat" … "reply with I'm on my way"). Only a bare reply inherits it — a spoken name always wins — and it
    # expires, so an old conversation never receives a new dictation.
    LAST_CONTACT_S = 60.0

    def __init__(self, decider: Decider, contacts: list[Contact], policy: Policy | None = None) -> None:
        self.decider, self.contacts, self.policy = decider, contacts, policy or Policy()
        self.pending: Pending | None = None
        self.carry, self.carry_at = "", 0.0
        self.last_contact: Contact | None = None
        self.last_contact_at = 0.0
        self.last_message = ""
        self.last_message_contact = ""
        self.engine = self._new()

    def _new(self) -> IntentEngine:
        eng = IntentEngine(self.decider, self.contacts, self.policy)
        if self.last_contact and time.monotonic() - self.last_contact_at < self.LAST_CONTACT_S:
            eng.last_contact = self.last_contact
            eng.last_message = self.last_message
            eng.last_message_contact = self.last_message_contact
        return eng

    def begin(self) -> IntentEngine:
        self._remember(self.engine)
        self.engine = self._new()
        return self.engine

    def _remember(self, eng: IntentEngine) -> None:
        if eng.last_contact:
            self.last_contact, self.last_contact_at = eng.last_contact, time.monotonic()
            self.last_message = eng.last_message
            self.last_message_contact = eng.last_message_contact

    async def tick(self, t: float) -> list[Event]:
        """While an answer to a question is being spoken, nothing runs early: it is decided at the end."""
        return [] if self.pending or self.carry else await self.engine.tick(t)

    async def finish(self, t: float) -> list[Event]:
        """End of speech: answer an open question if this utterance does, otherwise decide it as a new command."""
        text = self.engine.text
        carry, self.carry = self.carry, ""
        if carry and time.monotonic() - self.carry_at < CARRY_S and text.strip():
            events = await self._run(f"{carry} {text}", t)  # "Open" + "my last chat"
            self.engine.events += events
            self.engine.ended = True
            return events
        m = DANGLING.match(text.strip().strip(".!?,"))
        if m and not self.pending:
            self.carry, self.carry_at = text.strip().strip(".!?,"), time.monotonic()
            ev = Event("ask", t, label=_dangling_question(m.group("verb")), clause=text)
            self.engine.events.append(ev)
            self.engine.ended = True
            return [ev]
        pending, self.pending = self.pending, None
        if pending:
            answered = self._answer(pending, text, t)
            if answered is not None:
                events = answered
                if pending.rest and not any(e.type == "ask" for e in events):
                    events += await self._run(" and ".join(pending.rest), t)
                self.engine.events += events
                self.engine.ended = True
                return events
        events = await self.engine.end(t)
        self._remember(self.engine)
        self.pending = self.engine.pending
        return events

    async def _run(self, text: str, t: float) -> list[Event]:
        eng = self._new()
        eng.partial(text, t)
        evs = await eng.end(t)
        self.pending = eng.pending
        self._remember(eng)
        return evs

    def _answer(self, pending: Pending, text: str, t: float) -> list[Event] | None:
        """Classify an answer to an open question instead of parroting instructions: a name or "my last chat"
        settles the recipient; words to a settled recipient are dictation ("What should I say?" → the message).
        Anything that is a command of its own (a send head with words, another action) runs as a new command."""
        bare = text.strip().strip(".!?, ")
        if pending.kind in ("trip_intent", "calendar_offer"):
            if NO.match(bare):
                return [Event("cancel", t, action=pending.action, label="Cancelled", clause=pending.clause)]
            if command_head(bare):
                return None  # a different app request starts fresh, including an explicit trip command
            if pending.kind == "calendar_offer" and YES.match(bare):
                args = {"screen": "calendar", "name": "calendar"}
                return [Event("act", t, action="open_screen", args=args, label=_label("open_screen", args),
                              clause=pending.clause, source="answer")]
            if pending.kind == "trip_intent":
                if re.search(r"\b(?:appointment|meeting|calendar)\b", bare, re.I) and not _TRIP_WORDS.search(bare):
                    self.pending = Pending("open_screen", pending.clause, rest=pending.rest, kind="calendar_offer")
                    return [Event("ask", t, action="open_screen", label="Would you like me to open Calendar for this visit?",
                                  clause=pending.clause, source="answer")]
                if YES.match(bare) or _TRIP_WORDS.search(bare):
                    request = re.sub(r"\bplan\b", "plan a trip", pending.clause, count=1, flags=re.I)
                    if _TRIP_WORDS.search(bare):
                        request += f". {bare}"
                    args = {"request": request}
                    if self.last_contact:
                        args.update(contactId=self.last_contact.id, name=self.last_contact.name)
                    return [Event("confirm", t, action="plan_trip", args=args, label=_label("plan_trip", args),
                                  clause=pending.clause, source="answer")]
            self.pending = pending
            question = "Do you want me to plan a trip?" if pending.kind == "trip_intent" else "Should I open Calendar?"
            return [Event("ask", t, action=pending.action, label=question, clause=pending.clause, source="answer")]
        if NO.match(text) and not mentions(text, list(pending.candidates)):
            return [Event("cancel", t, label="cancelled", args={"all": True}, clause=text)]
        if pending.contact is not None and pending.action == "send_message" and bare and not command_head(bare):
            # The question was what to say, not whom to send to. Names and last-chat words are dictation here too.
            name = pending.contact.name
            body = bare[0].upper() + bare[1:]
            self.last_message = body
            self.last_message_contact = pending.contact.id
            self.last_contact, self.last_contact_at = pending.contact, time.monotonic()
            args = {"contactId": pending.contact.id, "name": name, "text": body}
            return [Event("undo", t, action="send_message", args=args, label=f"Sending to {name}: “{body}”",
                          p=1.0, clause=pending.clause, source="answer")]
        chosen: Contact | None = None
        if pending.candidates:
            named = mentions(text, list(pending.candidates))
            exact_full = [c for _, c, ph in named if norm(ph) == norm(c.name)] or [c for _, c, _ in named]
            if len({c.id for c in exact_full}) == 1:
                chosen = exact_full[0]
            elif YES.match(text) and len(pending.candidates) == 1:
                chosen = pending.candidates[0]
        if not chosen and pending.action in ("open_chat", "send_message", "read_messages", "plan_trip") and self.contacts \
                and not SEND_HEAD.match(bare):
            if LAST_CHAT.search(bare) and len(bare.split()) <= 4 and not mentions(bare, self.contacts):
                chosen = self.contacts[0]  # "my last chat / message" answers "to who?"
            else:
                simple = re.sub(r"^(?:please\s+)+", "", bare, flags=re.I).strip()
                exact = mentions(simple, self.contacts)
                if exact and norm(simple) in (norm(exact[0][1].name), norm(exact[0][1].name.split()[0])):
                    chosen = exact[0][1]  # a bare "Arif" answers it; "tell Arif hi" runs as a new command
        if not chosen:
            if pending.action == "open_screen" and self.contacts and not SEND_HEAD.match(bare) \
                    and LAST_CHAT.search(bare) and len(bare.split()) <= 4 and not mentions(bare, self.contacts):
                # "Should I open an app or open a chat?" → "my last chat": a misheard "chat" ("shot")
                # still lands on the conversation instead of another lecture.
                self.last_contact, self.last_contact_at = self.contacts[0], time.monotonic()
                args = {"contactId": self.contacts[0].id, "name": self.contacts[0].name}
                return [Event("act", t, action="open_chat", args=args, label=_label("open_chat", args),
                              p=1.0, clause=pending.clause, source="answer")]
            return None  # not an answer: treat it as a new command
        self.last_contact, self.last_contact_at = chosen, time.monotonic()
        eng = self._new()
        orig_phrase = next((w for w in pending.clause.split() if any(norm(w) in c.keys for c in self.contacts)), "")
        clause = pending.clause
        if pending.action == "plan_meeting":
            context = self.last_message if self.last_message_contact == chosen.id else ""
            args, q = meeting_args(clause, context, chosen.id, chosen.name), ""
        else:
            args, q, _ = eng._contact_args(pending.action, clause, chosen, orig_phrase or chosen.keys[-1])
        if q and pending.action == "send_message":
            # The original words named someone else ("Sarah"); cut the message after the first name-like word.
            words = clause.split()
            for i, w in enumerate(words[1:], 1):
                if w[:1].isupper():
                    args, q, _ = eng._contact_args(pending.action, " ".join(words[:i] + [chosen.name] + words[i + 1:]), chosen, chosen.name)
                    break
        if q:
            self.pending = Pending(pending.action, clause, (chosen,), pending.rest, contact=chosen)
            return [Event("ask", t, action=pending.action, label=q, clause=clause)]
        if pending.action == "send_message":
            self.last_message = args["text"]
            self.last_message_contact = chosen.id
        kind = "act" if BY_NAME[pending.action].kind == "in_app" else "undo"
        return [Event(kind, t, action=pending.action, args=args, label=_label(pending.action, args), p=1.0, clause=clause, source="answer")]
