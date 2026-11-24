"""cm_ tables + demo seed for the Community social core.

Owner comes from the cookie session (``actions.ActionStore.owner``); callers
never set owner/provenance. User content is ``user_supplied``; the seeded demo
group/posts are ``demo_fixture``. Adults-only (D11): profiles with a non-adult
age band are refused by the routes layer.
"""
from datetime import datetime, timezone
from uuid import uuid4

ADULT_BANDS = {"18+", "adult", "18-24", "25-34", "35-44", "45-54", "55+", "18_plus", "18plus"}
NON_ADULT_BANDS = {
    "under-18", "under_18", "under18", "<18", "13-17", "15-17", "16-17", "17",
    "under-13", "under_13", "under13", "<13", "child", "minor", "teen", "13", "14", "15", "16",
}

DDL = (
    """CREATE TABLE IF NOT EXISTS cm_profiles (
        owner TEXT PRIMARY KEY, handle TEXT NOT NULL, display_name TEXT NOT NULL DEFAULT '',
        bio TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '',
        interests TEXT NOT NULL DEFAULT '[]', age_band TEXT NOT NULL,
        privacy TEXT NOT NULL DEFAULT 'public', provenance TEXT NOT NULL DEFAULT 'user_supplied',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS cm_profiles_handle ON cm_profiles(handle)",
    """CREATE TABLE IF NOT EXISTS cm_follows (
        follower TEXT NOT NULL, followee TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(follower, followee))""",
    """CREATE TABLE IF NOT EXISTS cm_groups (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, handle TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '', visibility TEXT NOT NULL DEFAULT 'public',
        owner TEXT NOT NULL, provenance TEXT NOT NULL DEFAULT 'user_supplied',
        created_at TEXT NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS cm_groups_handle ON cm_groups(handle)",
    """CREATE TABLE IF NOT EXISTS cm_group_members (
        group_id TEXT NOT NULL, owner TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member',
        status TEXT NOT NULL DEFAULT 'active', invited_by TEXT,
        created_at TEXT NOT NULL, PRIMARY KEY(group_id, owner))""",
    """CREATE TABLE IF NOT EXISTS cm_posts (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, group_id TEXT,
        text TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
        pinned INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0,
        provenance TEXT NOT NULL DEFAULT 'user_supplied',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS cm_posts_feed ON cm_posts(group_id, created_at)",
    """CREATE TABLE IF NOT EXISTS cm_post_revisions (
        post_id TEXT NOT NULL, revision INTEGER NOT NULL, text TEXT NOT NULL,
        created_at TEXT NOT NULL, PRIMARY KEY(post_id, revision))""",
    """CREATE TABLE IF NOT EXISTS cm_comments (
        id TEXT PRIMARY KEY, post_id TEXT NOT NULL, owner TEXT NOT NULL,
        parent_id TEXT, text TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'user_supplied', created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS cm_comments_post ON cm_comments(post_id, created_at)",
    """CREATE TABLE IF NOT EXISTS cm_reactions (
        owner TEXT NOT NULL, target_type TEXT NOT NULL DEFAULT 'post',
        target_id TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'like',
        created_at TEXT NOT NULL, PRIMARY KEY(owner, target_type, target_id, kind))""",
    """CREATE TABLE IF NOT EXISTS cm_bookmarks (
        owner TEXT NOT NULL, post_id TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(owner, post_id))""",
    """CREATE TABLE IF NOT EXISTS cm_group_moderation_log (
        id TEXT PRIMARY KEY, group_id TEXT NOT NULL, actor TEXT NOT NULL,
        action TEXT NOT NULL, target_type TEXT, target_id TEXT,
        detail TEXT NOT NULL DEFAULT '', undone INTEGER NOT NULL DEFAULT 0,
        undone_by TEXT, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS cm_notifications (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, actor TEXT,
        kind TEXT NOT NULL, post_id TEXT, comment_id TEXT, group_id TEXT,
        text TEXT NOT NULL DEFAULT '', dedupe_key TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS cm_notifications_dedupe ON cm_notifications(dedupe_key)",
)
TABLES = ("cm_profiles", "cm_follows", "cm_groups", "cm_group_members", "cm_posts",
          "cm_post_revisions", "cm_comments", "cm_reactions", "cm_bookmarks",
          "cm_group_moderation_log", "cm_notifications")

DEMO_GROUP_ID = "demo-marina-foodies"
DEMO_POST_IDS = ("demo-post-01", "demo-post-02")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_adult_band(age_band: str) -> bool:
    return (age_band or "").strip().lower() in ADULT_BANDS


def is_non_adult_band(age_band: str) -> bool:
    return (age_band or "").strip().lower() in NON_ADULT_BANDS


def setup(store):
    if getattr(store, "_community_ready", False):
        return
    for statement in DDL:
        store.db.execute(statement)
    if store.db.dialect == "postgres":
        for table in TABLES:
            try:
                store.db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            except Exception:
                pass
    stamp = now()
    store.db.execute(
        "INSERT OR IGNORE INTO cm_groups (id,name,handle,description,visibility,owner,provenance,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (DEMO_GROUP_ID, "Marina Foodies (Demo)", "demo-marina-foodies",
         "Demo group seeded for the contest demo.", "public", "demo", "demo_fixture", stamp))
    for pid, text in ((DEMO_POST_IDS[0], "Demo: best shawarma near the Marina tram stop?"),
                      (DEMO_POST_IDS[1], "Demo: Saturday morning walk around the lake.")):
        store.db.execute(
            "INSERT OR IGNORE INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at) VALUES (?,?,?,?,1,0,0,'demo_fixture',?,?)",
            (pid, "demo", DEMO_GROUP_ID, text, stamp, stamp))
    store.db.commit()
    store._community_ready = True


def notify(store, recipient, actor, kind, dedupe_key, text="", post_id=None, comment_id=None, group_id=None):
    """Insert a deduped notification; returns the row id or None if deduped/self."""
    if not recipient or recipient == actor:
        return None
    nid = uuid4().hex
    try:
        store.db.execute(
            "INSERT OR IGNORE INTO cm_notifications (id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at) VALUES (?,?,?,?,?,?,?,?,?,0,?)",
            (nid, recipient, actor, kind, post_id, comment_id, group_id, text, dedupe_key, now()))
    except Exception:
        return None
    row = store.db.execute("SELECT id FROM cm_notifications WHERE dedupe_key=?", (dedupe_key,)).fetchone()
    return row[0] if row else None
