"""Trip planner: leave/dates/places parsing + the Planner skill."""
from __future__ import annotations

import datetime as dt
import difflib
import json
import random
import re
import time

import httpx2 as httpx  # ships with the openai SDK

from ..contacts import Contact
from ..store import Store
from .base import CONTEXT_MAX, Msg, fence
# ------------------------------------------------------------------ trip plan
PLACES: dict[str, dict] = {
    "egypt": {"city": "Cairo", "iata": "CAI", "currency": "EGP", "subject": "the pyramids of Giza at sunrise with camels", "daily_aed": 150,
              "climate": {1: (19, 9), 2: (21, 10), 3: (24, 12), 10: (29, 18), 11: (24, 14), 12: (20, 10)}},
    "cairo": {"alias": "egypt"}, "pyramids": {"alias": "egypt"},
    "alexandria": {"city": "Alexandria", "iata": "HBE", "currency": "EGP", "subject": "Alexandria's corniche and the Qaitbay Citadel",
                   "daily_aed": 150, "climate": {1: (18, 9), 4: (24, 14), 7: (30, 23), 10: (28, 19), 11: (24, 15), 12: (20, 11)},
                   "name": "Alexandria"},
    "turkey": {"city": "Istanbul", "iata": "IST", "currency": "TRY", "subject": "Istanbul skyline over the Bosphorus", "daily_aed": 250, "climate": {1: (9, 3)}},
    "istanbul": {"alias": "turkey"},
    "georgia": {"city": "Tbilisi", "iata": "TBS", "currency": "GEL", "subject": "Tbilisi old town and mountains", "daily_aed": 200, "climate": {1: (7, -1)}},
    "japan": {"city": "Tokyo", "iata": "HND", "currency": "JPY", "subject": "Tokyo streets at night", "daily_aed": 400, "climate": {1: (10, 1)}},
    "london": {"city": "London", "iata": "LHR", "currency": "GBP", "subject": "London on a crisp winter morning", "daily_aed": 450, "climate": {1: (8, 3)}},
    "uk": {"alias": "london"}, "britain": {"alias": "london"}, "england": {"alias": "london"},
    "france": {"city": "Paris", "iata": "CDG", "currency": "EUR", "subject": "Paris, the Eiffel Tower at dusk", "daily_aed": 450,
               "climate": {1: (7, 2), 12: (7, 2)}},
    "paris": {"alias": "france"},
    "italy": {"city": "Rome", "iata": "FCO", "currency": "EUR", "subject": "Rome, the Colosseum at golden hour", "daily_aed": 400,
              "climate": {1: (12, 4), 12: (12, 4)}},
    "rome": {"alias": "italy"}, "milan": {"alias": "italy"}, "venice": {"alias": "italy"},
    "spain": {"city": "Barcelona", "iata": "BCN", "currency": "EUR", "subject": "Barcelona, the Sagrada Familia", "daily_aed": 350,
              "climate": {1: (14, 7), 12: (14, 7)}},
    "barcelona": {"alias": "spain"}, "madrid": {"alias": "spain"},
    "greece": {"city": "Athens", "iata": "ATH", "currency": "EUR", "subject": "Santorini's white houses over the sea", "daily_aed": 300,
               "climate": {1: (14, 8), 12: (14, 8)}},
    "athens": {"alias": "greece"}, "santorini": {"alias": "greece"},
    "portugal": {"city": "Lisbon", "iata": "LIS", "currency": "EUR", "subject": "Lisbon trams over the river", "daily_aed": 300,
                 "climate": {1: (15, 9), 12: (15, 9)}},
    "lisbon": {"alias": "portugal"},
    "switzerland": {"city": "Zurich", "iata": "ZRH", "currency": "CHF", "subject": "the Swiss Alps over a lake village", "daily_aed": 600,
                    "climate": {1: (3, -2), 12: (3, -2)}},
    "zurich": {"alias": "switzerland"},
    "austria": {"city": "Vienna", "iata": "VIE", "currency": "EUR", "subject": "Vienna old town in light snow", "daily_aed": 380,
                "climate": {1: (4, -1), 12: (4, -1)}},
    "vienna": {"alias": "austria"},
    "germany": {"city": "Berlin", "iata": "BER", "currency": "EUR", "subject": "Berlin in winter lights", "daily_aed": 350,
                "climate": {1: (4, -1), 12: (4, -1)}},
    "berlin": {"alias": "germany"}, "munich": {"alias": "germany"},
    "netherlands": {"city": "Amsterdam", "iata": "AMS", "currency": "EUR", "subject": "Amsterdam canals at dusk", "daily_aed": 380,
                    "climate": {1: (6, 1), 12: (6, 1)}},
    "amsterdam": {"alias": "netherlands"}, "holland": {"alias": "netherlands"},
    "bali": {"city": "Denpasar", "iata": "DPS", "currency": "IDR", "subject": "Bali rice terraces and a villa pool", "daily_aed": 250, "climate": {1: (30, 24)}},
    "jordan": {"city": "Amman", "iata": "AMM", "currency": "JOD", "subject": "Petra treasury at dawn", "daily_aed": 250, "climate": {1: (13, 4)}},
    "morocco": {"city": "Marrakech", "iata": "RAK", "currency": "MAD", "subject": "Marrakech souk lanterns", "daily_aed": 220, "climate": {1: (19, 6)}},
    "kazakhstan": {"city": "Almaty", "iata": "ALA", "currency": "KZT", "subject": "Almaty overlooked by snowy mountains at dusk",
                   "daily_aed": 250, "climate": {1: (-3, -9), 5: (22, 11), 12: (-2, -8)}},
    "kazakhistan": {"alias": "kazakhstan"}, "kazakstan": {"alias": "kazakhstan"}, "almaty": {"alias": "kazakhstan"},
    "astana": {"city": "Astana", "iata": "NQZ", "currency": "KZT", "subject": "Astana skyline over the Ishim river", "daily_aed": 250,
               "climate": {1: (-10, -18), 5: (20, 8), 12: (-8, -16)}, "name": "Kazakhstan"},
    "denmark": {"city": "Copenhagen", "iata": "CPH", "currency": "DKK", "subject": "Copenhagen's colourful Nyhavn harbour", "daily_aed": 450,
                "climate": {1: (3, -1), 7: (22, 14), 12: (5, 1)}},
    "copenhagen": {"alias": "denmark"},
    "sweden": {"city": "Stockholm", "iata": "ARN", "currency": "SEK", "subject": "Stockholm old town on the water", "daily_aed": 420,
               "climate": {1: (0, -5), 7: (23, 14), 12: (2, -3)}},
    "stockholm": {"alias": "sweden"},
    "norway": {"city": "Oslo", "iata": "OSL", "currency": "NOK", "subject": "Norwegian fjords under the northern lights", "daily_aed": 500,
               "climate": {1: (-2, -7), 7: (22, 13), 12: (0, -5)}},
    "oslo": {"alias": "norway"},
    "finland": {"city": "Helsinki", "iata": "HEL", "currency": "EUR", "subject": "a snowy Lapland cabin under the northern lights", "daily_aed": 420,
                "climate": {1: (-2, -7), 7: (22, 14), 12: (0, -4)}},
    "helsinki": {"alias": "finland"}, "lapland": {"alias": "finland"},
    "iceland": {"city": "Reykjavik", "iata": "KEF", "currency": "ISK", "subject": "Iceland's waterfalls and black-sand beaches", "daily_aed": 550,
                "climate": {1: (3, -2), 7: (14, 9), 12: (3, -2)}},
    "reykjavik": {"alias": "iceland"},
    "czechia": {"city": "Prague", "iata": "PRG", "currency": "CZK", "subject": "Prague's Charles Bridge at dawn", "daily_aed": 300,
                "climate": {1: (1, -4), 7: (25, 14), 12: (3, -2)}, "name": "Czechia"},
    "czech": {"alias": "czechia"}, "prague": {"alias": "czechia"},
    "hungary": {"city": "Budapest", "iata": "BUD", "currency": "HUF", "subject": "Budapest's parliament on the Danube at night", "daily_aed": 280,
                "climate": {1: (2, -3), 7: (27, 16), 12: (4, -1)}},
    "budapest": {"alias": "hungary"},
    "poland": {"city": "Krakow", "iata": "KRK", "currency": "PLN", "subject": "Krakow's old market square", "daily_aed": 260,
               "climate": {1: (1, -5), 7: (24, 13), 12: (3, -3)}},
    "krakow": {"alias": "poland"}, "warsaw": {"alias": "poland"},
    "ireland": {"city": "Dublin", "iata": "DUB", "currency": "EUR", "subject": "the Cliffs of Moher on a green coast", "daily_aed": 420,
                "climate": {1: (8, 3), 7: (19, 11), 12: (8, 3)}},
    "dublin": {"alias": "ireland"},
    "scotland": {"city": "Edinburgh", "iata": "EDI", "currency": "GBP", "subject": "Edinburgh Castle above the old town", "daily_aed": 420,
                 "climate": {1: (7, 1), 7: (19, 11), 12: (7, 1)}},
    "edinburgh": {"alias": "scotland"},
    "thailand": {"city": "Bangkok", "iata": "BKK", "currency": "THB", "subject": "a Thai island beach with longtail boats", "daily_aed": 220,
                 "climate": {1: (32, 22), 7: (33, 26), 12: (31, 21)}},
    "bangkok": {"alias": "thailand"}, "phuket": {"alias": "thailand"},
    "maldives": {"city": "Malé", "iata": "MLE", "currency": "MVR", "subject": "Maldives overwater villas on a turquoise lagoon", "daily_aed": 700,
                 "climate": {1: (30, 26), 7: (30, 26), 12: (30, 26)}},
    "sri lanka": {"city": "Colombo", "iata": "CMB", "currency": "LKR", "subject": "Sri Lankan tea hills and a blue train", "daily_aed": 200,
                  "climate": {1: (31, 22), 7: (30, 25), 12: (30, 23)}},
    "colombo": {"alias": "sri lanka"},
    "india": {"city": "Delhi", "iata": "DEL", "currency": "INR", "subject": "the Taj Mahal at sunrise", "daily_aed": 180,
              "climate": {1: (20, 8), 7: (35, 27), 12: (23, 9)}},
    "delhi": {"alias": "india"}, "mumbai": {"alias": "india"},
    "singapore": {"city": "Singapore", "iata": "SIN", "currency": "SGD", "subject": "Marina Bay Sands and Gardens by the Bay at night", "daily_aed": 450,
                  "climate": {1: (30, 23), 7: (31, 25), 12: (30, 24)}},
    "malaysia": {"city": "Kuala Lumpur", "iata": "KUL", "currency": "MYR", "subject": "the Petronas Towers at dusk", "daily_aed": 220,
                 "climate": {1: (32, 23), 7: (32, 24), 12: (31, 23)}},
    "kuala lumpur": {"alias": "malaysia"},
    "vietnam": {"city": "Hanoi", "iata": "HAN", "currency": "VND", "subject": "Ha Long Bay's limestone islands", "daily_aed": 180,
                "climate": {1: (19, 14), 7: (33, 27), 12: (21, 15)}},
    "hanoi": {"alias": "vietnam"},
    "korea": {"city": "Seoul", "iata": "ICN", "currency": "KRW", "subject": "Seoul palace gates and city lights", "daily_aed": 380,
              "climate": {1: (2, -6), 7: (29, 22), 12: (4, -4)}, "name": "South Korea"},
    "seoul": {"alias": "korea"},
    "china": {"city": "Beijing", "iata": "PEK", "currency": "CNY", "subject": "the Great Wall winding over the hills", "daily_aed": 320,
              "climate": {1: (2, -9), 7: (31, 22), 12: (4, -7)}},
    "beijing": {"alias": "china"}, "shanghai": {"alias": "china"},
    "usa": {"city": "New York", "iata": "JFK", "currency": "USD", "subject": "the New York skyline at dusk", "daily_aed": 600,
            "climate": {1: (4, -3), 7: (29, 21), 12: (6, -1)}, "name": "the USA"},
    "new york": {"alias": "usa"}, "america": {"alias": "usa"},
    "canada": {"city": "Toronto", "iata": "YYZ", "currency": "CAD", "subject": "Toronto skyline over Lake Ontario", "daily_aed": 480,
               "climate": {1: (-1, -8), 7: (27, 17), 12: (2, -4)}},
    "toronto": {"alias": "canada"},
    "saudi": {"city": "Riyadh", "iata": "RUH", "currency": "SAR", "subject": "AlUla's sandstone canyons", "daily_aed": 300,
              "climate": {1: (21, 9), 7: (43, 29), 12: (22, 10)}, "name": "Saudi Arabia"},
    "riyadh": {"alias": "saudi"}, "alula": {"alias": "saudi"},
    "oman": {"city": "Muscat", "iata": "MCT", "currency": "OMR", "subject": "Muscat's corniche and mountains", "daily_aed": 250,
             "climate": {1: (25, 19), 7: (37, 31), 12: (27, 21)}},
    "muscat": {"alias": "oman"},
    "qatar": {"city": "Doha", "iata": "DOH", "currency": "QAR", "subject": "the Doha skyline over the bay", "daily_aed": 350,
              "climate": {1: (22, 14), 7: (41, 30), 12: (24, 16)}},
    "doha": {"alias": "qatar"},
    "azerbaijan": {"city": "Baku", "iata": "GYD", "currency": "AZN", "subject": "Baku's Flame Towers at night", "daily_aed": 220,
                   "climate": {1: (7, 1), 7: (31, 22), 12: (9, 3)}},
    "baku": {"alias": "azerbaijan"},
    "uzbekistan": {"city": "Tashkent", "iata": "TAS", "currency": "UZS", "subject": "Samarkand's blue-tiled Registan", "daily_aed": 180,
                   "climate": {1: (7, -2), 7: (36, 20), 12: (9, 0)}},
    "tashkent": {"alias": "uzbekistan"}, "samarkand": {"alias": "uzbekistan"},
    "kenya": {"city": "Nairobi", "iata": "NBO", "currency": "KES", "subject": "a Maasai Mara safari at sunset", "daily_aed": 300,
              "climate": {1: (26, 13), 7: (22, 11), 12: (25, 13)}},
    "nairobi": {"alias": "kenya"},
    "zanzibar": {"city": "Zanzibar", "iata": "ZNZ", "currency": "TZS", "subject": "Zanzibar's white beaches and dhows", "daily_aed": 250,
                 "climate": {1: (32, 25), 7: (28, 21), 12: (32, 24)}},
    "tanzania": {"alias": "zanzibar"},
    "south africa": {"city": "Cape Town", "iata": "CPT", "currency": "ZAR", "subject": "Table Mountain over Cape Town", "daily_aed": 300,
                     "climate": {1: (27, 16), 7: (18, 8), 12: (26, 15)}},
    "cape town": {"alias": "south africa"},
    "mauritius": {"city": "Port Louis", "iata": "MRU", "currency": "MUR", "subject": "a Mauritius lagoon under Le Morne", "daily_aed": 400,
                  "climate": {1: (30, 23), 7: (24, 17), 12: (29, 22)}},
    "seychelles": {"city": "Mahé", "iata": "SEZ", "currency": "SCR", "subject": "Seychelles granite boulders on a white beach", "daily_aed": 550,
                   "climate": {1: (30, 25), 7: (28, 24), 12: (30, 25)}},
    "australia": {"city": "Sydney", "iata": "SYD", "currency": "AUD", "subject": "Sydney Opera House on the harbour", "daily_aed": 500,
                  "climate": {1: (26, 19), 7: (17, 8), 12: (25, 17)}},
    "sydney": {"alias": "australia"},
}
for _k, _v in list(PLACES.items()):
    if "alias" in _v:
        PLACES[_k] = {**PLACES[_v["alias"]]}  # the target is defined (and named) earlier in the table
    else:
        _v.setdefault("name", _k.title())
# Airport codes as typed ("CPH") resolve to the place that flies there.
IATA_PLACES = {v["iata"]: v for k, v in PLACES.items()}

FX_FALLBACK = {"EGP": 13.2, "TRY": 9.4, "GEL": 0.74, "JPY": 40.5, "GBP": 0.21, "EUR": 0.24, "CHF": 0.22,
               "IDR": 4420.0, "JOD": 0.19, "MAD": 2.6, "KZT": 141.0, "DKK": 1.83, "SEK": 2.9, "NOK": 2.9, "ISK": 37.5,
               "CZK": 6.2, "HUF": 98.0, "PLN": 1.08, "THB": 8.9, "MVR": 4.2, "LKR": 80.0, "INR": 23.0, "SGD": 0.35,
               "MYR": 1.2, "VND": 7000.0, "KRW": 380.0, "CNY": 1.95, "USD": 0.272, "CAD": 0.38, "SAR": 1.02,
               "OMR": 0.105, "QAR": 0.99, "AZN": 0.46, "UZS": 3450.0, "KES": 35.0, "TZS": 700.0, "ZAR": 4.9,
               "MUR": 12.4, "SCR": 3.9, "AUD": 0.41}

# A region is not a destination: "europe" never resolves to one country by itself — the planner asks which one.
# Examples only name places the planner knows, so the answer lands on the first try.
REGIONS: dict[str, list[str]] = {
    "europe": ["France", "Italy", "Spain", "Greece", "Portugal", "Switzerland", "Austria", "Germany", "the Netherlands", "the UK",
               "Denmark", "Czechia"],
    "asia": ["Japan", "Bali", "Georgia", "Kazakhstan", "Thailand", "the Maldives", "Singapore", "Azerbaijan"],
    "africa": ["Egypt", "Morocco", "Kenya", "Zanzibar", "Mauritius"],
    "scandinavia": ["Denmark", "Sweden", "Norway", "Finland", "Iceland"],
}
STOPWORDS = {"that", "this", "with", "from", "have", "your", "about", "there", "they", "what", "when", "will", "just", "like",
             "make", "create", "image", "messenger", "sticker", "plan", "setup", "true", "really", "think", "thinking", "also", "said"}
MONTHS = {m.lower(): i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                               "September", "October", "November", "December"], 1)}
UAE_HOLIDAYS = {(1, 1): "New Year's Day", (12, 2): "Eid Al Etihad", (12, 3): "Eid Al Etihad"}
LEAVE_WORDS = re.compile(r"\b(leave|vacation|holiday|off work|days off|taking off|coming|join|in too|trip)\b", re.I)


def best_leave(year: int, month: int, length: int, max_leave: int | None) -> dict:
    """The `length`-day window in the month that needs the fewest leave days (UAE weekend Sat–Sun + public holidays).
    Ties go to the window with the most days off at either end, then the earliest."""
    days_in = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)).day
    best = None
    for start in range(1, days_in - length + 2):
        days = [dt.date(year, month, start) + dt.timedelta(days=i) for i in range(length)]
        off = [d for d in days if d.weekday() >= 5 or (d.month, d.day) in UAE_HOLIDAYS]
        leave = length - len(off)
        if max_leave is not None and leave > max_leave:
            continue
        # Also count free days that touch the window (a Friday holiday before a Saturday start still helps).
        before = days[0] - dt.timedelta(days=1)
        bonus = int(before.weekday() >= 5 or (before.month, before.day) in UAE_HOLIDAYS)
        key = (leave, -bonus, start)
        if best is None or key < best[0]:
            best = (key, days, off, leave)
    if best is None:
        return best_leave(year, month, max(3, length - 2), max_leave)
    _, days, off, leave = best
    return {"from": days[0].isoformat(), "to": days[-1].isoformat(), "days": len(days), "leaveDays": leave,
            "freeDays": len(off), "holidays": [UAE_HOLIDAYS[(d.month, d.day)] for d in off if (d.month, d.day) in UAE_HOLIDAYS],
            "weekendDays": [d.isoformat() for d in off]}


MONTH_WORD = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?{MONTH_WORD}\b|\b{MONTH_WORD}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", re.I)


def start_date(text: str, today: dt.date) -> dt.date | None:
    """An explicit start day in the request — "on 2 january", "2nd of Jan", "January 2" — at its next occurrence."""
    m = DAY_MONTH.search(text)
    if not m:
        return None
    day, word = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
    month = next(i for name, i in MONTHS.items() if name.startswith(word.lower()[:3]))
    for year in (today.year, today.year + 1):
        try:
            d = dt.date(year, month, int(day))
        except ValueError:
            return None
        if d > today:
            return d
    return None


DAY_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
# Full day names stand alone; a short form ("fri") only counts after next/this/on, so "sunny" or "money" never match.
RELATIVE_DAY = re.compile(
    r"\b(?:(next|this|coming|on)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"|\b(next|this|coming|on)\s+(mon|tues?|wed|thur?s?|fri|sat|sun)\b"
    r"|\b(tomorrow|this weekend|next weekend|next week)\b", re.I)


def relative_start(text: str, today: dt.date) -> dt.date | None:
    """A start day said relative to today: "tomorrow", "friday" / "this friday" (the coming one), "next friday"
    (that day in next calendar week), "this weekend" (the coming Saturday), "next week" (next Monday)."""
    m = RELATIVE_DAY.search(re.sub(r"@messenger\b", " ", text, flags=re.I))
    if not m:
        return None
    next_monday = today + dt.timedelta(days=7 - today.weekday())
    if m.group(5):
        word = m.group(5).lower()
        if word == "tomorrow":
            return today + dt.timedelta(days=1)
        if word == "next week":
            return next_monday
        saturday = today + dt.timedelta(days=(5 - today.weekday()) % 7 or 7)
        return saturday + dt.timedelta(days=7) if word == "next weekend" else saturday
    prefix, day = (m.group(1), m.group(2)) if m.group(2) else (m.group(3), m.group(4))
    target = DAY_INDEX[day.lower()[:3]]
    if (prefix or "").lower() == "next":
        return next_monday + dt.timedelta(days=target)
    return today + dt.timedelta(days=(target - today.weekday()) % 7 or 7)


def fixed_leave(start: dt.date, end: dt.date) -> dict:
    """The leave for exactly the selected dates. The range is kept as picked — weekends stay in it and it is
    never shifted or shortened; only workdays that are not UAE public holidays count as leave days."""
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    off = [d for d in days if d.weekday() >= 5 or (d.month, d.day) in UAE_HOLIDAYS]
    return {"from": days[0].isoformat(), "to": days[-1].isoformat(), "days": len(days), "leaveDays": len(days) - len(off),
            "freeDays": len(off), "holidays": [UAE_HOLIDAYS[(d.month, d.day)] for d in off if (d.month, d.day) in UAE_HOLIDAYS],
            "weekendDays": [d.isoformat() for d in off], "fixed": True}


WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "mon", "tue", "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun"}
DEST_STOP = (STOPWORDS | set(MONTHS) | WEEKDAYS
             | {"messenger", "plan", "trip", "travel", "visit", "holiday", "vacation", "tour", "flight", "flights",
                "hotel", "group", "explore", "aswell", "well", "too", "also", "with", "from", "for",
                "sounds", "sound", "good", "great", "nice", "sure", "maybe", "yes", "yeah"})
NAME_STOP = (STOPWORDS | set(MONTHS) | WEEKDAYS
             | {"messenger", "trip", "travel", "travelling", "traveling", "visit", "holiday", "vacation", "tour",
                "flight", "flights", "hotel", "group", "leave", "days", "day", "aswell", "well", "too", "also",
                "both", "each", "other", "plus", "along", "together", "friend", "friends", "everyone", "everybody",
                "someone", "anyone", "nobody"})

TO_PLACE = re.compile(r"\b(?:trip\s+(?:to|for|in)|visit\s+to|travel\s+to|fly\s+to|go\s+to|plan\s+(?:for|in))\s+([A-Za-z]{3,})\b"
                      r"|\bto\s+([A-Z][A-Za-z]{2,})\b|\bvisit\s+([A-Z][A-Za-z]{2,})\b|\bplan\s+([A-Z][A-Za-z]{2,})\b")


def request_place(request: str) -> dict | None:
    """The destination named in the request: a known place or alias, an airport code as typed ("CPH"), or a close
    misspelling of a single-word place ("khazakhistan" → Kazakhstan)."""
    ask = re.sub(r"@messenger\b", " ", request, flags=re.I)
    low = ask.lower()
    place = next((PLACES[k] for k in sorted(PLACES, key=len, reverse=True) if re.search(rf"\b{k}\b", low)), None)
    if place:
        return place
    for code in re.findall(r"\b[A-Z]{3}\b", ask):
        if code in IATA_PLACES:
            return IATA_PLACES[code]
    single = [k for k in PLACES if " " not in k]
    for word in re.findall(r"[a-z]{5,}", low):
        if word in DEST_STOP:
            continue
        close = difflib.get_close_matches(word, single, n=1, cutoff=0.84)
        if close:
            return PLACES[close[0]]
    return None


def unknown_destination(request: str) -> str | None:
    """A destination word in the request that is not a place the planner knows ("to Atlantis"). Returned so the
    planner asks about it instead of silently reusing a country from old chat messages."""
    clean = re.sub(r"@messenger\b", " ", request, flags=re.I)
    cands: list[str] = []
    for m in TO_PLACE.finditer(clean):
        cands.append(next(g for g in m.groups() if g))
    if not cands and len(re.findall(r"[A-Za-z']+", clean)) <= 4:
        # A short follow-up to "where do you want to go?" ("Atlantis?", "Almaty") names the place outright.
        cands = re.findall(r"[A-Za-z']{3,}", clean)
    for word in cands:
        low = word.lower()
        if low in DEST_STOP or low in PLACES or low in REGIONS or low in MONTHS:
            continue
        return word
    return None


ISO_RANGE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\s*(?:to|until|\u2013|\u2014|-)\s*(\d{4}-\d{2}-\d{2})\b", re.I)
ISO_DAY = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _parse_iso(s: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def request_dates(request: str, today: dt.date) -> tuple[dt.date | None, dt.date | None]:
    """Explicit travel dates from the request itself — an ISO range ("from 2027-05-01 to 2027-05-07"), a single
    ISO day plus a length ("2027-05-01 for 5 days"), or a day-month ("on 2 january for 5 days"). Nothing is read
    from chat history and nothing is guessed: (None, None) means the planner must ask for dates."""
    m = ISO_RANGE.search(request)
    if m:
        start, end = _parse_iso(m.group(1)), _parse_iso(m.group(2))
        if start and end and today <= start <= end and (end - start).days < 60:
            return start, end
        # A broken range is not silently repaired: fall through to the other phrasings, then ask.
    single = ISO_DAY.search(request)
    if single and (day := _parse_iso(single.group(1))) and day >= today:
        explicit = [int(n) for n in re.findall(r"(\d{1,2})\s*(?:days?|nights?)\b", request.lower())]
        span = min(max(explicit[0] if explicit else 10, 1), 60)
        return day, day + dt.timedelta(days=span - 1)
    if (day := start_date(request, today) or relative_start(request, today)) is not None:
        explicit = [int(n) for n in re.findall(r"(\d{1,2})\s*(?:days?|nights?)\b", request.lower())]
        span = min(max(explicit[0] if explicit else 10, 1), 60)
        return day, day + dt.timedelta(days=span - 1)
    return None, None


def extract_trip(context: list[Msg], today: dt.date, request: str = "") -> dict:
    """Rules: the request itself ("@messenger plan egypt on 2 january for 5 days", "... from 2027-05-01 to
    2027-05-07") wins over the chat for destination and dates; the chat only fills gaps the request leaves
    silent. An explicit destination never falls back to history, and an unknown one ("to Atlantis") is reported
    instead of reusing a country from old messages. Dates are never taken from history and never guessed:
    without explicit dates `start`/`end` come back None so the planner asks instead of picking a window.
    A region ("europe") or no destination at all is not guessed: `place` comes back None with the region
    (if any), so the planner asks instead of forcing a country."""
    text = " ".join(m.text for m in context[-CONTEXT_MAX:])
    low = text.lower()
    ask = request.lower()
    place = request_place(request)
    unknown: str | None = None
    region: str | None = None
    if place is None:
        unknown = unknown_destination(request) if request.strip() else None
    if place is None and unknown is None:
        place = next((PLACES[k] for k in sorted(PLACES, key=len, reverse=True) if re.search(rf"\b{k}\b", low)), None)
        if place is None:
            region = next((r for src in (ask, low) for r in REGIONS if re.search(rf"\b{r}\b", src)), None)
    start, end = request_dates(request, today)
    budget = re.search(r"(\d[\d,]{2,})\s*(?:aed|dirhams?)", ask) or re.search(r"(\d[\d,]{2,})\s*(?:aed|dirhams?)", low)
    month_hint = next((MONTHS[w] for w in re.findall(r"[a-z]+", ask) if w in MONTHS), None)
    if month_hint is None:
        month_hint = next((MONTHS[w] for w in re.findall(r"[a-z]+", low) if w in MONTHS), (today.month % 12) + 1)
    year = start.year if start else today.year + (1 if month_hint <= today.month else 0)
    return {"place": place, "region": region, "unknown": unknown, "start": start, "end": end,
            "days": (end - start).days + 1 if start and end else None,
            "month": start.month if start else month_hint, "year": year,
            "budgetAed": int(budget.group(1).replace(",", "")) if budget else None, "text": text}


def companions(context: list[Msg], contacts: list[Contact], chat_partner: str | None) -> list[Contact]:
    """People explicitly named in a message about leave or joining ("with Hana", "Omar and Hana are coming").
    Names must match a contact exactly (typed text, so no near-name guessing). The chat partner is never added
    on their own: a group is only suggested when someone is actually mentioned, so planning alone never asks
    to "create a group"."""
    found: list[Contact] = []
    for m in context[-CONTEXT_MAX:]:
        if not LEAVE_WORDS.search(m.text):
            continue
        for c in contacts:
            first = c.name.split()[0]
            if re.search(rf"\b{re.escape(first)}\b", m.text) and c not in found and c.id != chat_partner:
                found.append(c)
    return [c for c in found if c.id not in ("me",)]


def mentioned_names(context: list[Msg]) -> list[str]:
    """First names tied to joining, whether or not they are contacts ("with Hana and Zane", "Omar and Hana
    are coming"). The planner matches these against contacts; whatever is left over is reported so the app
    can ask the person to confirm who is who instead of silently dropping them."""
    out: list[str] = []
    pats = (r"\bwith\s+([A-Z][a-z]{2,})(?:\s+and\s+([A-Z][a-z]{2,}))?",
            r"\b([A-Z][a-z]{2,})\s+and\s+([A-Z][a-z]{2,})\b")
    for m in context[-CONTEXT_MAX:]:
        if not LEAVE_WORDS.search(m.text):
            continue
        for pat in pats:
            for mm in re.finditer(pat, m.text):
                for g in mm.groups():
                    if g and g not in out:
                        out.append(g)
    return out


WITH_PAT = re.compile(r"\bwith\s+([A-Za-z']+)(?:\s+and\s+([A-Za-z']+))?", re.I)
JOIN_PAT = re.compile(r"\b([A-Za-z']+)\s+and\s+([A-Za-z']+)\s+(?:are\s+coming|is\s+coming|join(?:ing)?|coming|taking\s+leave|in\s+too)\b", re.I)


def resolve_request_companions(request: str, contacts: list[Contact], chat_partner: str | None
                               ) -> tuple[list[Contact], list[str], list[str], bool]:
    """People named in the request itself ("with sara", "Sara and Omar are coming", "with Sara Ali").
    Typed text spells names exactly, so a first name matching exactly one contact resolves on its own; a name
    matching two contacts asks instead of guessing. Full names are matched first, so "Sara Ali" never leaves a
    stray "Ali". Names that match nobody are reported so the app can confirm them. Returns
    (resolved, ambiguous, unknown, named_any): `named_any` tells the planner the request talked about people,
    so it must not fall back to names from old chat messages."""
    partner = next((c for c in contacts if c.id == chat_partner), None)
    partner_names = {partner.name.lower(), partner.name.split()[0].lower()} if partner else set()
    found: list[Contact] = []
    for c in contacts:
        if c.id in ("me", chat_partner) or len(c.name.split()) < 2:
            continue
        if re.search(rf"\b{re.escape(c.name)}\b", request, re.I) and c not in found:
            found.append(c)
    covered = {c.name.split()[0].lower() for c in found}
    surnames = {c.name.split()[-1].lower() for c in found}
    toks: list[str] = []
    for pat in (WITH_PAT, JOIN_PAT):
        for mm in pat.finditer(request):
            toks.extend(g for g in mm.groups() if g)
    ambiguous: list[str] = []
    unknown: list[str] = []
    partner_mentioned = any(t.lower() in partner_names for t in toks) or (
        partner is not None and re.search(rf"\b{re.escape(partner.name)}\b", request, re.I) is not None)
    for tok in toks:
        tl = tok.lower()
        if tl in covered or tl in surnames or tl in partner_names or tl in NAME_STOP:
            continue
        matches = [c for c in contacts if c.id not in ("me", chat_partner) and c.name.split()[0].lower() == tl]
        if len(matches) == 1:
            found.append(matches[0])
            covered.add(tl)
        elif len(matches) > 1:
            if tok not in ambiguous:
                ambiguous.append(tok)
        elif tok[:1].isupper() and tok not in unknown:
            unknown.append(tok)
    if partner_mentioned and partner and partner not in found:
        found.insert(0, partner)  # this chat's partner only travels when the request names them
    return found, ambiguous, unknown, bool(found or ambiguous or unknown)


async def fx_rate(currency: str, http: httpx.AsyncClient | None = None) -> tuple[float, str]:
    """AED → currency from a free, keyless rates API; a dated fallback if it is unreachable."""
    try:
        client = http or httpx.AsyncClient(timeout=3)
        res = await client.get("https://open.er-api.com/v6/latest/AED")
        res.raise_for_status()
        data = res.json()
        return float(data["rates"][currency]), f"open.er-api.com · {data.get('time_last_update_utc', '')[:16]}"
    except Exception:  # noqa: BLE001 — offline: an approximate rate, labelled as such
        return FX_FALLBACK.get(currency, 1.0), "approximate rate (offline)"


class Planner:
    """Trip plan. Leave is a local draft in the memory store. There is no HR connector."""

    def __init__(self, store: Store, http: httpx.AsyncClient | None = None, approver: str = "r.khalfan@nadi.ae") -> None:
        self.store, self.http, self.approver = store, http, approver

    async def _requests(self, user: str) -> list[dict]:
        return await self.store.get(f"nadi:{user}") or []

    async def _file_leave(self, user: str, start: str, end: str, leave_days: int, note: str) -> dict:
        existing = await self._requests(user)
        same = next((r for r in existing if r["from"] == start and r["to"] == end), None)
        if same:
            return {**same, "duplicate": True}
        used = sum(r["leaveDays"] for r in existing)
        balance = 30
        req = {"ref": f"NADI-{start[:4]}-{1400 + len(existing) + 1:04d}", "type": "Annual leave", "from": start, "to": end,
               "leaveDays": leave_days, "status": "Pending manager approval", "approver": "Line manager",
               "balanceBefore": balance - used, "balanceAfter": balance - used - leave_days,
               "note": note[:200], "filedAt": int(time.time())}
        await self.store.set(f"nadi:{user}", existing + [req])
        return req

    async def plan(self, user: str, context: list[Msg], contacts: list[Contact], chat_partner: str | None,
                   today: dt.date | None = None, request: str = "",
                   keep_members: list[str] | None = None) -> dict:
        started = time.time()
        today = today or dt.date.today()
        trip = extract_trip(context, today, request)
        if trip["place"] is None:
            # Never force a country: an unknown name is asked about outright (never borrowed from history),
            # a region gets its options, anything else asks outright. The person answers with
            # "@messenger <country>" and the next call resolves it.
            if trip.get("unknown"):
                return {"ask": (f"I couldn't find \"{trip['unknown']}\" — which country or city did you mean? "
                                "Name a city and I'll search flights there."),
                        "unknown": trip["unknown"], "status": "asked where to go"}
            region = trip.get("region") or ""
            examples = REGIONS.get(region, [])
            month_hint = f" for {dt.date(trip['year'], trip['month'], 1).strftime('%B')}" if request else ""
            return {"ask": (f"{region.title()} is a big place for one plan — which country{month_hint}? "
                            f"{', '.join(examples[:6])}?" if examples else
                            f"Where do you want to go{month_hint}? Name a country or a city and I'll plan it."),
                    "region": region, "status": "asked where to go"}
        place = trip["place"]
        if keep_members is not None:
            # Dates changed on an existing card: the same people carry over, nobody is re-asked.
            by_id = {c.id: c for c in contacts}
            people = [by_id[i] for i in keep_members if i in by_id and by_id[i].id != "me"]
            extra: list[str] = []
            group_detail = "Same people — kept when the dates changed."
        else:
            found, ambiguous, unknown_names, named_any = resolve_request_companions(request, contacts, chat_partner)
            if ambiguous:
                token = ambiguous[0]
                cands = [c for c in contacts if c.id != "me" and c.name.split()[0].lower() == token.lower()][:3]
                who = " or ".join(c.name for c in cands) if cands else token
                return {"ask": (f"Who do you mean — {who}? Reply with the full name and I'll add them to the trip."),
                        "ambiguous": ambiguous, "status": "asked who is coming"}
            # Travellers are you plus exactly the people the request names. Nobody is borrowed from old
            # messages or added because they are in this chat: no names → a solo trip, no group step.
            people = found if named_any else []
            extra = unknown_names if named_any else []
            group_detail = "Named in your message."
        travellers = 1 + len(people)
        names = [c.name.split()[0] for c in people]
        dest = {"country": place["name"], "city": place["city"], "iata": place["iata"]}
        if trip["start"] is None or trip["end"] is None:
            # Dates are missing: ask inside the trip card. Nothing is filed, drafted or scheduled yet — the
            # person picks dates first, then the same participants carry over to the full plan.
            # Minimal: just the date picker (and the group, when people were named). Flights appear once dates exist.
            steps = [{"kind": "dates", "title": "Pick your dates", "detail": "",
                      "data": {"from": trip["start"].isoformat() if trip["start"] else ""}}]
            if people or extra:
                steps.append({"kind": "group",
                              "title": f"Create a group with {_join(names)}?" if names else "Create a group?",
                              "detail": f"Not in your contacts: {_join(extra)} — confirm below." if extra else "",
                              "data": {"name": f"{place['name']} trip",
                                       "members": [c.id for c in people], "suggested": extra}})
            return {"title": place["city"] if place["city"] != place["name"] else place["name"],
                    "summary": f"{'With ' + _join(names) + ' · ' if names else ''}DXB → {place['iata']} · {travellers} "
                               f"{'traveller' if travellers == 1 else 'travellers'}",
                    "needsDates": True, "destination": dest, "steps": steps,
                    "calendar": {"year": today.year, "month": today.month, "from": "", "to": "", "free": []},
                    "status": "waiting for dates"}
        leave = fixed_leave(trip["start"], trip["end"])
        nadi = await self._file_leave(user, leave["from"], leave["to"], leave["leaveDays"], f"Trip to {place['name']}")
        budget = trip["budgetAed"] or place["daily_aed"] * leave["days"]
        rate, rate_source = await fx_rate(place["currency"], self.http)
        hi, lo = place["climate"].get(trip["month"], (None, None))
        start = dt.date.fromisoformat(leave["from"])
        remind = max(today + dt.timedelta(days=1), start - dt.timedelta(days=75))
        month_name = start.strftime("%B %Y")
        steps = [
            {"kind": "leave", "title": f"Annual leave filed in Nadi · {_d(leave['from'])} – {_d(leave['to'])}",
             "detail": f"{leave['days']} days away for {leave['leaveDays']} days of leave — "
                       f"{leave['freeDays']} are weekends{' and ' + ', '.join(leave['holidays']) if leave['holidays'] else ''}. "
                       f"{nadi['ref']} · {nadi['status']} · balance {nadi['balanceBefore']} → {nadi['balanceAfter']} days",
             "data": {"leave": leave, "nadi": nadi}},
            {"kind": "email", "title": f"Added draft email to {self.approver}",
             "detail": "Asks your manager to approve the leave — saved in Mail › Drafts, not sent.",
             "data": {"to": self.approver, "subject": f"Annual leave request · {_d(leave['from'])} – {_d(leave['to'])}",
                      "body": (f"Hello,\n\nI've filed annual leave in Nadi for {_d(leave['from'])} – {_d(leave['to'])} "
                               f"({leave['leaveDays']} leave days, ref {nadi['ref']}) for a trip to {place['name']}. "
                               "Could you approve it when you have a moment?\n\nThank you.")}},
            {"kind": "flights", "title": f"Flights DXB → {place['iata']} for {travellers}",
             "detail": f"{_d(leave['from'])} out, {_d(leave['to'])} back · economy",
             "data": {"query": {"from": "DXB", "to": place["iata"], "depart": leave["from"], "return": leave["to"],
                                "passengers": travellers, "cabin": "economy"}}},
            {"kind": "budget", "title": f"Spending money: AED {budget:,} ≈ {place['currency']} {round(budget * rate):,}",
             "detail": f"About AED {round(budget / leave['days']):,} a day for {leave['days']} days · 1 AED = {rate:g} {place['currency']} ({rate_source})",
             "data": {"aed": budget, "rate": rate, "currency": place["currency"], "local": round(budget * rate)}},
        ]
        if people or extra:
            detail = group_detail
            if extra:
                detail += f" Also mentioned, not in your contacts: {_join(extra)} — confirm below."
            steps.append({"kind": "group",
                          "title": f"Create a group with {_join(names)}?" if names else "Create a group?",
                          "detail": detail,
                          "data": {"name": f"{place['name']} · {start.strftime('%b %Y')}",
                                   "members": [c.id for c in people], "suggested": extra}})
        steps.append({"kind": "reminder", "title": f"Reminder set in Messenger Calendar · {_d(remind.isoformat())}, 9:00 AM",
                      "detail": f"“Book {place['name']} flights” — you'll get a notification. Leave days added to your calendar.",
                      "data": {"events": [
                          {"title": f"Book {place['name']} flights", "start": f"{remind.isoformat()}T09:00:00", "end": f"{remind.isoformat()}T09:30:00",
                           "calendar": "travel", "notes": "Messenger reminder from your trip plan"},
                          {"title": f"{place['name']} trip (annual leave {nadi['ref']})", "start": f"{leave['from']}T00:00:00",
                           # all-day: ends at midnight after the last day (the calendar's all-day convention)
                           "end": f"{(dt.date.fromisoformat(leave['to']) + dt.timedelta(days=1)).isoformat()}T00:00:00",
                           "calendar": "travel", "location": place["city"]}]}})
        if hi is not None:
            steps.append({"kind": "weather", "title": f"{place['city']} in {start.strftime('%B')}: typically {hi}° / {lo}°C",
                          "detail": "Warm days, cool evenings — pack a light jacket.", "data": {"high": hi, "low": lo}})
        return {"title": f"{place['name']} · {month_name}", "summary": f"{leave['days']} days in {place['city']} for {leave['leaveDays']} leave days",
                "destination": dest, "steps": steps,
                "status": f"Planned in {max(1, round(time.time() - started))}s · {len(steps)} steps",
                "calendar": {"year": start.year, "month": start.month, "from": leave["from"], "to": leave["to"],
                             "free": leave["weekendDays"]}}


def _d(iso: str) -> str:
    return dt.date.fromisoformat(iso).strftime("%d %b").lstrip("0")


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
