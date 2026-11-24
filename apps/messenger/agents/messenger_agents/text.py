"""Deterministic language rules: clause splitting, self-corrections and argument extraction.

The decision model chooses *which* action from a closed list; it cannot return free text. Free-text arguments (message
body, city, topic, prompt) therefore come from these rules, applied to the clause the decision was about.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

COMMAND_VERBS = (
    "open", "opened", "show", "go", "send", "sent", "text", "texted", "message", "tell", "told", "let", "ask", "write",
    "wrote", "check", "what's", "whats", "what", "how's", "hows", "how", "search", "find", "look", "book", "research",
    "compare", "plan", "generate", "create", "make", "draw", "get", "pull", "bring", "switch", "reply", "replied",
    "email", "emailed", "is", "will", "do", "can", "could", "please",
)
# Note: the separator's trailing space lives INSIDE each alternative — a shared trailing `\s+` would make the
# period branch need two spaces ("tomorrow.  And") and single-space sentence breaks would never split.
_SPLIT = re.compile(r"\s*(?:,?\s*\band then\b\s+|,?\s*\bthen\b\s+|,?\s*\bafter that\b\s+|;\s*|,?\s*\band\b\s+|\.\s+)", re.I)
# The router: "…and also / but also / also …" is message dictation ("…and also bring chips" stays one message)
# UNLESS what follows is one of the preset command heads ("…and also plan the trip" is a message plus a plan).
# The sentence is re-assessed at each of these joints instead of guessed once.
ROUTER_HEADS = ("open", "opened", "show", "go", "read", "reply", "replied", "send", "sent", "text", "texted", "message",
                "tell", "told", "ask", "write", "wrote", "email", "emailed", "e-mail", "search", "find", "research",
                "compare", "plan", "generate", "create", "make", "check")
_ROUTER = re.compile(r",?\s*\bbut also\b\s+|(?:,?\s*\band also\b|,\s*\balso\b|\s+also\b)\s+", re.I)
_JOINT_LEAD = re.compile(r"^(?:(?:and|then|also)\b\s+)+", re.I)
# A joint starts another app request only with an app command head. In particular, "bring chips", "get milk"
# and "make sandwiches" are dictation; "bring up mail" and "make an image" are commands.
_COMMAND_HEAD = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)*(?:"
    r"open(?:ed)?|show|go to|switch to|take me to|pull up|bring up|launch|read|catch me up|"
    r"send|sent|text(?:ed)?|message(?:d)?|tell|told|let|ask|write|wrote|reply|replied|e-?mail(?:ed)?|"
    r"check|search|find|look into|research|compare|plan|organi[sz]e|set up|generate|create|draw|"
    r"make\s+(?:(?:me\s+)?(?:an?\s+|the\s+|some\s+)?(?:image|picture|photo|video|clip|reel|animation|something|plan))|"
    r"book\s+(?:an?\s+)?(?:flight|ticket)|get\s+(?:(?:my|the)\s+)?(?:weather|forecast|messages|notifications)|"
    r"(?:what'?s|how'?s)\s+(?:the\s+)?(?:weather|forecast|temperature|new))\b", re.I,
)


def command_head(text: str) -> bool:
    return bool(_COMMAND_HEAD.match(text.strip()))
# A self-correction: "Sara, no, Omar" · "mail, actually calendar" · "Lina — sorry, Lena" · "scratch that, ..."
CORRECTION = re.compile(
    r"(?:^|[\s,.;—–-]+)(?:no,?\s*wait|no,|no no|nope|actually|sorry|i mean|i meant|scratch that|make (?:that|it)|wait,|not\s+\w+,)\s*,?\s*",
    re.I,
)
CANCEL = re.compile(r"^\s*(?:cancel|never ?mind|stop|forget (?:it|that)|don'?t send|undo)\b", re.I)
YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|correct|right|exactly|that'?s (?:it|right|her|him)|do it|go ahead|confirm|sure|ok(?:ay)?)\b", re.I)
NO = re.compile(r"^\s*(?:no|nope|nah|wrong|cancel)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s'’]", " ", s.lower().replace("’", "'"))).strip()


def words(s: str) -> list[str]:
    return norm(s).split()


def split_clauses(text: str) -> list[str]:
    """Split on "and/then/after that" only when a command verb follows, so "bread and milk" stays one message.

    "and also / but also / also" go through the router instead: they split only when a preset command head
    follows ("…and also plan the trip" → message + plan), so dictation like "…and also bring chips" stays whole."""
    cands = [(m, False) for m in _SPLIT.finditer(text)] + [(m, True) for m in _ROUTER.finditer(text)]
    cands.sort(key=lambda x: (x[0].start(), -x[0].end()))
    parts: list[str] = []
    last = 0
    for m, strict in cands:
        if m.start() <= last:
            continue
        tail = text[m.end():]
        lead = _JOINT_LEAD.match(tail)
        start = m.end() + (lead.end() if lead else 0)
        if not command_head(text[start:]):
            continue
        if m.start() > last:
            parts.append(text[last:m.start()])
            last = start
    parts.append(text[last:])
    result = []
    for part in parts:
        # A trailing imperative after a meeting proposal is an app instruction even
        # without "and". Keep ordinary "we can plan for it" and quoted words as dictation.
        match = re.search(r"\s+(plan for (?:it|this)|plan this (?:meeting|event))\s*$", part, re.I)
        before = part[:match.start()] if match else ""
        if match and SEND_HEAD.match(before) and re.search(r"\b(?:meet|meeting|dinner|lunch|restaurant|event)\b", before, re.I) \
                and not re.search(r"\b(?:can|could|will|should|to|not|don't|do not|we|i|you)\s*$", before, re.I) \
                and before.count('"') % 2 == 0:
            result.extend([before, match.group(1)])
        else:
            result.append(part)
    return [p.strip(" ,.") for p in result if p.strip(" ,.")]


@dataclass
class Corrected:
    text: str        # the clause with the corrected slot replaced (what the person meant)
    corrected: bool  # a self-correction happened (the trace records the cancelled reading)
    before: str = ""
    after: str = ""


def apply_correction(clause: str, slot_words: set[str]) -> Corrected:
    """Resolve "X, no, Y". A short replacement (≤3 words) swaps the last slot word before the marker (a name, screen or
    city); a long one replaces the whole clause (the person restarted the command)."""
    m = None
    for m in CORRECTION.finditer(clause):
        pass
    if not m or m.start() == 0:
        return Corrected(clause, False)
    before, after = clause[:m.start()].strip(" ,"), clause[m.end():].strip(" ,.")
    if not after:
        return Corrected(before, False)
    if CANCEL.match(after):
        return Corrected(before, True, before, after)  # "…, actually never mind": the engine withdraws the clause
    after_head = re.split(r",|\bthat\b|\bsaying\b", after, maxsplit=1)
    replacement, tail = after_head[0].strip(), (after[len(after_head[0]):].strip(" ,") if len(after_head) > 1 else "")
    rw = words(replacement)
    if rw and rw[0] in COMMAND_VERBS and rw[0] not in ("message",):
        return Corrected(after, True, before, after)  # the person restarted the command
    bw = before.split()
    if not tail:
        # "research electric cars, I mean electric motorbikes…" · "image of a red Ferrari, no, a blue Lamborghini":
        # splice the replacement in where its first word last appears before the marker (keeping the command verb).
        lead = rw[0] if rw else ""
        hits = [i for i, w in enumerate(bw) if i > 0 and norm(w) == lead]
        if hits:
            return Corrected(" ".join(bw[:hits[-1]] + [after]), True, before, after)
        if len(rw) > 3:
            return Corrected(f"{bw[0]} {after}" if bw else after, True, before, after)
    for i in range(len(bw) - 1, -1, -1):
        if norm(bw[i]) in slot_words or (i and norm(f"{bw[i-1]} {bw[i]}") in slot_words):
            j = i - 1 if i and norm(f"{bw[i-1]} {bw[i]}") in slot_words else i
            fixed = " ".join(bw[:j] + [replacement] + bw[i + 1:])
            return Corrected(f"{fixed} {tail}".strip(), True, before, after)
    # No known slot word before the marker: the replacement still wins for the last word (e.g. a city).
    if bw and len(bw) > 1 and rw and norm(bw[-2]) == rw[0]:
        return Corrected(" ".join(bw[:-2] + [replacement]) + (f" {tail}" if tail else ""), True, before, after)
    if bw:
        return Corrected(" ".join(bw[:-1] + [replacement]) + (f" {tail}" if tail else ""), True, before, after)
    return Corrected(after, True, before, after)


# Speech arrives in past tense too ("opened …", "replied …"): the heads match both forms.
_SEND_HEAD = r"(?:please\s+)?(?:can you\s+|could you\s+)?(?:send|sent|text(?:ed)?|message(?:d)?|tell|told|write(?: to)?|wrote(?: to)?|whatsapp|(?:reply(?: to)?|replied)|let)"
# "my last chat", "the latest conversation": the contact list arrives most-recent first, so this is contacts[0].
LAST_CHAT = re.compile(r"\b(?:my\s+|the\s+)?(?P<core>(?:last|latest|most recent|recent)\s+(?:chat|conversation|message|person))\b", re.I)
EMAIL_HEAD = re.compile(r"^(?:please\s+|can you\s+|could you\s+)*(?:(?:send|write|draft|compose)\s+(?:an?\s+)?e-?mail\b|e-?mail(?:ed)?\s+(?!app\b|inbox\b))", re.I)


def email_parts(clause: str) -> dict:
    """'email Rashid that I'm late' · 'send an email to r.khalfan@nadi.ae saying the dates changed' → to, subject, body."""
    s = clause.strip().rstrip(".!")
    addr = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", s)
    to = addr.group(0) if addr else ""
    if not to:
        m = re.search(r"\b(?:e-?mail|to)\s+(?!an?\b|the\b|to\b)([A-Za-z][\w'’-]*(?:\s+[A-Z][\w'’-]*)?)", s)
        to = m.group(1) if m else ""
    m = re.search(r"\b(?:that|saying|about|to say)\s+(?P<b>.+)$", s, re.I)
    body = m.group("b").strip() if m else ""
    if body:
        body = body[0].upper() + body[1:]
    subject = " ".join(body.split()[:6]).rstrip(",;:") if body else ""
    return {"to": to, "subject": subject, "body": body}


SEND_HEAD = re.compile(r"^(?:please\s+|can you\s+|could you\s+)*(?:send|sent|text(?:ed)?|message(?:d)?|tell|told|write to|wrote to|(?:reply(?: to)?|replied)|whatsapp|let (?:\w+ ){1,3}know|ask)\b", re.I)
# A bare "reply …" heads a message to someone already in context ("open the last chat and reply with …",
# "read my last message and reply yes"). With no words after it the turn is asking what to say, not chatting.
REPLY = re.compile(r"^(?:please\s+|can you\s+|could you\s+)*repl(?:y|ied)\b", re.I)
# An unfinished reply: the head with an optional recipient and a dangling "with/saying" — the person is about to
# dictate ("reply", "reply with", "reply to Arif", "reply to the last chat saying"). The turn must stay open for it.
REPLY_OPEN = re.compile(r"^(?:please\s+|can you\s+|could you\s+)*repl(?:y|ied)(?:\s+to\s+\S[^,.;]*?)?(?:\s+(?:with|saying|that))?\s*$", re.I)


@dataclass
class SendParts:
    recipient: str
    body: str
    verb: str


_SEND_PARTS_HEAD = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)*(?P<verb>send|sent|text(?:ed)?|message(?:d)?|tell|told|"
    r"write|wrote|whatsapp|reply|replied|let|ask)\b[\s,:]*(?P<tail>.*)$", re.I,
)
_BODY_LEAD = re.compile(
    r"^(?:and\s+)?(?:(?:a\s+)?(?:message|text|note)\s+)?(?:know\s+)?"
    r"(?:say(?:ing)?|that|to say|with)\b[\s,:]*", re.I,
)


def send_parts(clause: str, names: list[str] | tuple[str, ...] = ()) -> SendParts | None:
    """Read the recipient BEFORE the dictation. Contact names in the body are never recipients.

    Known names only match at the start of the recipient field; an explicit pronoun or last-chat phrase wins
    there too. Unknown recipients are kept for the exact-name guard to ask about, never guessed from the body.
    """
    if EMAIL_HEAD.match(clause):
        return None
    m = _SEND_PARTS_HEAD.match(clause.strip().rstrip(".!"))
    if not m:
        return None
    verb, tail = m.group("verb").lower(), m.group("tail").strip()
    reply = verb in ("reply", "replied")
    # "send a message to X" / "write to X" / "reply to X".
    tail = re.sub(r"^(?:an?\s+)?(?:message|text|note)\s+to\s+", "to ", tail, flags=re.I)
    explicit_to = bool(re.match(r"^to\b", tail, re.I))
    if explicit_to:
        tail = re.sub(r"^to\b\s*", "", tail, flags=re.I)
    if verb in ("write", "wrote") and not explicit_to:
        return None
    if verb == "let" and not re.search(r"\bknow\b", tail, re.I):
        return None
    recipient, body = "", tail
    target = re.match(r"^(?:him|her|them)\b", tail, re.I) or LAST_CHAT.match(tail)
    if target:
        recipient, body = target.group(0), tail[target.end():].strip(" ,:")
    else:
        for name in sorted(set(names), key=lambda n: -len(n)):
            target = re.match(rf"^(?:the\s+)?{re.escape(name)}\b(?:\s+(?:group|chat))?", tail, re.I)
            if target:
                recipient, body = target.group(0), tail[target.end():].strip(" ,:")
                break
        if not recipient:
            trailing = re.match(r"^(?P<body>.+?)\s+to\s+(?P<recipient>[^,.;]+)$", tail, re.I)
            if trailing and not explicit_to and verb in ("send", "sent", "text", "texted", "message", "messaged"):
                recipient, body = trailing.group("recipient"), trailing.group("body")
            elif not reply or explicit_to:
                target = re.match(r"^(?:the\s+)?[^\s,:]+", tail)
                if target:
                    recipient, body = target.group(0), tail[target.end():].strip(" ,:")
    if verb == "let":
        body = re.sub(r"^know\b\s*", "", body, flags=re.I)
    body = _BODY_LEAD.sub("", body).strip(" ,\"'“”")
    if verb in ("ask", "tell", "told"):
        body = re.sub(r"^to\s+", "", body, flags=re.I)
    if re.fullmatch(r"(?:a\s+)?(?:message|text|note|something|with|saying|that)", body, re.I):
        body = ""
    return SendParts(recipient, body, verb)


def message_text(clause: str, contact_phrase: str | None) -> str:
    """Extract only dictation, including replies with an explicit pronoun and unfinished send heads."""
    parts = send_parts(clause, [contact_phrase] if contact_phrase else [])
    if not parts:
        return ""
    if parts.verb == "ask":
        m = re.match(r"^(?:if|whether)\s+(?:he|she|they)(?:'s|\s+is|\s+are|'re)\s+(.+?)[?.!]*$", parts.body, re.I)
        if m:
            return f"Are you {m.group(1)}?"
        m = re.match(r"^(?:if|whether)\s+(?:he|she|they)\s+(.+?)[?.!]*$", parts.body, re.I)
        if m:
            return f"Do you {m.group(1)}?"
    return parts.body


def city(clause: str) -> str:
    s = clause.strip().rstrip("?.!")
    m = re.search(r"\b(?:in|for|at|of)\s+([A-Za-z][A-Za-z .'-]*?)(?:\s+(?:today|tomorrow|tonight|this week|this weekend|now|right now|please|like))*$", s, re.I)
    if m:
        return m.group(1).strip()
    m = re.match(r"^(?:what's |whats |how's |check )?(?:the )?([A-Z][A-Za-z .'-]+?)\s+(?:weather|forecast|temperature)\b", s)
    return m.group(1).strip() if m else ""


def flight_route(clause: str) -> dict:
    s = clause.strip().rstrip("?.!")
    out: dict = {}
    m = re.search(r"\bfrom\s+([A-Za-z][A-Za-z .'-]*?)(?=\s+to\b|\s+on\b|\s+next\b|\s+tomorrow\b|\s+this\b|$)", s, re.I)
    if m:
        out["from"] = m.group(1).strip()
    m = re.search(r"\bto\s+([A-Za-z][A-Za-z .'-]*?)(?=\s+from\b|\s+on\b|\s+next\b|\s+tomorrow\b|\s+this\b|\s+for\b|\s+in\b|$)", s, re.I)
    if m:
        out["to"] = m.group(1).strip()
    m = re.search(r"\b(tomorrow|tonight|next \w+|this \w+|on \w+(?: \d+\w*)?)\b", s, re.I)
    if m:
        out["when"] = m.group(1)
    return out


def strip_lead(clause: str, lead: str) -> str:
    return re.sub(lead, "", clause.strip().rstrip("?.!"), count=1, flags=re.I).strip(" ,:")


def topic(clause: str) -> str:
    return strip_lead(clause, r"^(?:please\s+|can you\s+|could you\s+)*(?:do (?:a |some )?(?:deep )?research on|research|look into|find out about|what's the latest on|whats the latest on|dig into|deep dive into|compare|give me a brief on)\s+(?:the\s+)?")


def prompt(clause: str) -> str:
    return strip_lead(clause, r"^(?:please\s+|can you\s+|could you\s+)*(?:generate|create|make|draw|render|produce)\s+(?:me\s+)?(?:an?\s+|the\s+|some\s+)?(?:\d+[- ]second\s+)?(?:short\s+)?(?:image|picture|photo|illustration|video|clip|reel|drawing)?s?\s*(?:of|showing|about|with|for)?\s*")
