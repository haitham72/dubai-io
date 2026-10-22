"""Luna's output contract. Understanding only: intents come from an allowlist,
slots are typed, and the free text is a short reply with no URLs, prices or
statuses (CLAUDE.md rules 1, 2, 7). The host decides what happens next."""
from typing import Literal, Optional

from datetime import datetime
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Intent = Literal[
    "lost_item",
    "airport_guide",
    "service_offers",
    "places_near",
    "order_status",
    "task_help",
    "info_question",
    "market_quote",
    "product_search",
    "greeting",
    "smalltalk",
    "unclear",
]
Service = Literal["laundry", "cleaning", "ac", "grooming", "carwash", "pharmacy", "maid"]
Category = Literal["pets", "food", "coffee", "barber", "home-help", "laundry", "clothing", "fix-it"]
FactKey = Literal["area", "hotel", "terminal", "taxi_plate", "taxi_roof", "deadline", "pet", "language", "other"]


class FocusContext(BaseModel):
    """Transient selected UI data, not confirmed memory or provider availability."""
    model_config = ConfigDict(extra="forbid")
    entity_id: str = Field(min_length=1, max_length=160)
    entity_name: str = Field(min_length=1, max_length=120)
    source: Literal["google", "app", "user"]
    card: str | None = Field(default=None, max_length=80)
    fragment: str | None = Field(default=None, max_length=300)
    selected_at: datetime
    area: str | None = Field(default=None, max_length=80)
    plan_id: str | None = Field(default=None, max_length=64)
    plan_revision: int | None = Field(default=None, ge=1)


class TaskFocusContext(BaseModel):
    """Only a reference leaves the client; task content is resolved by its owner."""
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(ge=1)
    selected_at: AwareDatetime


class ProjectFocusContext(BaseModel):
    """Owner/revision-bound workspace reference; content stays server-resolved."""
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(ge=1)
    selected_at: AwareDatetime


class StatedFact(BaseModel):
    """Something the user explicitly said about themselves in this message."""
    key: FactKey
    value: str = Field(max_length=80)


class TaskEditSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["outcome", "next_step", "details", "due_at"]
    value: str = Field(max_length=1600, description="Requested replacement; empty clears an optional value. due_at must be an ISO timestamp with timezone, normally +04:00 for Dubai.")


class Understanding(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    item: Optional[str] = Field(description="lost_item only: the lost thing in one or two words, e.g. wallet")
    where_lost: Optional[Literal["taxi", "metro", "shop", "unknown"]]
    service: Optional[Service] = Field(description="service_offers only")
    category: Optional[Category] = Field(description="places_near only")
    subcategory: Optional[str] = Field(description="places_near only, e.g. Grooming, Vet, 24h")
    terminal: Optional[Literal["1", "2", "3"]]
    query: Optional[str] = Field(default=None, max_length=200, description="info_question: a short web search query; product_search: the product to search for, e.g. shampoo")
    symbol: Optional[str] = Field(default=None, max_length=15, description="market_quote only: the ticker symbol, e.g. AAPL, TSLA, BINANCE:BTCUSDT")
    stated_facts: list[StatedFact] = Field(description="Only facts the user explicitly stated about themselves. Never guesses.")
    reply: str = Field(max_length=300, description="One or two warm, plain sentences. No URLs, prices, phone numbers or order statuses.")
    clarify: Optional[str] = Field(description="If unclear: one short question that would resolve it")
    task_edits: list[TaskEditSuggestion] = Field(default_factory=list, max_length=4, description="task_help only: explicit requested task-detail changes to propose for review. Empty unless the user requested a change. Never status, source or execution changes.")
