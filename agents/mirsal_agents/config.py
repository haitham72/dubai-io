"""Settings from the environment (the repo's .env is loaded when present). Every key is optional: missing keys mean fakes."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "agents" / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, "").strip() or default


def _float(key: str, default: float) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(float(_env(key, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class Cleaner:
    """Clean AI Detection engine tuning (was ai_cleaner_engine USER SETTINGS).

    Every value is overridable from the environment; the engine keeps
    same-name module globals sourced from here so battle-tested call sites
    keep working. No settings API: change env, restart the service."""

    mode: str = field(default_factory=lambda: _env("CLEANER_MODE", "resize_then_sdxl"))
    resize_multiplier: float = field(default_factory=lambda: _float("CLEANER_RESIZE_MULTIPLIER", 2))
    jpeg_quality: int = field(default_factory=lambda: _int("CLEANER_JPEG_QUALITY", 95))
    output_format: str = field(default_factory=lambda: _env("CLEANER_OUTPUT_FORMAT", "jpg"))
    sdxl_strength: float = field(default_factory=lambda: _float("CLEANER_SDXL_STRENGTH", 0.01))
    sdxl_effective_steps: int = field(default_factory=lambda: _int("CLEANER_SDXL_EFFECTIVE_STEPS", 2))
    cpu_offload: bool = field(default_factory=lambda: _env("CLEANER_CPU_OFFLOAD", "1") == "1")
    max_resolution: int = field(default_factory=lambda: _int("CLEANER_MAX_RESOLUTION", 2024))
    allow_model_downloads: bool = field(default_factory=lambda: _env("CLEANER_ALLOW_MODEL_DOWNLOADS", "1") == "1")
    pipeline: str = field(default_factory=lambda: _env("CLEANER_PIPELINE", "sdxl-zimage"))
@dataclass(frozen=True)
class Prices:
    """USD. Streaming STT and Decisions are the owner-approved POC prices; the rest are list prices, overridable."""
    stt_per_minute: float = field(default_factory=lambda: _float("PRICE_STT_PER_MIN", 0.017))
    decision_in_per_m: float = field(default_factory=lambda: _float("PRICE_DECISION_IN_PER_M", 0.10))
    decision_out_per_m: float = field(default_factory=lambda: _float("PRICE_DECISION_OUT_PER_M", 0.40))
    llm_in_per_m: float = field(default_factory=lambda: _float("PRICE_LLM_IN_PER_M", 0.15))
    llm_out_per_m: float = field(default_factory=lambda: _float("PRICE_LLM_OUT_PER_M", 0.60))
    search_credit: float = field(default_factory=lambda: _float("PRICE_SEARCH_CREDIT", 0.008))


@dataclass(frozen=True)
class Settings:
    openai_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    # Legacy fallback for the Nara base URL only. NEVER point the OpenAI SDK at it: the SDK reads
    # OPENAI_BASE_URL from the environment on its own, which would send the OpenAI key to the router.
    # OpenAI clients are therefore built with an explicit base_url (see app.py).
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL"))
    # Text/vLLM provider (Nara router): chat, replies, research, fact check.
    nara_key: str = field(default_factory=lambda: _env("NARA_API_KEY"))
    nara_base_url: str = field(default_factory=lambda: _env("NARA_BASE_URL") or _env("OPENAI_BASE_URL"))
    tavily_key: str = field(default_factory=lambda: _env("TVLY_API_KEY") or _env("TAVILY_API_KEY"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))
    stt_model: str = field(default_factory=lambda: _env("AGENTS_STT_MODEL", "gpt-realtime-whisper"))
    # Streaming transcription (OpenAI realtime) is opt-in: third-party routers don't serve it — while off the
    # browser keeps its batch voice path and the service reports stt "fake".
    stt_live: bool = field(default_factory=lambda: _env("AGENTS_STT_LIVE") == "1")
    # How long the transcriber waits before emitting text (gpt-realtime-whisper): "minimal" streamed fast but garbled
    # words in live use; "medium" lets the stream run a little before committing to words.
    stt_delay: str = field(default_factory=lambda: _env("AGENTS_STT_DELAY", "medium"))
    decision_model: str = field(default_factory=lambda: _env("AGENTS_DECISION_MODEL", "gpt-6-luna"))
    # Unambiguous in-app commands ("check notifications", "open mail") are decided by rules in ~0 ms, skipping the model.
    # Seconds a live transcript must stay unchanged before a clause is decided (mid-sentence actions wait this long).
    stable_s: float = field(default_factory=lambda: _float("AGENTS_STABLE_S", 0.35))
    fast_path: bool = field(default_factory=lambda: _env("AGENTS_FAST_PATH", "1") == "1")
    # Who a trip plan's leave-approval email is addressed to (it is only ever saved as a draft).
    leave_approver: str = field(default_factory=lambda: _env("NADI_APPROVER_EMAIL", "r.khalfan@nadi.ae"))
    research_model: str = field(default_factory=lambda: _env("AGENTS_RESEARCH_MODEL") or _env("OPENAI_MODEL", "gpt-4o-mini"))
    # Reads photos for "@mirsal is this true" (OpenAI, image input). Defaults to the research model.
    vision_model: str = field(default_factory=lambda: _env("AGENTS_VISION_MODEL"))
    # Live providers are opt-in: a key alone is not enough, so a dev loop never spends by accident.
    live: bool = field(default_factory=lambda: _env("AGENTS_LIVE") == "1")
    budget_usd: float = field(default_factory=lambda: _float("AGENTS_BUDGET_USD", 1.0))
    act_threshold: float = field(default_factory=lambda: _float("AGENTS_ACT_THRESHOLD", 0.80))
    act_margin: float = field(default_factory=lambda: _float("AGENTS_ACT_MARGIN", 0.30))
    undo_ms: int = field(default_factory=lambda: int(_float("AGENTS_UNDO_MS", 3000)))
    watch_enabled: bool = field(default_factory=lambda: _env("AGENTS_WATCH", "1") == "1")
    gmail_client_file: Path = field(default_factory=lambda: Path(_env("GMAIL_CLIENT_FILE", str(ROOT / "agents" / ".secrets" / "gmail_client.json"))))
    gmail_token_file: Path = field(default_factory=lambda: Path(_env("GMAIL_TOKEN_FILE", str(ROOT / "agents" / ".secrets" / "gmail_token.json"))))
    public_url: str = field(default_factory=lambda: _env("AGENTS_PUBLIC_URL", "http://localhost:5173"))
    stickers_dir: Path = field(default_factory=lambda: Path(_env("STICKERS_DIR", str(ROOT / "public" / "stickers"))))
    # The Mirsal Builder project's Library (approved packs, read only). Default: the sibling checkout, when present.
    builder_library: Path = field(default_factory=lambda: Path(_env(
        "MIRSAL_BUILDER_LIBRARY", str(ROOT.parent / "Mirsal-Builder" / "mirsal" / "out" / "library"))))
    diwan_mcp_url: str = field(default_factory=lambda: _env("DIWAN_MCP_URL"))
    diwan_mcp_token: str = field(default_factory=lambda: _env("DIWAN_MCP_TOKEN"))
    diwan_tool: str = field(default_factory=lambda: _env("DIWAN_MCP_TOOL", "upcoming_events"))
    # Demo only: pin Diwan's "today" (YYYY-MM-DD) so a past event still shows, e.g. 2026-10-07 → "Today".
    diwan_demo_date: str = field(default_factory=lambda: _env("DIWAN_DEMO_DATE"))
    supabase_url: str = field(default_factory=lambda: _env("SUPABASE_URL"))
    supabase_key: str = field(default_factory=lambda: _env("SUPABASE_ANON_KEY"))
    diwan_bucket: str = field(default_factory=lambda: _env("DIWAN_BUCKET", "diwan"))
    nadi_mcp_url: str = field(default_factory=lambda: _env("NADI_MCP_URL"))
    nadi_mcp_token: str = field(default_factory=lambda: _env("NADI_MCP_TOKEN"))
    builder_mcp_url: str = field(default_factory=lambda: _env("MIRSAL_BUILDER_MCP_URL"))
    builder_mcp_token: str = field(default_factory=lambda: _env("MIRSAL_BUILDER_MCP_TOKEN"))
    giphy_key: str = field(default_factory=lambda: _env("GIPHY_API_KEY"))
    data_dir: Path = field(default_factory=lambda: Path(_env("AGENTS_DATA_DIR", str(ROOT / "agents" / ".data"))))
    cleaner: Cleaner = field(default_factory=Cleaner)
    prices: Prices = field(default_factory=Prices)

    @property
    def openai_live(self) -> bool:
        return self.live and bool(self.openai_key)

    @property
    def nara_live(self) -> bool:
        return self.live and bool(self.nara_key)

    @property
    def tavily_live(self) -> bool:
        return self.live and bool(self.tavily_key)
