"""Runtime configuration loaded from environment variables (WP-A)."""
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("TM_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
    test_database_url: str = os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
    broker_url: str = os.environ.get("TM_BROKER_URL", "amqp://guest:guest@localhost:5682//")
    redis_url: str = os.environ.get("TM_REDIS_URL", "redis://localhost:6390/0")
    lmstudio_url: str = os.environ.get("TM_LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
    lmstudio_model: str = os.environ.get("TM_LMSTUDIO_MODEL", "qwen/qwen3-4b-2507")
    cloud_model: str = os.environ.get("TM_CLOUD_MODEL", "claude-haiku-4-5-20251001")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    admin_token: str = os.environ.get("TM_ADMIN_TOKEN", "")
    agent_cli_cmd: str = os.environ.get(
        "TM_AGENT_CLI_CMD",
        "claude -p --model {model} --effort medium --output-format json --tools \"\" --disable-slash-commands",
    )
    governor_usd_per_month: float = float(os.environ.get("TM_GOVERNOR_USD_PER_MONTH", "0.18"))
    p0_fallback_seconds: int = int(os.environ.get("TM_P0_FALLBACK_SECONDS", "20"))
    p1_fallback_seconds: int = int(os.environ.get("TM_P1_FALLBACK_SECONDS", "600"))
    lease_seconds: int = int(os.environ.get("TM_LEASE_SECONDS", "300"))
    cloud_rate_in_per_1m: float = float(os.environ.get("TM_CLOUD_RATE_IN_PER_1M", "1.00"))
    cloud_rate_out_per_1m: float = float(os.environ.get("TM_CLOUD_RATE_OUT_PER_1M", "5.00"))
    packet_token_budget: int = int(os.environ.get("TM_PACKET_TOKEN_BUDGET", "4000"))
    semantic_enabled: bool = os.environ.get("TM_SEMANTIC", "1").strip().lower() not in ("0", "false", "no", "off")
    semantic_model: str = os.environ.get("TM_SEMANTIC_MODEL", "BAAI/bge-m3")
    semantic_min_sim: float = float(os.environ.get("TM_SEMANTIC_MIN_SIM", "0.40"))


def get_settings() -> Settings:
    """Read fresh settings from current os.environ."""
    return Settings(
        database_url=os.environ.get("TM_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm"),
        test_database_url=os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm"),
        broker_url=os.environ.get("TM_BROKER_URL", "amqp://guest:guest@localhost:5682//"),
        redis_url=os.environ.get("TM_REDIS_URL", "redis://localhost:6390/0"),
        lmstudio_url=os.environ.get("TM_LMSTUDIO_URL", "http://127.0.0.1:1234/v1"),
        lmstudio_model=os.environ.get("TM_LMSTUDIO_MODEL", "qwen/qwen3-4b-2507"),
        cloud_model=os.environ.get("TM_CLOUD_MODEL", "claude-haiku-4-5-20251001"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        admin_token=os.environ.get("TM_ADMIN_TOKEN", ""),
        agent_cli_cmd=os.environ.get(
            "TM_AGENT_CLI_CMD",
            "claude -p --model {model} --effort medium --output-format json --tools \"\" --disable-slash-commands",
        ),
        governor_usd_per_month=float(os.environ.get("TM_GOVERNOR_USD_PER_MONTH", "0.18")),
        p0_fallback_seconds=int(os.environ.get("TM_P0_FALLBACK_SECONDS", "20")),
        p1_fallback_seconds=int(os.environ.get("TM_P1_FALLBACK_SECONDS", "600")),
        lease_seconds=int(os.environ.get("TM_LEASE_SECONDS", "300")),
        cloud_rate_in_per_1m=float(os.environ.get("TM_CLOUD_RATE_IN_PER_1M", "1.00")),
        cloud_rate_out_per_1m=float(os.environ.get("TM_CLOUD_RATE_OUT_PER_1M", "5.00")),
        packet_token_budget=int(os.environ.get("TM_PACKET_TOKEN_BUDGET", "4000")),
        semantic_enabled=os.environ.get("TM_SEMANTIC", "1").strip().lower() not in ("0", "false", "no", "off"),
        semantic_model=os.environ.get("TM_SEMANTIC_MODEL", "BAAI/bge-m3"),
        semantic_min_sim=float(os.environ.get("TM_SEMANTIC_MIN_SIM", "0.40")),
    )


settings = get_settings()
