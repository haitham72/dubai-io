"""Deterministic 10-user / 7-group Community demo cohort (namespace community-demo-10-v1).

All rows use provenance ``demo_fixture``. Owners and entity IDs are prefixed with
the namespace so ``--reset-demo`` is scoped and cannot touch organic data.
Excluded from two-tower training, usage-profile aggregation, and temporal_memory
writes by callers that check ``is_demo_namespace_owner`` / ``is_demo_entity_id``.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from . import store as cm
from . import media as cm_media
from . import moderation as cm_mod

NAMESPACE = "community-demo-10-v1"
SEED = 20261126
PROVENANCE = "demo_fixture"
DXB = timezone(timedelta(hours=4))

# Tiny valid 1×1 PNG (demo media only).
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

ACTORS: list[dict[str, Any]] = [
    {"id": "sim-01", "handle": "nour_fe_demo", "display_name": "Nour (Demo)", "bio": "Frontend developer — demo account", "area": "DIFC", "interests": ["react", "ml", "career"], "groups": ["dubai-developers", "learning-circle"]},
    {"id": "sim-02", "handle": "omar_design_demo", "display_name": "Omar (Demo)", "bio": "Product designer — demo account", "area": "Business Bay", "interests": ["ux", "motion", "design"], "groups": ["design-creators", "dubai-developers"]},
    {"id": "sim-03", "handle": "leila_walks_demo", "display_name": "Leila (Demo)", "bio": "City explorer — demo account", "area": "Jumeirah", "interests": ["walks", "photo", "spaces"], "groups": ["dubai-weekends", "design-creators"]},
    {"id": "sim-04", "handle": "adam_new_demo", "display_name": "Adam (Demo)", "bio": "New resident — demo account", "area": "JLT", "interests": ["moving", "intros"], "groups": ["new-in-dubai", "dubai-weekends"]},
    {"id": "sim-05", "handle": "mariam_study_demo", "display_name": "Mariam (Demo)", "bio": "Student — demo account", "area": "Academic City", "interests": ["python", "study", "courses"], "groups": ["learning-circle", "dubai-developers"]},
    {"id": "sim-06", "handle": "rami_games_demo", "display_name": "Rami (Demo)", "bio": "Gaming enthusiast — demo account", "area": "Al Quoz", "interests": ["pc", "multiplayer", "games"], "groups": ["dubai-gamers", "design-creators"]},
    {"id": "sim-07", "handle": "sara_biz_demo", "display_name": "Sara (Demo)", "bio": "Small-business operator — demo account", "area": "Deira", "interests": ["workflow", "customers", "network"], "groups": ["small-business-uae", "dubai-developers"]},
    {"id": "sim-08", "handle": "youssef_photo_demo", "display_name": "Youssef (Demo)", "bio": "Photographer — demo account", "area": "Marina", "interests": ["camera", "composition"], "groups": ["design-creators", "dubai-weekends"]},
    {"id": "sim-09", "handle": "dana_vol_demo", "display_name": "Dana (Demo)", "bio": "Community volunteer — demo account", "area": "Bur Dubai", "interests": ["events", "help", "resources"], "groups": ["new-in-dubai", "dubai-weekends"]},
    {"id": "sim-10", "handle": "kareem_pm_demo", "display_name": "Kareem (Demo)", "bio": "Project coordinator — demo account", "area": "Internet City", "interests": ["planning", "productivity", "ai"], "groups": ["small-business-uae", "learning-circle"]},
]

GROUPS: list[dict[str, str]] = [
    {"key": "dubai-developers", "name": "Dubai Developers (Demo)", "handle": "demo-dubai-developers", "description": "Coding, AI projects, tools, beginner questions — demo community."},
    {"key": "design-creators", "name": "Design & Creators (Demo)", "handle": "demo-design-creators", "description": "Portfolios, motion design, creative prompts — demo community."},
    {"key": "dubai-weekends", "name": "Dubai Weekends (Demo)", "handle": "demo-dubai-weekends", "description": "Fictional social planning suggestions — demo community."},
    {"key": "new-in-dubai", "name": "New in Dubai (Demo)", "handle": "demo-new-in-dubai", "description": "Introductions and requests for verifiable guidance — demo community."},
    {"key": "learning-circle", "name": "Learning Circle (Demo)", "handle": "demo-learning-circle", "description": "Courses, Python, studying and accountability — demo community."},
    {"key": "dubai-gamers", "name": "Dubai Gamers (Demo)", "handle": "demo-dubai-gamers", "description": "Games, hardware and friendly discussions — demo community."},
    {"key": "small-business-uae", "name": "Small Business UAE (Demo)", "handle": "demo-small-business-uae", "description": "Collaboration, productivity and workflow ideas — demo community."},
]

# Directed follow edges (follower -> followee) by sim-id; ≥20, no self-follows.
FOLLOW_EDGES: list[tuple[str, str]] = [
    ("sim-01", "sim-02"), ("sim-01", "sim-05"), ("sim-01", "sim-10"),
    ("sim-02", "sim-01"), ("sim-02", "sim-06"), ("sim-02", "sim-08"),
    ("sim-03", "sim-08"), ("sim-03", "sim-04"), ("sim-03", "sim-09"),
    ("sim-04", "sim-09"), ("sim-04", "sim-03"), ("sim-04", "sim-01"),
    ("sim-05", "sim-01"), ("sim-05", "sim-10"), ("sim-05", "sim-07"),
    ("sim-06", "sim-02"), ("sim-06", "sim-08"),
    ("sim-07", "sim-10"), ("sim-07", "sim-01"), ("sim-07", "sim-05"),
    ("sim-08", "sim-03"), ("sim-08", "sim-06"),
    ("sim-09", "sim-04"), ("sim-09", "sim-03"),
    ("sim-10", "sim-07"), ("sim-10", "sim-05"),
]

POST_TEMPLATES: list[dict[str, Any]] = [
    # (author, group_key, text, has_image) — 40 posts, ≥3 per user
    {"a": "sim-01", "g": "dubai-developers", "t": "Anyone joining the React meetup this week? Looking for a study buddy on hooks patterns.", "img": False},
    {"a": "sim-01", "g": "learning-circle", "t": "Shared a short checklist for switching careers into frontend — happy to answer beginner questions.", "img": False},
    {"a": "sim-01", "g": "dubai-developers", "t": "Tried a new ML demo notebook for side projects. What local meetups are good for beginners?", "img": True},
    {"a": "sim-01", "g": "dubai-developers", "t": "Tip: keep component props small. Curious how others structure design tokens in Expo web.", "img": False},
    {"a": "sim-02", "g": "design-creators", "t": "Working on a motion portfolio reel — looking for feedback on pacing, not pitches.", "img": True},
    {"a": "sim-02", "g": "dubai-developers", "t": "Designers: which prototyping tools play nicest with React Native sketches?", "img": False},
    {"a": "sim-02", "g": "design-creators", "t": "Sharing a fictional case study outline for UX interviews (demo content only).", "img": False},
    {"a": "sim-02", "g": "design-creators", "t": "Creative prompt: redesign a transit card for weekend walkers — show process, not polished ads.", "img": False},
    {"a": "sim-03", "g": "dubai-weekends", "t": "Planning a Saturday morning photo walk around public waterfront paths — fictional plan for demo.", "img": True},
    {"a": "sim-03", "g": "design-creators", "t": "Favourite public spaces for soft evening light? Looking for first-hand fictional tips only.", "img": False},
    {"a": "sim-03", "g": "dubai-weekends", "t": "Quiet coffee spots near walkable parks? Please share personal opinions, not official hours.", "img": False},
    {"a": "sim-03", "g": "design-creators", "t": "Composition challenge: leading lines in everyday streets. Post your practice shots.", "img": False},
    {"a": "sim-04", "g": "new-in-dubai", "t": "Just moved — looking for a checklist of verifiable first-week errands (no legal advice).", "img": False},
    {"a": "sim-04", "g": "dubai-weekends", "t": "Introducing myself: Adam (demo). Keen to meet walkers and learners this month.", "img": False},
    {"a": "sim-04", "g": "new-in-dubai", "t": "What community intros helped you settle? Prefer links to official guides when possible.", "img": True},
    {"a": "sim-04", "g": "dubai-weekends", "t": "Anyone hosting beginner-friendly weekend hangouts that are clearly labelled as meetups?", "img": False},
    {"a": "sim-05", "g": "learning-circle", "t": "Python study sprint tonight — accountability thread for finishing chapter exercises.", "img": False},
    {"a": "sim-05", "g": "dubai-developers", "t": "Best free course formats for data basics? Looking for peer reviews, not ads.", "img": False},
    {"a": "sim-05", "g": "learning-circle", "t": "Shared my fictional study timetable template — edit freely for your own week.", "img": True},
    {"a": "sim-05", "g": "learning-circle", "t": "Stuck on list comprehensions — anyone have a plain-language analogy?", "img": False},
    {"a": "sim-06", "g": "dubai-gamers", "t": "Building a mid-range PC for multiplayer — what cooling setups do you like for hot rooms?", "img": False},
    {"a": "sim-06", "g": "design-creators", "t": "Game UI moodboards: looking for friendly critiques on contrast, not monetisation tips.", "img": True},
    {"a": "sim-06", "g": "dubai-gamers", "t": "Weekend co-op queue — fictional lobby for demo friends only.", "img": False},
    {"a": "sim-06", "g": "dubai-gamers", "t": "Controller vs keyboard for strategy games — what's your preference and why?", "img": False},
    {"a": "sim-07", "g": "small-business-uae", "t": "Looking for lightweight workflow tools for customer replies — share what you actually use.", "img": False},
    {"a": "sim-07", "g": "dubai-developers", "t": "Local networking ideas for operators (demo). Prefer open community events over cold DMs.", "img": False},
    {"a": "sim-07", "g": "small-business-uae", "t": "Template: weekly ops checklist for a tiny shop — fictional sample for discussion.", "img": True},
    {"a": "sim-07", "g": "small-business-uae", "t": "How do you track follow-ups without drowning in spreadsheets?", "img": False},
    {"a": "sim-08", "g": "design-creators", "t": "Camera bag essentials for a short waterfront walk — gear chat only, no brand rankings.", "img": True},
    {"a": "sim-08", "g": "dubai-weekends", "t": "Hosting a practice shoot this weekend (demo invite) — beginners welcome.", "img": False},
    {"a": "sim-08", "g": "design-creators", "t": "Composition tip: frame with doorways. Share a practice crop if you try it.", "img": False},
    {"a": "sim-08", "g": "design-creators", "t": "Looking for peers who shoot architecture details — swap feedback, not clients.", "img": False},
    {"a": "sim-09", "g": "new-in-dubai", "t": "Neighbourhood volunteer board: fictional event ideas for the demo week.", "img": False},
    {"a": "sim-09", "g": "dubai-weekends", "t": "Useful resources thread — please cite official pages when you share links.", "img": False},
    {"a": "sim-09", "g": "new-in-dubai", "t": "Offering to walk newcomers through community norms (demo mentoring).", "img": True},
    {"a": "sim-09", "g": "dubai-weekends", "t": "Help needed: packing leftover supplies after a fictional park meetup.", "img": False},
    {"a": "sim-10", "g": "small-business-uae", "t": "Project planning board for small teams — how do you keep AI drafts out of final docs?", "img": False},
    {"a": "sim-10", "g": "learning-circle", "t": "Accountability buddy for finishing a productivity course this fortnight?", "img": False},
    {"a": "sim-10", "g": "small-business-uae", "t": "Demo: sprint retro template with three questions — adapt as you like.", "img": True},
    {"a": "sim-10", "g": "learning-circle", "t": "AI-at-work discussion: keep human review on anything customer-facing.", "img": False},
]


def owner_id(sim_id: str) -> str:
    return f"{NAMESPACE}:{sim_id}"


def group_id(key: str) -> str:
    return f"{NAMESPACE}:grp-{key}"


def post_id(n: int) -> str:
    return f"{NAMESPACE}:post-{n:03d}"


def comment_id(n: int) -> str:
    return f"{NAMESPACE}:cmt-{n:03d}"


def media_id(n: int) -> str:
    return f"{NAMESPACE}:media-{n:03d}"


def is_demo_namespace_owner(owner: str | None) -> bool:
    return bool(owner) and str(owner).startswith(f"{NAMESPACE}:")


def is_demo_entity_id(entity_id: str | None) -> bool:
    return bool(entity_id) and str(entity_id).startswith(f"{NAMESPACE}:")


def _stamp(day_offset: int, hour: int, minute: int = 0) -> str:
    """UTC ISO stamp for a Dubai-local fictional day within the 14-day window."""
    base = datetime(2026, 11, 12, tzinfo=DXB)  # start of 14-day window
    local = base + timedelta(days=day_offset, hours=hour, minutes=minute)
    return local.astimezone(timezone.utc).isoformat(timespec="seconds")


def _idem(kind: str, *parts: str) -> str:
    raw = "|".join((NAMESPACE, kind, *parts))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def plan_counts() -> dict[str, int]:
    return {
        "users": 10,
        "groups": 7,
        "posts": 40,
        "min_posts_per_user": 3,
        "min_image_posts": 10,  # ≥1 per 3 users → ≥4; we seed 10
        "comments": 90,
        "reply_chains": 15,
        "reactions": 120,
        "follows": len(FOLLOW_EDGES),
        "memberships_min": 20,
        "notifications_min": 20,
        "bookmarks_min": 10,
        "moderation_fixtures": 2,
    }


def _ensure_ready(store) -> None:
    cm.setup(store)
    cm_media.setup(store)
    cm_mod.setup_mod(store)


def verify_counts(store) -> dict[str, Any]:
    """Return measured counts + pass/fail against §2 targets (namespace-scoped)."""
    _ensure_ready(store)
    ns = f"{NAMESPACE}%"
    users = store.db.execute("SELECT COUNT(*) FROM cm_profiles WHERE owner LIKE ?", (ns,)).fetchone()[0]
    groups = store.db.execute("SELECT COUNT(*) FROM cm_groups WHERE id LIKE ?", (ns,)).fetchone()[0]
    posts = store.db.execute(
        "SELECT COUNT(*) FROM cm_posts WHERE id LIKE ? AND deleted=0", (ns,)
    ).fetchone()[0]
    comments = store.db.execute("SELECT COUNT(*) FROM cm_comments WHERE id LIKE ?", (ns,)).fetchone()[0]
    reactions = store.db.execute(
        "SELECT COUNT(*) FROM cm_reactions WHERE target_id LIKE ?", (ns,)
    ).fetchone()[0]
    follows = store.db.execute(
        "SELECT COUNT(*) FROM cm_follows WHERE follower LIKE ? AND followee LIKE ?", (ns, ns)
    ).fetchone()[0]
    memberships = store.db.execute(
        "SELECT COUNT(*) FROM cm_group_members WHERE group_id LIKE ?", (ns,)
    ).fetchone()[0]
    notifications = store.db.execute(
        "SELECT COUNT(*) FROM cm_notifications WHERE dedupe_key LIKE ?", (f"{NAMESPACE}:%",)
    ).fetchone()[0]
    bookmarks = store.db.execute(
        "SELECT COUNT(*) FROM cm_bookmarks WHERE post_id LIKE ?", (ns,)
    ).fetchone()[0]
    media = store.db.execute("SELECT COUNT(*) FROM cm_media WHERE id LIKE ?", (ns,)).fetchone()[0]
    reports = store.db.execute(
        "SELECT COUNT(*) FROM cm_reports WHERE id LIKE ?", (ns,)
    ).fetchone()[0]
    # reply chains: comments with parent_id set
    chains = store.db.execute(
        "SELECT COUNT(*) FROM cm_comments WHERE id LIKE ? AND parent_id IS NOT NULL AND parent_id <> ''",
        (ns,),
    ).fetchone()[0]
    per_user = store.db.execute(
        "SELECT owner, COUNT(*) FROM cm_posts WHERE id LIKE ? AND deleted=0 GROUP BY owner", (ns,)
    ).fetchall()
    min_posts = min((r[1] for r in per_user), default=0) if per_user else 0
    targets = plan_counts()
    checks = {
        "users": users == targets["users"],
        "groups": groups == targets["groups"],
        "posts": posts >= targets["posts"],
        "min_posts_per_user": min_posts >= targets["min_posts_per_user"],
        "image_media": media >= targets["min_image_posts"],
        "comments": comments >= targets["comments"],
        "reply_chains": chains >= targets["reply_chains"],
        "reactions": reactions >= targets["reactions"],
        "follows": follows >= targets["follows"],
        "memberships": memberships >= targets["memberships_min"],
        "notifications": notifications >= targets["notifications_min"],
        "bookmarks": bookmarks >= targets["bookmarks_min"],
        "moderation_reports": reports >= targets["moderation_fixtures"],
        "provenance_demo_only": store.db.execute(
            "SELECT COUNT(*) FROM cm_posts WHERE id LIKE ? AND provenance <> ?",
            (ns, PROVENANCE),
        ).fetchone()[0]
        == 0,
    }
    return {
        "namespace": NAMESPACE,
        "measured": {
            "users": users,
            "groups": groups,
            "posts": posts,
            "comments": comments,
            "reply_chains": chains,
            "reactions": reactions,
            "follows": follows,
            "memberships": memberships,
            "notifications": notifications,
            "bookmarks": bookmarks,
            "media": media,
            "reports": reports,
            "min_posts_per_user": min_posts,
        },
        "targets": targets,
        "checks": checks,
        "ok": all(checks.values()),
    }


def reset_demo(store) -> dict[str, int]:
    """Delete only namespace-scoped rows. Never touches organic Community data."""
    _ensure_ready(store)
    ns = f"{NAMESPACE}%"
    deleted: dict[str, int] = {}
    with store.lock:
        # Order: children first
        for table, col in (
            ("cm_media", "id"),
            ("cm_reports", "id"),
            ("cm_moderation_events", "id"),
            ("cm_notifications", "dedupe_key"),
            ("cm_bookmarks", "post_id"),
            ("cm_reactions", "target_id"),
            ("cm_votes", "target_id"),
            ("cm_post_tags", "post_id"),
            ("cm_post_revisions", "post_id"),
            ("cm_comments", "id"),
            ("cm_posts", "id"),
            ("cm_group_members", "group_id"),
            ("cm_group_moderation_log", "id"),
            ("cm_groups", "id"),
            ("cm_follows", "follower"),
            ("cm_memory_preferences", "owner"),
            ("cm_profiles", "owner"),
        ):
            if table == "cm_follows":
                cur = store.db.execute(
                    "DELETE FROM cm_follows WHERE follower LIKE ? OR followee LIKE ?", (ns, ns)
                )
            elif table == "cm_notifications":
                cur = store.db.execute(
                    "DELETE FROM cm_notifications WHERE dedupe_key LIKE ? OR owner LIKE ?",
                    (f"{NAMESPACE}:%", ns),
                )
            elif table == "cm_moderation_events":
                cur = store.db.execute(
                    "DELETE FROM cm_moderation_events WHERE id LIKE ? OR target_id LIKE ?",
                    (ns, ns),
                )
            else:
                cur = store.db.execute(f"DELETE FROM {table} WHERE {col} LIKE ?", (ns,))
            deleted[table] = int(getattr(cur, "rowcount", 0) or 0)
        store.db.commit()
    return deleted


def apply_seed(store, *, dry_run: bool = True) -> dict[str, Any]:
    """Idempotent seed. dry_run computes plan without writes."""
    _ensure_ready(store)
    rng = random.Random(SEED)
    planned = {
        "namespace": NAMESPACE,
        "seed": SEED,
        "provenance": PROVENANCE,
        "users": len(ACTORS),
        "groups": len(GROUPS),
        "posts": len(POST_TEMPLATES),
        "follows": len(FOLLOW_EDGES),
        "dry_run": dry_run,
    }
    if dry_run:
        planned["would_write"] = True
        planned["verify_before"] = verify_counts(store)
        return planned

    with store.lock:
        # Profiles
        for actor in ACTORS:
            oid = owner_id(actor["id"])
            stamp = _stamp(0, 8)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_profiles "
                "(owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    oid,
                    actor["handle"],
                    actor["display_name"],
                    actor["bio"],
                    actor["area"],
                    json.dumps(actor["interests"]),
                    "18+",
                    "public",
                    PROVENANCE,
                    stamp,
                    stamp,
                ),
            )

        # Groups + memberships
        for g in GROUPS:
            gid = group_id(g["key"])
            owner = owner_id("sim-01")  # stable demo owner of groups
            stamp = _stamp(0, 9)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_groups "
                "(id,name,handle,description,visibility,owner,provenance,created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (gid, g["name"], g["handle"], g["description"], "public", owner, PROVENANCE, stamp),
            )
            store.db.execute(
                "INSERT OR IGNORE INTO cm_group_members VALUES (?,?, 'owner', 'active', NULL, ?)",
                (gid, owner, stamp),
            )
        for actor in ACTORS:
            oid = owner_id(actor["id"])
            for i, gkey in enumerate(actor["groups"]):
                stamp = _stamp(0, 10 + i)
                store.db.execute(
                    "INSERT OR IGNORE INTO cm_group_members VALUES (?,?, 'member', 'active', NULL, ?)",
                    (group_id(gkey), oid, stamp),
                )

        # Follows
        for follower, followee in FOLLOW_EDGES:
            stamp = _stamp(1, 11)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_follows VALUES (?,?,?)",
                (owner_id(follower), owner_id(followee), stamp),
            )

        # Posts (+ media for image posts)
        image_n = 0
        for i, tmpl in enumerate(POST_TEMPLATES, start=1):
            pid = post_id(i)
            oid = owner_id(tmpl["a"])
            gid = group_id(tmpl["g"])
            day = (i - 1) % 14
            hour = 9 + (i % 10)
            stamp = _stamp(day, hour, (i * 3) % 50)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_posts "
                "(id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at,flair,repost_of_id) "
                "VALUES (?,?,?,?,1,0,0,?,?,?,'',NULL)",
                (pid, oid, gid, tmpl["t"], PROVENANCE, stamp, stamp),
            )
            store.db.execute(
                "INSERT OR IGNORE INTO cm_post_revisions VALUES (?,?,?,?)",
                (pid, 1, tmpl["t"], stamp),
            )
            if tmpl.get("img"):
                image_n += 1
                mid = media_id(image_n)
                key = mid
                store.db.execute(
                    "INSERT OR IGNORE INTO cm_media "
                    "(id,owner,post_id,filename,content_type,size,storage_key,provenance,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        mid,
                        oid,
                        pid,
                        f"{mid}.png",
                        "image/png",
                        len(_PNG_1X1),
                        key,
                        PROVENANCE,
                        stamp,
                    ),
                )
                # Best-effort write bytes (local media dir).
                try:
                    path = cm_media._media_dir() / key
                    if not path.exists():
                        path.write_bytes(_PNG_1X1)
                except Exception:
                    pass

        # Comments + nested reply chains (≥90 comments, ≥15 parent-child)
        c_n = 0
        chain_parents: list[str] = []
        for i in range(1, 41):
            pid = post_id(i)
            author = POST_TEMPLATES[i - 1]["a"]
            # 2 top-level comments per post → 80
            for j in range(2):
                c_n += 1
                cid = comment_id(c_n)
                commenter = ACTORS[(i + j + 1) % 10]["id"]
                if commenter == author:
                    commenter = ACTORS[(i + j + 2) % 10]["id"]
                stamp = _stamp((i - 1) % 14, 12 + j, i % 40)
                text = f"Demo reply {j + 1} on post {i}: thanks for sharing — continuing the thread."
                store.db.execute(
                    "INSERT OR IGNORE INTO cm_comments "
                    "(id,post_id,owner,parent_id,text,provenance,created_at) VALUES (?,?,?,?,?,?,?)",
                    (cid, pid, owner_id(commenter), None, text, PROVENANCE, stamp),
                )
                if j == 0:
                    chain_parents.append(cid)
                # notifications for post author
                dedupe = f"{NAMESPACE}:reply:{cid}"
                store.db.execute(
                    "INSERT OR IGNORE INTO cm_notifications "
                    "(id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,0,?)",
                    (
                        f"{NAMESPACE}:notif-{c_n:03d}",
                        owner_id(author),
                        owner_id(commenter),
                        "reply",
                        pid,
                        cid,
                        group_id(POST_TEMPLATES[i - 1]["g"]),
                        text[:80],
                        dedupe,
                        stamp,
                    ),
                )
        # 15 nested replies + 10 more top-level to reach ≥90
        for k in range(15):
            c_n += 1
            parent = chain_parents[k]
            cid = comment_id(c_n)
            replier = ACTORS[k % 10]["id"]
            stamp = _stamp(k % 14, 15, k)
            parent_post = post_id(k + 1)  # chain_parents[k] was the first comment on post k+1
            store.db.execute(
                "INSERT OR IGNORE INTO cm_comments "
                "(id,post_id,owner,parent_id,text,provenance,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    cid,
                    parent_post,
                    owner_id(replier),
                    parent,
                    f"Nested demo reply {k + 1} — addressing the parent comment.",
                    PROVENANCE,
                    stamp,
                ),
            )
        for k in range(10):
            c_n += 1
            cid = comment_id(c_n)
            stamp = _stamp(k % 14, 16, k)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_comments "
                "(id,post_id,owner,parent_id,text,provenance,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    cid,
                    post_id((k % 40) + 1),
                    owner_id(ACTORS[k % 10]["id"]),
                    None,
                    f"Extra demo comment {k + 1} for volume.",
                    PROVENANCE,
                    stamp,
                ),
            )

        # Reactions ≥120
        kinds = ("like", "like", "like", "celebrate", "insightful")
        r_n = 0
        for i in range(1, 41):
            pid = post_id(i)
            for j in range(3):  # 120
                r_n += 1
                reactor = ACTORS[(i + j) % 10]["id"]
                kind = kinds[(i + j) % len(kinds)]
                stamp = _stamp((i - 1) % 14, 17, j)
                store.db.execute(
                    "INSERT OR IGNORE INTO cm_reactions VALUES (?,?,?,?,?)",
                    (owner_id(reactor), "post", pid, kind, stamp),
                )

        # Bookmarks ≥10
        for i in range(1, 11):
            stamp = _stamp(i % 14, 18)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_bookmarks VALUES (?,?,?)",
                (owner_id(ACTORS[i % 10]["id"]), post_id(i), stamp),
            )

        # Moderation fixtures: 1 false-positive candidate, 1 clear spam (no real abuse)
        fp_post = post_id(1)
        spam_post = post_id(21)
        for n, (rid, target, reason, label) in enumerate(
            (
                (
                    f"{NAMESPACE}:report-fp",
                    fp_post,
                    "possible duplicate wording — human review",
                    "false_positive_candidate",
                ),
                (
                    f"{NAMESPACE}:report-spam",
                    spam_post,
                    "repeated promotional phrasing — spam fixture",
                    "spam_fixture",
                ),
            ),
            start=1,
        ):
            stamp = _stamp(13, 19, n)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_reports "
                "(id,reporter,target_type,target_id,reason,status,created_at) VALUES (?,?,?,?,?,?,?)",
                (rid, owner_id("sim-09"), "post", target, reason, "pending", stamp),
            )
            store.db.execute(
                "INSERT OR IGNORE INTO cm_moderation_events "
                "(id,report_id,source,label,evidence,categories,target_type,target_id,target_owner,"
                "group_id,status,target_state,resolved_by,resolution,is_minor,created_at,resolved_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,0,?,NULL)",
                (
                    f"{NAMESPACE}:modev-{n}",
                    rid,
                    "human",
                    label,
                    reason,
                    json.dumps([label]),
                    "post",
                    target,
                    owner_id(POST_TEMPLATES[int(target.rsplit("-", 1)[-1]) - 1]["a"]),
                    None,
                    "flagged",
                    "flagged",
                    stamp,
                ),
            )

        # Extra follow notifications to help hit ≥20 notifications
        for idx, (follower, followee) in enumerate(FOLLOW_EDGES[:12], start=1):
            stamp = _stamp(2, 11, idx)
            store.db.execute(
                "INSERT OR IGNORE INTO cm_notifications "
                "(id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at) "
                "VALUES (?,?,?,?,NULL,NULL,NULL,?,?,0,?)",
                (
                    f"{NAMESPACE}:notif-follow-{idx:02d}",
                    owner_id(followee),
                    owner_id(follower),
                    "follow",
                    f"{ACTORS[idx % 10]['display_name']} followed you (demo)",
                    f"{NAMESPACE}:follow:{follower}:{followee}",
                    stamp,
                ),
            )

        store.db.commit()
        _ = rng  # reserved for future shuffle of optional fields

    return {"dry_run": False, "applied": True, "verify": verify_counts(store), **planned}
