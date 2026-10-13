"""Luna's output contract. Understanding only: intents come from an allowlist,
slots are typed, and the free text is a short reply with no URLs, prices or
statuses (CLAUDE.md rules 1, 2, 7). The host decides what happens next."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal["lost_item", "airport_guide", "service_offers", "places_near", "greeting", "smalltalk", "unclear"]
Service = Literal["laundry", "cleaning", "ac", "grooming", "carwash", "pharmacy", "maid"]
Category = Literal["pets", "food", "coffee", "barber", "home-help", "laundry", "clothing", "fix-it"]
FactKey = Literal["area", "hotel", "terminal", "taxi_plate", "taxi_roof", "deadline", "pet", "language", "other"]


class StatedFact(BaseModel):
    """Something the user explicitly said about themselves in this message."""
    key: FactKey
    value: str = Field(max_length=80)


class Understanding(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    item: Optional[str] = Field(description="lost_item only: the lost thing in one or two words, e.g. wallet")
    where_lost: Optional[Literal["taxi", "metro", "shop", "unknown"]]
    service: Optional[Service] = Field(description="service_offers only")
    category: Optional[Category] = Field(description="places_near only")
    subcategory: Optional[str] = Field(description="places_near only, e.g. Grooming, Vet, 24h")
    terminal: Optional[Literal["1", "2", "3"]]
    stated_facts: list[StatedFact] = Field(description="Only facts the user explicitly stated about themselves. Never guesses.")
    reply: str = Field(max_length=300, description="One or two warm, plain sentences. No URLs, prices, phone numbers or order statuses.")
    clarify: Optional[str] = Field(description="If unclear: one short question that would resolve it")
