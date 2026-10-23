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
    luna_effort = os.getenv("LUNA_EFFORT", "low")  # routing: low was 2-4 s vs ~9.5 s at high with the same intents (23 Oct check)
    fast_model = os.getenv("FAST_MODEL", "gpt-6.1-sol")
    fast_effort = os.getenv("FAST_EFFORT", "medium")
    luna_timeout_s = float(os.getenv("LUNA_TIMEOUT_S", "20"))
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    nararouter_api_key = os.getenv("NARAROUTER_API_KEY", "")
    # AI demo personas. Founder rule (23 Oct, apps/api/.env): chat replies wait on the
    # user, so Luna (LUNA_MODEL at SOCIAL_EFFORT, 5/5 valid, ~3 s) runs first with agnes
    # via NaraRouter as fallback; feed posts/comments use agnes first, Luna fallback.
    # Values: agnes | luna | none.
    social_main = os.getenv("AI_main", "luna")
    social_fallback = os.getenv("fallback_model", "agnes")
    feed_main = os.getenv("FEED_AI_main", "agnes")
    feed_fallback = os.getenv("FEED_fallback_model", "luna")
    social_model = os.getenv("SOCIAL_MODEL", "agnes-2.5-flash")
    social_effort = os.getenv("SOCIAL_EFFORT", "medium")
    social_base_url = os.getenv("NARAROUTER_BASE_URL", "https://router.bynara.id/v1")
    social_timeout_s = float(os.getenv("SOCIAL_TIMEOUT_S", "35"))
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ml_eager = os.getenv("CELERY_EAGER", "1") == "1"
    sentiment_model = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    harsh_neg_threshold = float(os.getenv("HARSH_NEG_THRESHOLD", "0.8"))
    google_key = os.getenv("GOOGLE_PLACES_KEY", "")
    # Maps JavaScript keys are visible in the browser by design: use a separate key
    # restricted to your site (HTTP referrer) and to the Maps JavaScript API.
    google_maps_browser_key = os.getenv("GOOGLE_MAPS_BROWSER_KEY", "")
    google_oauth_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    google_oauth_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    google_oauth_redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    oauth_token_key = os.getenv("OAUTH_TOKEN_KEY", "")
    database_url = os.getenv("DATABASE_URL", "").strip()  # whitespace explicitly selects SQLite on Windows
    database_schema = os.getenv("DATABASE_SCHEMA", "").strip()  # Supabase backend-only schema; empty preserves existing deployments
    widget_port = int(os.getenv("WIDGET_PORT", "8001"))  # separate mini-app origin; 0 disables
    merchant_pin = os.getenv("MERCHANT_PIN", "")  # sandbox merchant sign-in; generated into data/ when unset
    web_dir = ROOT / "apps" / "web"
    lab_dir = web_dir  # backward compatibility alias
    data_dir = Path(os.getenv("APP_DATA_DIR", str(ROOT / "apps" / "api" / "data")))


settings = Settings()
