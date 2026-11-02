"""One-shot: fixture counts vs live DB (Postgres if DATABASE_URL, else note SQLite seed path)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "app" / "fixtures" / "community"
CHAT = ROOT / "app" / "fixtures" / "chat_personas.json"


def fixture_counts() -> dict:
    personas = json.loads((FIXTURES / "personas.json").read_text(encoding="utf-8"))
    if isinstance(personas, dict):
        personas = personas.get("personas", [])
    posts = comments = 0
    for path in FIXTURES.glob("*.json"):
        if path.name == "personas.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for post in data.get("posts", []):
            posts += 1
            comments += len(post.get("comments", []))
    chat = json.loads(CHAT.read_text(encoding="utf-8"))
    return {
        "fixture_personas": len(personas),
        "fixture_communities": len([p for p in FIXTURES.glob("*.json") if p.name != "personas.json"]),
        "fixture_posts": posts,
        "fixture_comments": comments,
        "fixture_chat_personas": len(chat.get("personas", [])),
        "fixture_chat_threads": len(chat.get("threads", [])),
        "fixture_chat_messages": sum(len(t.get("messages", [])) for t in chat.get("threads", [])),
    }


def redact(url: str) -> str:
    return re.sub(r":[^:@]+@", ":***@", url)


def main() -> None:
    print("FIXTURES", json.dumps(fixture_counts(), indent=2))
    env_path = ROOT / ".env"
    url = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip("\"'")
                break
    print("DATABASE_URL", redact(url) if url else "(missing)")
    if not url or url.startswith("sqlite"):
        print("SUPABASE", "not configured as Postgres — community seed loads into API ActionStore SQLite on first request")
        return
    try:
        import psycopg
    except ImportError:
        print("SUPABASE", "psycopg missing")
        return
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                print("connected", cur.fetchone()[0])
                for schema in ("dubaiio", "public"):
                    for table in (
                        "personas",
                        "posts",
                        "comments",
                        "communities",
                        "chat_threads",
                        "chat_messages",
                        "social_personas",
                    ):
                        try:
                            cur.execute(f"SELECT count(*) FROM {schema}.{table}")
                            print(f"{schema}.{table}", cur.fetchone()[0])
                        except Exception as exc:  # noqa: BLE001
                            conn.rollback()
                            print(f"{schema}.{table}", "MISSING", str(exc).split("\n")[0][:100])
    except Exception as exc:  # noqa: BLE001
        print("SUPABASE_CONNECT_FAIL", type(exc).__name__, str(exc)[:240])


if __name__ == "__main__":
    main()
