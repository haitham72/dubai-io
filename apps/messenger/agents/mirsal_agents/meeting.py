"""Extract a reviewable meeting draft, without inventing a time, venue branch or attendees."""
import re
from datetime import datetime, timedelta, timezone


def meeting_args(request: str, context: str = "", contact_id: str = "", name: str = "", today=None) -> dict[str, str]:
    today = today or datetime.now(timezone(timedelta(hours=4))).date()
    text = f"{context}. {request}"
    date = ""
    day = re.search(r"\b(today|tomorrow|day after tomorrow)\b", request, re.I) or re.search(r"\b(today|tomorrow|day after tomorrow)\b", context, re.I)
    if day:
        offset = {"today": 0, "tomorrow": 1, "day after tomorrow": 2}[day.group(1).lower()]
        date = (today + timedelta(days=offset)).isoformat()
    explicit = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if explicit:
        try:
            date = datetime.strptime(explicit.group(1), "%Y-%m-%d").date().isoformat()
        except ValueError:
            pass
    # Preserve the spoken venue, not a guessed address or branch.
    venue = re.search(r"\b(?:at|in)\s+(?:at\s+|in\s+)?(.+?\b(?:restaurant|cafe|café|hotel))\b", text, re.I)
    location = venue.group(1).strip() if venue else ""
    clock = re.search(r"\b(?:at\s+)(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text, re.I)
    start = ""
    if clock and 1 <= int(clock.group(1)) <= 12 and int(clock.group(2) or 0) < 60:
        hour = int(clock.group(1)) % 12 + (12 if clock.group(3).lower() == "pm" else 0)
        start = f"{hour:02}:{int(clock.group(2) or 0):02}"
    return {"request": request, "context": context, "contactId": contact_id, "name": name,
            "title": f"Meeting with {name}" if name else "Meeting", "date": date, "startTime": start,
            "endTime": "", "location": location}
