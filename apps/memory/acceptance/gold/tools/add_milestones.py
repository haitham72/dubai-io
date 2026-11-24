"""P2: append milestones + trivia + profile to gold/ledger.json.

Adds only NEW top-level keys. Never touches facts/people/records/probes/ingest order.
Idempotent: skips keys that already exist.
"""
import json
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent
LEDGER = GOLD / "ledger.json"

MILESTONES = [
    {"id": "ms01", "title": "Ship Raseef beta to testers",
     "status_by_week": {"1": "planned", "2": "in_progress", "3": "in_progress", "4": "in_progress", "5": "done"},
     "fact_ids": ["f015", "f016", "f059", "f082"], "first_week": 2},
    {"id": "ms02", "title": "Train up to the half marathon",
     "status_by_week": {"1": "planned", "2": "in_progress", "3": "in_progress", "4": "in_progress", "5": "in_progress"},
     "fact_ids": ["f036", "f038", "f100", "f037"], "first_week": 2},
    {"id": "ms03", "title": "Buy the used Camry",
     "status_by_week": {"1": "in_progress", "2": "in_progress", "3": "in_progress", "4": "in_progress", "5": "in_progress"},
     "fact_ids": ["f033", "f050", "f098", "f073"], "first_week": 1},
    {"id": "ms04", "title": "Complete the LLM agents course",
     "status_by_week": {"1": "planned", "2": "planned", "3": "planned", "4": "in_progress", "5": "in_progress"},
     "fact_ids": ["f039", "f041", "f075", "f101"], "first_week": 2},
    {"id": "ms05", "title": "Grow AI bil Arabi past 500 subscribers",
     "status_by_week": {"1": None, "2": None, "3": "in_progress", "4": "in_progress", "5": "done"},
     "fact_ids": ["f061", "f062"], "first_week": 5},
    {"id": "ms06", "title": "Complete dental cleaning",
     "status_by_week": {"1": None, "2": "in_progress", "3": "in_progress", "4": "done", "5": "done"},
     "fact_ids": ["f065", "f107"], "first_week": 2},
]

TRIVIA = [
    {"id": "tr01", "text": "Skillforge OTP verification email (login code, expires in 10 min).", "record_ids": ["g132"]},
    {"id": "tr02", "text": "StreamFlix winback promo (50% off, marketing).", "record_ids": ["g076"]},
    {"id": "tr03", "text": "FitZone membership-pause confirmation email.", "record_ids": ["g065"]},
    {"id": "tr04", "text": "Aramex one-off delivery notification.", "record_ids": ["g024"]},
    {"id": "tr05", "text": "PeakForm spin-class booking confirmation.", "record_ids": ["g010"]},
    {"id": "tr06", "text": "DarProperty saved-search update email.", "record_ids": ["g004"]},
    {"id": "tr07", "text": "NexaPay public tech-talk invite.", "record_ids": ["g130"]},
    {"id": "tr08", "text": "Marathon race-pack collection notice.", "record_ids": ["g038"]},
    {"id": "tr09", "text": "AutoHub service-slot reminder.", "record_ids": ["g028"]},
    {"id": "tr10", "text": "Work-chat complaint about the GPU queue being long.", "record_ids": ["wag-0004"]},
    {"id": "tr11", "text": "Work-chat complaint about the VPN being slow.", "record_ids": ["wag-0027"]},
    {"id": "tr12", "text": "noon flash-sale promo email.", "record_ids": ["g080"]},
]

PROFILE = {
    "Identity": [
        {"text": "Karim is a 31-year-old AI engineer at QamarTech in Dubai.", "fact_ids": ["f001", "f002"], "first_week": 1},
        {"text": "He rents a 1BR in Al Barsha; rent rose to AED 5,400 from November.", "fact_ids": ["f003", "f004"], "first_week": 2},
        {"text": "He co-founded the Raseef side-project app with Nour El-Din.", "fact_ids": ["f015"], "first_week": 1},
    ],
    "Personality": [
        {"text": "Trains consistently even with a full schedule.", "fact_ids": ["f038", "f100"], "first_week": 4},
        {"text": "Documents decisions and deliberations in his notes.", "fact_ids": ["f043", "f044"], "first_week": 5},
        {"text": "Shows up for friends (best-man duties, beta testing).", "fact_ids": ["f056", "f011"], "first_week": 3},
    ],
    "Values": [
        {"text": "Family first: monthly food box flow, preps for his mother's visit.", "fact_ids": ["f091", "f071"], "first_week": 4},
        {"text": "Financially disciplined: monthly gold plan, explicit flat budget.", "fact_ids": ["f060", "f043"], "first_week": 2},
        {"text": "Invests in health: gym membership plus marathon training.", "fact_ids": ["f006", "f038"], "first_week": 2},
    ],
    "Strengths & Tensions": [
        {"text": "Strong backend/API engineer (fixed the Atlas ranking latency bug).", "fact_ids": ["f087"], "first_week": 3},
        {"text": "Stretched thin across Atlas, Raseef and marathon; killed the freelance gig.", "fact_ids": ["f047"], "first_week": 4},
        {"text": "Job search is selective: product teams only, turned down misaligned roles.", "fact_ids": ["f076", "f030"], "first_week": 2},
    ],
    "Interests": [
        {"text": "Long-distance running with a club.", "fact_ids": ["f036", "f038"], "first_week": 2},
        {"text": "Arabic AI education via his YouTube channel.", "fact_ids": ["f061"], "first_week": 3},
        {"text": "Personal finance: monthly gold coin purchases.", "fact_ids": ["f060", "f104"], "first_week": 2},
    ],
    "Drive": [
        {"text": "Wants a Senior AI Engineer role in Dubai at AED 28k+.", "fact_ids": ["f076"], "first_week": 2},
        {"text": "Finishes what he starts: course labs, Raseef 0.4.", "fact_ids": ["f075", "f082"], "first_week": 5},
        {"text": "Upgraded his marathon goal from 10K to half.", "fact_ids": ["f037"], "first_week": 4},
    ],
    "Relationships": [
        {"text": "Best friend is Omar Farouk; Karim is his best man.", "fact_ids": ["f007", "f056"], "first_week": 3},
        {"text": "Reports to Salma Nasser at QamarTech.", "fact_ids": ["f013"], "first_week": 1},
        {"text": "Close to his mother Layla; preps the flat for her December visit.", "fact_ids": ["f071", "f091"], "first_week": 4},
        {"text": "Cousin Salma Haddad visits Dubai mid-December.", "fact_ids": ["f092"], "first_week": 5},
    ],
}

MUST_NOT_CLAIM = [
    "Karim accepted a NexaPay offer (only an intro was offered).",
    "Karim bought the Camry (he is 90% decided, not done).",
    "Layla lives with Karim in Dubai (she visits from Cairo).",
]


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for key, val in (("milestones", MILESTONES), ("trivia", TRIVIA), ("profile", PROFILE),
                     ("must_not_claim", MUST_NOT_CLAIM)):
        if key in ledger:
            print(f"{key} already present, skipping")
        else:
            ledger[key] = val
            print(f"added {key}: {len(val) if isinstance(val, list) else len(val)} entries")
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
