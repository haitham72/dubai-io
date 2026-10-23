"""Communities, chats and contacts (demo-grade, founder decision 23 Oct).

Seeded communities, posts, stories and group conversations are demo fixtures and
say so (`provenance: demo_fixture`). What a user adds (posts, messages, contacts,
calls started from the app) is owner-scoped and deletable. Community content is
untrusted text: it is never handed to the assistant as instructions and never
turned into profile facts or hypotheses about the user.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .actions import COOKIE, engine
from . import social_generation as social
from . import ml_tasks

router = APIRouter(tags=["communities"])
clock = lambda: datetime.now(timezone.utc)

DDL = (
    """CREATE TABLE IF NOT EXISTS personas (id TEXT PRIMARY KEY, name TEXT NOT NULL, handle TEXT NOT NULL, emoji TEXT NOT NULL,
        bio TEXT NOT NULL, area TEXT NOT NULL, provenance TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS communities (id TEXT PRIMARY KEY, name TEXT NOT NULL, handle TEXT NOT NULL, topic TEXT NOT NULL,
        about TEXT NOT NULL, image TEXT NOT NULL, members_base INTEGER NOT NULL, provenance TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS community_members (owner TEXT NOT NULL, community_id TEXT NOT NULL, joined_at TEXT NOT NULL,
        PRIMARY KEY(owner, community_id))""",
    """CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, community_id TEXT NOT NULL, owner TEXT, persona_id TEXT, author TEXT NOT NULL,
        kind TEXT NOT NULL, text TEXT NOT NULL, image TEXT, created_at TEXT NOT NULL, likes INTEGER NOT NULL, provenance TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS posts_feed ON posts(kind, created_at)",
    """CREATE TABLE IF NOT EXISTS comments (id TEXT PRIMARY KEY, post_id TEXT NOT NULL, owner TEXT, persona_id TEXT, author TEXT NOT NULL,
        text TEXT NOT NULL, created_at TEXT NOT NULL, likes INTEGER NOT NULL, provenance TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS comments_post ON comments(post_id, created_at)",
    "CREATE TABLE IF NOT EXISTS hidden_posts (owner TEXT NOT NULL, post_id TEXT NOT NULL, reason TEXT, at TEXT NOT NULL, PRIMARY KEY(owner, post_id))",
    "CREATE TABLE IF NOT EXISTS votes (target_type TEXT NOT NULL, target_id TEXT NOT NULL, owner TEXT NOT NULL, value INTEGER NOT NULL, PRIMARY KEY(target_type, target_id, owner))",
    """CREATE TABLE IF NOT EXISTS chat_threads (id TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
        community_id TEXT, created_at TEXT NOT NULL, PRIMARY KEY(owner, id))""",
    """CREATE TABLE IF NOT EXISTS chat_messages (id TEXT PRIMARY KEY, owner TEXT NOT NULL, thread_id TEXT NOT NULL, author TEXT NOT NULL,
        text TEXT NOT NULL, at TEXT NOT NULL, provenance TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS chat_messages_thread ON chat_messages(owner, thread_id, at)",
    "CREATE TABLE IF NOT EXISTS chat_reads (owner TEXT NOT NULL, thread_id TEXT NOT NULL, read_at TEXT NOT NULL, PRIMARY KEY(owner, thread_id))",
    "CREATE TABLE IF NOT EXISTS contacts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS call_log (id TEXT PRIMARY KEY, owner TEXT NOT NULL, contact_id TEXT, name TEXT NOT NULL, phone TEXT NOT NULL, at TEXT NOT NULL)",
)
TABLES = ("personas", "communities", "community_members", "posts", "comments", "hidden_posts", "chat_threads", "chat_messages",
          "chat_reads", "contacts", "call_log", "votes")

FIXTURES = Path(__file__).parent / "fixtures" / "community"
MEDIA = {f"media/{name}.jpg" for name in ("ac", "barber-dark", "barber", "cafe-bulbs", "cafe-counter", "cloth", "coffee", "food", "grill",
         "home-green", "home", "laundry-shelf", "laundry", "marina-night", "marina", "pets", "puppy", "rest-room", "rest-water",
         "shawarma", "shoes", "spread", "vet")}
# Small built-in seed, used only when the generated fixture files are absent.
BUILTIN_PERSONAS = [
    {"id": "p01", "name": "Sara K.", "handle": "sarak", "emoji": "🌴", "bio": "Designer in JLT.", "area": "JLT"},
    {"id": "p02", "name": "Omar", "handle": "omar_dxb", "emoji": "🏃", "bio": "Runs before work.", "area": "Dubai Marina"},
]
BUILTIN_COMMUNITIES = [
    {"id": "marina-foodies", "name": "Marina Foodies", "handle": "marinafoodies", "topic": "Food", "image": "media/food.jpg", "members": 18400,
     "about": "Where to eat around Dubai Marina and JBR, from shawarma to brunch.",
     "stories": [{"author": "p02", "text": "Friday grill night on the promenade", "image": "media/grill.jpg", "hours_ago": 3}],
     "posts": [{"id": "marina-foodies-01", "author": "p01", "text": "Best lasagna in the Marina right now? 🍝", "image": "media/grill.jpg",
                "hours_ago": 2, "likes": 40, "comments": [{"author": "p02", "text": "Try the place by the tram stop 👌", "hours_ago": 1, "likes": 3}]}]},
    {"id": "jlt-runners", "name": "JLT Runners", "handle": "jltrunners", "topic": "Fitness", "image": "media/marina.jpg", "members": 2630,
     "about": "Early runs around the JLT lakes and Marina walk.",
     "stories": [{"author": "p02", "text": "Sunrise over the lakes", "image": "media/marina.jpg", "hours_ago": 5}],
     "posts": [{"id": "jlt-runners-01", "author": "p02", "text": "Saturday 6:30 easy 5K, meet at the fountain 🏃", "image": None,
                "hours_ago": 6, "likes": 22, "comments": []}]},
]


GROUPS = (
    ("group:building", "Building 7 neighbours", (("Maya", "Water is back on all floors 💧"), ("Karim", "Thanks! Gym reopens at 6 tomorrow."))),
    ("group:friday-lunch", "Friday lunch crew", (("Nadia", "Same place as last week?"), ("Tom", "Let’s try somewhere new near the Marina 🍽️"))),
)


def load_seed():
    """Generated fixtures (apps/api/app/fixtures/community) when present, else the built-in seed. Fails loudly on bad data."""
    path = FIXTURES / "personas.json"
    files = sorted(f for f in FIXTURES.glob("*.json") if f.name != "personas.json") if FIXTURES.is_dir() else []
    if path.exists() and files:
        personas = json.loads(path.read_text(encoding="utf-8"))
        groups = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    else:
        personas, groups = BUILTIN_PERSONAS, BUILTIN_COMMUNITIES
    ids = {p["id"] for p in personas}
    assert len(ids) == len(personas), "duplicate persona id"
    for g in groups:
        assert g["image"] in MEDIA and isinstance(g["members"], int), g["id"]
        for story in g["stories"]:
            assert story["author"] in ids and story["image"] in MEDIA, (g["id"], story)
        for post in g["posts"]:
            assert post["author"] in ids and (post["image"] is None or post["image"] in MEDIA), post["id"]
            assert 0 < len(post["text"]) <= 500, post["id"]
            seen_comments = set()
            for index, comment in enumerate(post["comments"]):
                assert not comment.get("parent_id") or comment["parent_id"] in seen_comments, post["id"]
                seen_comments.add(f"{post['id']}-c{index:02d}")
                assert comment["author"] in ids and 0 < len(comment["text"]) <= 400, post["id"]
    return personas, groups


def setup(store):
    if getattr(store, "_communities_ready", False):
        return
    for statement in DDL:
        store.db.execute(statement)
    social.migrate(store)
    ml_tasks.setup(store)
    if store.db.dialect == "postgres":
        for table in TABLES:
            store.db.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    personas, groups = load_seed()
    personas = personas + social.chat_fixture()["personas"] + social.legacy_personas(GROUPS)
    names = {p["id"]: p["name"] for p in personas}
    now = clock()
    ago = lambda hours: (now - timedelta(hours=max(0, hours))).isoformat()
    for p in personas:
        store.db.execute("INSERT OR IGNORE INTO personas (id,name,handle,emoji,bio,area,provenance) VALUES (?,?,?,?,?,?,?)",
                         (p["id"], p["name"], p["handle"], p["emoji"], p["bio"], p["area"], "demo_fixture"))
        store.db.execute("UPDATE personas SET avatar=?, profile=? WHERE id=?", (p.get("avatar"), json.dumps(p), p["id"]))
    for g in groups:
        store.db.execute("INSERT OR IGNORE INTO communities VALUES (?,?,?,?,?,?,?,?)",
                         (g["id"], g["name"], g["handle"], g["topic"], g["about"], g["image"], g["members"], "demo_fixture"))
        for i, story in enumerate(g["stories"]):
            store.db.execute("INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"{g['id']}-story-{i}", g["id"], None, story["author"],
                             names[story["author"]], "story", story["text"], story["image"], ago(story["hours_ago"]), 0, "demo_fixture"))
        for post in g["posts"]:
            store.db.execute("INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (post["id"], g["id"], None, post["author"],
                             names[post["author"]], "post", post["text"], post["image"], ago(post["hours_ago"]), post["likes"], "demo_fixture"))
            for j, c in enumerate(post["comments"]):
                store.db.execute("INSERT OR IGNORE INTO comments (id,post_id,owner,persona_id,author,text,created_at,likes,provenance) VALUES (?,?,?,?,?,?,?,?,?)", (f"{post['id']}-c{j:02d}", post["id"], None, c["author"],
                                 names[c["author"]], c["text"], ago(c["hours_ago"]), c["likes"], "demo_fixture"))
                parent = c.get("parent_id")
                if parent:
                    store.db.execute("UPDATE comments SET parent_id=? WHERE id=? AND provenance='demo_fixture'", (parent, f"{post['id']}-c{j:02d}"))
    store.db.commit()
    store._communities_ready = True


def scope(request):
    store = engine().store
    return store, store.owner(request.cookies.get(COOKIE))


POST_SQL = """SELECT p.id,p.community_id,p.owner,p.author,p.kind,p.text,p.image,p.created_at,p.provenance,c.name,c.handle,
        p.likes,p.persona_id,pe.handle,pe.emoji,pe.avatar,(SELECT COUNT(*) FROM comments m WHERE m.post_id=p.id AND (m.owner IS NULL OR m.owner=?))
    FROM posts p JOIN communities c ON c.id=p.community_id LEFT JOIN personas pe ON pe.id=p.persona_id"""


def present_post(row, joined):
    pid, community, owner, author, kind, text, image, at, provenance, name, handle, likes, persona, phandle, emoji, avatar, comments = row
    return {"id": pid, "community": {"id": community, "name": name, "handle": handle, "joined": community in joined},
            "author": {"name": author, "handle": phandle or "you", "emoji": emoji or "🙂", "persona_id": persona, "avatar": avatar},
            "mine": owner is not None and persona is None, "kind": kind, "text": text, "image": image, "likes": likes, "comments": comments,
            "created_at": at, "provenance": provenance}


def joined_ids(store, owner):
    return {r[0] for r in store.db.execute("SELECT community_id FROM community_members WHERE owner=?", (owner,)).fetchall()}


@router.get("/api/communities")
def list_communities(request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        joined = joined_ids(store, owner)
        rows = store.db.execute("SELECT id,name,handle,topic,about,image,members_base,provenance FROM communities ORDER BY members_base DESC").fetchall()
        return {"communities": [{"id": r[0], "name": r[1], "handle": r[2], "topic": r[3], "about": r[4], "image": r[5],
                                 "members": r[6] + (r[0] in joined), "joined": r[0] in joined, "provenance": r[7]} for r in rows]}


def community(store, community_id):
    row = store.db.execute("SELECT id,name FROM communities WHERE id=?", (community_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Community not found")
    return row


@router.post("/api/communities/{community_id}/join")
def join(community_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        community(store, community_id)
        store.db.execute("INSERT OR IGNORE INTO community_members VALUES (?,?,?)", (owner, community_id, clock().isoformat()))
        store.db.commit()
    return list_communities(request)


@router.post("/api/communities/{community_id}/leave")
def leave(community_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        store.db.execute("DELETE FROM community_members WHERE owner=? AND community_id=?", (owner, community_id))
        store.db.commit()
    return list_communities(request)


@router.get("/api/feed")
def feed(request: Request, limit: int = Query(default=20, ge=1, le=50), community_id: str | None = None,
         sort: str = Query(default="new", pattern="^(new|top|hot)$")):
    """Posts from joined communities first, then discovery; hidden posts and other users' private posts excluded."""
    store, owner = scope(request)
    with store.lock:
        setup(store)
        joined = joined_ids(store, owner)
        hidden = {r[0] for r in store.db.execute("SELECT post_id FROM hidden_posts WHERE owner=?", (owner,)).fetchall()}
        rows = store.db.execute(POST_SQL + " WHERE (p.owner IS NULL OR p.owner=?) ORDER BY p.created_at DESC", (owner, owner)).fetchall()
        if community_id:
            community(store, community_id)
        posts = [present_post(r, joined) for r in rows if r[0] not in hidden and (not community_id or r[1] == community_id)]
        sums, mine = vote_maps(store, owner, "post", [p["id"] for p in posts])
        for p in posts:
            p["score"] = p["likes"] + sums.get(p["id"], 0)
            p["my_vote"] = mine.get(p["id"], 0)
        stories = {}
        for p in posts:
            if p["kind"] == "story" and p["community"]["id"] not in stories:
                stories[p["community"]["id"]] = {"community": p["community"], "author": p["author"], "image": p["image"], "at": p["created_at"],
                                                  "provenance": p["provenance"]}
        items = [p for p in posts if p["kind"] == "post"]
        if sort == "top":
            items.sort(key=lambda p: (not p["community"]["joined"], -p["score"]))
        elif sort == "hot":
            items.sort(key=lambda p: (not p["community"]["joined"], -hot_score(p["score"], p["created_at"])))
        else:
            items.sort(key=lambda p: (not p["community"]["joined"],))  # stable: newest within each group
        return {"posts": items[:limit], "stories": sorted(stories.values(), key=lambda s: not s["community"]["joined"])}


@router.get("/api/communities/{community_id}/stories")
def stories(community_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        name = community(store, community_id)[1]
        hidden = {r[0] for r in store.db.execute("SELECT post_id FROM hidden_posts WHERE owner=?", (owner,)).fetchall()}
        rows = store.db.execute("""SELECT p.id,p.author,p.text,p.image,p.created_at,p.provenance,pe.emoji FROM posts p
            LEFT JOIN personas pe ON pe.id=p.persona_id
            WHERE p.community_id=? AND p.kind='story' AND (p.owner IS NULL OR p.owner=?) ORDER BY p.created_at""", (community_id, owner)).fetchall()
        return {"community": {"id": community_id, "name": name},
                "frames": [{"id": r[0], "author": r[1], "emoji": r[6] or "🙂", "text": r[2], "image": r[3], "created_at": r[4], "provenance": r[5]}
                           for r in rows if r[0] not in hidden]}


class PostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    request_id: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("text")
    @classmethod
    def trimmed(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Write something first")
        return value


@router.post("/api/communities/{community_id}/posts")
def create_post(community_id: str, body: PostIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        community(store, community_id)
        if community_id not in joined_ids(store, owner):
            raise HTTPException(409, "Join the community before posting")
        result, fresh = social.claim(store, owner, "post", community_id, body)
        if not fresh:
            return result
        pid = result["id"]
        store.db.execute("INSERT INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (pid, community_id, owner, None, "You", "post", body.text, None,
                         clock().isoformat(), 0, "user_supplied"))
        store.db.commit()
    return social.respond(store, owner, result, "post", pid)


def visible_post(store, owner, post_id):
    if not store.db.execute("SELECT 1 FROM posts WHERE id=? AND (owner IS NULL OR owner=?)", (post_id, owner)).fetchone():
        raise HTTPException(404, "Post not found")


@router.get("/api/posts/{post_id}")
def get_post(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        row = store.db.execute(POST_SQL + " WHERE p.id=? AND p.kind='post' AND (p.owner IS NULL OR p.owner=?) AND NOT EXISTS (SELECT 1 FROM hidden_posts h WHERE h.owner=? AND h.post_id=p.id)", (owner, post_id, owner, owner)).fetchone()
        if not row:
            raise HTTPException(404, "Post not found")
        post = present_post(row, joined_ids(store, owner))
        sums, mine = vote_maps(store, owner, "post", [post["id"]])
        post["score"] = post["likes"] + sums.get(post["id"], 0)
        post["my_vote"] = mine.get(post["id"], 0)
        return {"post": post}


@router.get("/api/posts/{post_id}/comments")
def comments(post_id: str, request: Request, sort: str = Query(default="new", pattern="^(new|top)$")):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        visible_post(store, owner, post_id)
        rows = store.db.execute("""SELECT m.id,m.author,m.text,m.created_at,m.likes,m.provenance,m.owner,pe.handle,pe.emoji,m.persona_id,pe.avatar,m.parent_id,m.model,
            l.sentiment,l.neg,l.topics,l.harsh,l.model FROM comments m
            LEFT JOIN personas pe ON pe.id=m.persona_id LEFT JOIN comment_labels l ON l.comment_id=m.id
            WHERE m.post_id=? AND (m.owner IS NULL OR m.owner=?) ORDER BY m.created_at""",
            (post_id, owner)).fetchall()
        out = [{"id": r[0], "author": {"name": r[1], "handle": r[7] or "you", "emoji": r[8] or "🙂", "persona_id": r[9], "avatar": r[10]}, "text": r[2],
                "created_at": r[3], "likes": r[4], "provenance": r[5], "mine": r[6] is not None and r[9] is None, "parent_id": r[11], "model": r[12],
                "analysis": None if r[13] is None else {"sentiment": r[13], "neg": r[14], "topics": json.loads(r[15] or "[]"),
                "harsh": bool(r[16]), "harsh_basis": "sentiment_negative", "model": r[17]}} for r in rows]
        sums, mine = vote_maps(store, owner, "comment", [m["id"] for m in out])
        for m in out:
            m["score"] = m["likes"] + sums.get(m["id"], 0)
            m["my_vote"] = mine.get(m["id"], 0)
        if sort == "top":
            out.sort(key=lambda m: -m["score"])
        return {"comments": out}


class CommentIn(PostIn):
    parent_id: str | None = Field(default=None, max_length=100)


@router.post("/api/posts/{post_id}/comments")
def add_comment(post_id: str, body: CommentIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        visible_post(store, owner, post_id)
        if body.parent_id and not store.db.execute("SELECT 1 FROM comments WHERE id=? AND post_id=? AND (owner IS NULL OR owner=?)", (body.parent_id, post_id, owner)).fetchone():
            raise HTTPException(404, "Reply not found")
        result, fresh = social.claim(store, owner, "comment", post_id, body)
        if not fresh:
            return result
        cid = result["id"]
        store.db.execute("INSERT INTO comments (id,post_id,owner,persona_id,author,text,created_at,likes,provenance,parent_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (cid, post_id, owner, None, "You", body.text, clock().isoformat(), 0, "user_supplied", body.parent_id))
        store.db.commit()
    ml_tasks.dispatch_comment(store, owner, cid, post_id, body.text, clock().isoformat())
    return social.respond(store, owner, result, "comment", post_id)


class HideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(default=None, max_length=40)


@router.post("/api/posts/{post_id}/hide")
def hide_post(post_id: str, body: HideIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        visible_post(store, owner, post_id)
        store.db.execute("INSERT OR IGNORE INTO hidden_posts VALUES (?,?,?,?)", (owner, post_id, body.reason, clock().isoformat()))
        store.db.commit()
        return {"hidden": post_id}


# ---------------------------------------------------------------- chats
def ensure_threads(store, owner):
    """Each owner gets the demo groups once, plus one thread per joined community."""
    now = clock()
    social.ensure_chats(store, owner, now)
    for tid, title, lines in GROUPS:
        if store.db.execute("SELECT 1 FROM chat_threads WHERE owner=? AND id=?", (owner, tid)).fetchone():
            continue
        store.db.execute("INSERT INTO chat_threads VALUES (?,?,?,?,?,?)", (tid, owner, "group", title, None, now.isoformat()))
        for i, (author, text) in enumerate(lines):
            store.db.execute("INSERT INTO chat_messages (id,owner,thread_id,author,text,at,provenance) VALUES (?,?,?,?,?,?,?)", (uuid4().hex, owner, tid, author, text,
                             (now - timedelta(minutes=40 - i * 10)).isoformat(), "demo_fixture"))
    social.bind_legacy_messages(store, owner, GROUPS)
    for cid in joined_ids(store, owner):
        tid = "community:" + cid
        if not store.db.execute("SELECT 1 FROM chat_threads WHERE owner=? AND id=?", (owner, tid)).fetchone():
            name = community(store, cid)[1]
            store.db.execute("INSERT INTO chat_threads VALUES (?,?,?,?,?,?)", (tid, owner, "community", name, cid, now.isoformat()))
            store.db.execute("INSERT INTO chat_messages (id,owner,thread_id,author,text,at,provenance) VALUES (?,?,?,?,?,?,?)", (uuid4().hex, owner, tid, name,
                             f"Welcome to {name}. Be kind; posts here are from members, not Dubai-io.", now.isoformat(), "demo_fixture"))


def thread_list(store, owner):
    rows = store.db.execute("""SELECT t.id,t.kind,t.title,t.community_id,
            (SELECT text FROM chat_messages m WHERE m.owner=t.owner AND m.thread_id=t.id ORDER BY at DESC LIMIT 1),
            (SELECT author FROM chat_messages m WHERE m.owner=t.owner AND m.thread_id=t.id ORDER BY at DESC LIMIT 1),
            (SELECT at FROM chat_messages m WHERE m.owner=t.owner AND m.thread_id=t.id ORDER BY at DESC LIMIT 1),
            (SELECT COUNT(*) FROM chat_messages m WHERE m.owner=t.owner AND m.thread_id=t.id AND m.author!='You'
                AND m.at > COALESCE((SELECT read_at FROM chat_reads r WHERE r.owner=t.owner AND r.thread_id=t.id), ''))
        FROM chat_threads t WHERE t.owner=? AND (t.community_id IS NULL OR EXISTS (SELECT 1 FROM community_members cm WHERE cm.owner=t.owner AND cm.community_id=t.community_id))""", (owner,)).fetchall()
    threads = [{"id": r[0], "kind": r[1], "title": r[2], "community_id": r[3], "last": r[4] or "", "last_author": r[5] or "",
                "at": r[6] or "", "unread": int(r[7] or 0)} for r in rows]
    for thread in threads:
        thread.update(social.thread_identity(store, thread["id"]))
    return sorted(threads, key=lambda t: t["at"], reverse=True)


@router.get("/api/chats")
def chats(request: Request, filter: str = Query(default="all", pattern="^(all|unread|groups|communities)$")):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        ensure_threads(store, owner)
        store.db.commit()
        threads = thread_list(store, owner)
    keep = {"all": lambda t: True, "unread": lambda t: t["unread"] > 0,
            "groups": lambda t: t["kind"] == "group", "communities": lambda t: t["kind"] == "community"}[filter]
    return {"threads": [t for t in threads if keep(t)], "unread": sum(t["unread"] for t in threads)}


def own_thread(store, owner, thread_id):
    row = store.db.execute("SELECT id,kind,title,community_id FROM chat_threads WHERE owner=? AND id=?", (owner, thread_id)).fetchone()
    if not row or (row[3] and row[3] not in joined_ids(store, owner)):
        raise HTTPException(404, "Conversation not found")
    return row


@router.get("/api/chats/{thread_id}/messages")
def messages(thread_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        t = own_thread(store, owner, thread_id)
        rows = store.db.execute("SELECT id,author,text,at,provenance,persona_id,model FROM chat_messages WHERE owner=? AND thread_id=? ORDER BY at",
                                (owner, thread_id)).fetchall()
        store.db.execute("DELETE FROM chat_reads WHERE owner=? AND thread_id=?", (owner, thread_id))
        store.db.execute("INSERT INTO chat_reads VALUES (?,?,?)", (owner, thread_id, clock().isoformat()))
        store.db.commit()
        return {"thread": {"id": t[0], "kind": t[1], "title": t[2], "community_id": t[3]},
                "messages": [{"id": r[0], "author": r[1], "mine": r[1] == "You", "text": r[2], "at": r[3], "provenance": r[4], "persona_id": r[5], "avatar": social.avatar(store, r[5]), "model": r[6]} for r in rows]}


class MessageIn(PostIn):
    pass


@router.post("/api/chats/{thread_id}/messages")
def send_message(thread_id: str, body: MessageIn, request: Request):
    """Stored for this owner only; demo groups have no other real members yet."""
    store, owner = scope(request)
    with store.lock:
        setup(store)
        own_thread(store, owner, thread_id)
        result, fresh = social.claim(store, owner, "chat", thread_id, body)
        if not fresh:
            return result
        store.db.execute("INSERT INTO chat_messages (id,owner,thread_id,author,text,at,provenance) VALUES (?,?,?,?,?,?,?)", (result["id"], owner, thread_id, "You", body.text, clock().isoformat(), "user_supplied"))
        store.db.commit()
    return social.respond(store, owner, result, "chat", thread_id)


# ---------------------------------------------------------------- contacts and calls
class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(pattern=r"^\+?[0-9 ()-]{6,20}$")

    @field_validator("name")
    @classmethod
    def named(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter a name")
        return value


@router.get("/api/contacts")
def contacts(request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        rows = store.db.execute("SELECT id,name,phone,created_at FROM contacts WHERE owner=? ORDER BY name", (owner,)).fetchall()
        return {"contacts": [{"id": r[0], "name": r[1], "phone": r[2], "created_at": r[3]} for r in rows]}


@router.post("/api/contacts")
def add_contact(body: ContactIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        cid = uuid4().hex
        store.db.execute("INSERT INTO contacts VALUES (?,?,?,?,?)", (cid, owner, body.name, body.phone.strip(), clock().isoformat()))
        store.db.commit()
        return {"id": cid, "name": body.name, "phone": body.phone.strip()}


@router.delete("/api/contacts/{contact_id}")
def delete_contact(contact_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        gone = store.db.execute("DELETE FROM contacts WHERE id=? AND owner=?", (contact_id, owner)).rowcount
        store.db.commit()
    if not gone:
        raise HTTPException(404, "Contact not found")
    return {"deleted": contact_id}


class CallIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contact_id: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=80)


@router.get("/api/calls")
def calls(request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        rows = store.db.execute("SELECT id,contact_id,name,phone,at FROM call_log WHERE owner=? ORDER BY at DESC LIMIT 100", (owner,)).fetchall()
        return {"calls": [{"id": r[0], "contact_id": r[1], "name": r[2], "phone": r[3], "at": r[4], "source": "started_in_dubai_io"} for r in rows]}


@router.post("/api/calls")
def log_call(body: CallIn, request: Request):
    """Records that the user started a call from Dubai-io; the phone's dialer places it."""
    store, owner = scope(request)
    with store.lock:
        setup(store)
        if body.contact_id:
            row = store.db.execute("SELECT name,phone FROM contacts WHERE id=? AND owner=?", (body.contact_id, owner)).fetchone()
            if not row:
                raise HTTPException(404, "Contact not found")
            name, phone, contact_id = row[0], row[1], body.contact_id
        elif body.phone:
            digits = "".join(ch for ch in body.phone if ch in "+0123456789")
            if sum(ch.isdigit() for ch in digits) < 7:
                raise HTTPException(422, "Enter a dialable phone number")
            name, phone, contact_id = body.name or "Dialed number", body.phone, None
        else:
            raise HTTPException(422, "contact_id or phone is required")
        lid = uuid4().hex
        store.db.execute("INSERT INTO call_log VALUES (?,?,?,?,?,?)", (lid, owner, contact_id, name, phone, clock().isoformat()))
        store.db.commit()
        return {"tel": "tel:" + "".join(ch for ch in phone if ch in "+0123456789"), "logged": lid}


@router.delete("/api/calls")
def clear_calls(request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        store.db.execute("DELETE FROM call_log WHERE owner=?", (owner,))
        store.db.commit()
        return {"cleared": True}


# ---------------------------------------------------------------- votes, history, read markers

def vote_maps(store, owner, target_type, ids):
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}, {}
    marks = ",".join("?" * len(ids))
    sums = {r[0]: r[1] for r in store.db.execute(
        f"SELECT target_id, SUM(value) FROM votes WHERE target_type=? AND target_id IN ({marks}) GROUP BY target_id",
        (target_type, *ids)).fetchall()}
    mine = {r[0]: r[1] for r in store.db.execute(
        f"SELECT target_id, value FROM votes WHERE target_type=? AND owner=? AND target_id IN ({marks})",
        (target_type, owner, *ids)).fetchall()}
    return sums, mine


def hot_score(score, created_at):
    try:
        age = max(0.0, (clock() - datetime.fromisoformat(created_at)).total_seconds() / 3600)
    except Exception:
        age = 24.0
    return score / ((age + 2) ** 1.5)


class VoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_type: str = Field(pattern="^(post|comment)$")
    target_id: str = Field(min_length=1, max_length=100)
    value: int


@router.post("/api/votes")
def vote(body: VoteIn, request: Request):
    """Up/down vote a visible post or comment; repeating the same vote removes it."""
    store, owner = scope(request)
    with store.lock:
        setup(store)
        if body.value not in (-1, 1):
            raise HTTPException(422, "value must be -1 or 1")
        if body.target_type == "post":
            visible_post(store, owner, body.target_id)
            base = store.db.execute("SELECT likes FROM posts WHERE id=?", (body.target_id,)).fetchone()[0]
        else:
            row = store.db.execute("SELECT post_id,likes FROM comments WHERE id=? AND (owner IS NULL OR owner=?)",
                                   (body.target_id, owner)).fetchone()
            if not row:
                raise HTTPException(404, "Comment not found")
            visible_post(store, owner, row[0])
            base = row[1]
        current = store.db.execute("SELECT value FROM votes WHERE target_type=? AND target_id=? AND owner=?",
                                   (body.target_type, body.target_id, owner)).fetchone()
        if current and current[0] == body.value:
            store.db.execute("DELETE FROM votes WHERE target_type=? AND target_id=? AND owner=?",
                             (body.target_type, body.target_id, owner))
            mine = 0
        else:
            store.db.execute("INSERT OR REPLACE INTO votes VALUES (?,?,?,?)",
                             (body.target_type, body.target_id, owner, body.value))
            mine = body.value
        total = store.db.execute("SELECT COALESCE(SUM(value),0) FROM votes WHERE target_type=? AND target_id=?",
                                 (body.target_type, body.target_id)).fetchone()[0]
        store.db.commit()
        return {"target_type": body.target_type, "target_id": body.target_id,
                "score": base + total, "my_vote": mine}


@router.get("/api/me/posts")
def my_posts(request: Request):
    store, owner = scope(request)
    with store.lock:
        setup(store)
        rows = store.db.execute(POST_SQL + " WHERE p.owner=? AND p.kind='post' ORDER BY p.created_at DESC", (owner, owner)).fetchall()
        joined = joined_ids(store, owner)
        posts = [present_post(r, joined) for r in rows]
        sums, mine = vote_maps(store, owner, "post", [p["id"] for p in posts])
        for p in posts:
            p["score"] = p["likes"] + sums.get(p["id"], 0)
            p["my_vote"] = mine.get(p["id"], 0)
        return {"posts": posts}


@router.post("/api/chats/{thread_id}/read")
def mark_read(thread_id: str, request: Request):
    """Explicit read marker; opening messages already marks read implicitly."""
    store, owner = scope(request)
    with store.lock:
        setup(store)
        own_thread(store, owner, thread_id)
        store.db.execute("DELETE FROM chat_reads WHERE owner=? AND thread_id=?", (owner, thread_id))
        store.db.execute("INSERT INTO chat_reads VALUES (?,?,?)", (owner, thread_id, clock().isoformat()))
        store.db.commit()
        return {"thread": thread_id, "unread": 0}
