"""Settings. Keys live in apps/api/.env (or demo/.env during the lab phase) and
never reach the browser. Model IDs come only from here (CLAUDE.md: no model IDs
in code)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
for env_file in (ROOT / "apps" / "api" / ".env",):
    load_dotenv(env_file, override=False)

# A stale CA-bundle path set elsewhere on this machine breaks TLS; ignore it.
for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
    value = os.environ.get(var)
    if value and not Path(value).exists():
        os.environ.pop(var)


class Settings:
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    # Luna understands every turn. Founder choice (13 Oct): gpt-6-luna at high
    # reasoning effort; gpt-6.1-sol at medium is the faster alternative.
    luna_model = os.getenv("LUNA_MODEL", "gpt-6-luna")
    luna_effort = os.getenv("LUNA_EFFORT", "high")
    fast_model = os.getenv("FAST_MODEL", "gpt-6.1-sol")
    fast_effort = os.getenv("FAST_EFFORT", "medium")
    luna_timeout_s = float(os.getenv("LUNA_TIMEOUT_S", "20"))
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    google_key = os.getenv("GOOGLE_PLACES_KEY", "")
    google_oauth_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    google_oauth_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    google_oauth_redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    oauth_token_key = os.getenv("OAUTH_TOKEN_KEY", "")
    database_url = os.getenv("DATABASE_URL", "")  # Postgres 16 + pgvector; empty -> SQLite in data/
    widget_port = int(os.getenv("WIDGET_PORT", "8001"))  # separate mini-app origin; 0 disables
    merchant_pin = os.getenv("MERCHANT_PIN", "")  # sandbox merchant sign-in; generated into data/ when unset
    web_dir = ROOT / "apps" / "web"
    lab_dir = web_dir  # backward compatibility alias
    data_dir = ROOT / "apps" / "api" / "data"


settings = Settings()
