"""@messenger skills inside a chat. Each reads the last 5–10 messages as context (fenced as data) and returns a short,
typed result the app renders as a faint "AI replied" message.

  fact_check   "@messenger is this true" — web search + a model verdict with sources (like asking Grok on X)
  image_ideas  "@messenger create image about this" — three distinct prompts drawn from the conversation
  stickers     "@messenger create sticker of this" — a pack from the stickers folder (one sub-folder per pack)
  plan         "@messenger setup plan for this" — leave in the HR portal (demo connector), flights query, budget in the
               local currency, a group with the people who mentioned it, calendar reminders

Offline (no AGENTS_LIVE=1 or no keys) every skill still answers from rules and labelled demo data.
"""

# Split into messenger_agents/skills/ (base, factcheck, image_ideas, stickers,
# nadi, planner); this module re-exports every public name for compatibility.
from .skills.base import (CHAT_RULE, CONTEXT_MAX, Msg, fence)
from .skills.factcheck import (APP_PATH, DATA_URL, FACT_SCHEMA, FactChecker, MAX_PHOTOS, MAX_PHOTO_BYTES, PHOTO_SCHEMA, PHOTO_TYPES, photo_inputs)
from .skills.image_ideas import (IDEAS_SCHEMA, STYLES, image_ideas, subject_from)
from .skills.look import (LOOK_SCHEMA, look)
from .skills.stickers import (STICKER_EXT, Stickers)
from .skills.planner import (DAY_INDEX, DAY_MONTH, DEST_STOP, FX_FALLBACK, IATA_PLACES, ISO_DAY, ISO_RANGE, JOIN_PAT, LEAVE_WORDS, MONTHS, MONTH_WORD, NAME_STOP, Planner, RELATIVE_DAY, STOPWORDS, TO_PLACE, UAE_HOLIDAYS, WEEKDAYS, WITH_PAT, _d, _join, _parse_iso, best_leave, companions, extract_trip, fixed_leave, fx_rate, mentioned_names, relative_start, request_dates, request_place, resolve_request_companions, start_date, unknown_destination)

__all__ = ["CHAT_RULE", "CONTEXT_MAX", "Msg", "fence", "APP_PATH", "DATA_URL", "FACT_SCHEMA", "FactChecker", "MAX_PHOTOS", "MAX_PHOTO_BYTES", "PHOTO_SCHEMA", "PHOTO_TYPES", "photo_inputs", "IDEAS_SCHEMA", "STYLES", "image_ideas", "subject_from", "LOOK_SCHEMA", "look", "STICKER_EXT", "Stickers", "DAY_INDEX", "DAY_MONTH", "DEST_STOP", "FX_FALLBACK", "IATA_PLACES", "ISO_DAY", "ISO_RANGE", "JOIN_PAT", "LEAVE_WORDS", "MONTHS", "MONTH_WORD", "NAME_STOP", "Planner", "RELATIVE_DAY", "STOPWORDS", "TO_PLACE", "UAE_HOLIDAYS", "WEEKDAYS", "WITH_PAT", "_d", "_join", "_parse_iso", "best_leave", "companions", "extract_trip", "fixed_leave", "fx_rate", "mentioned_names", "relative_start", "request_dates", "request_place", "resolve_request_companions", "start_date", "unknown_destination"]
