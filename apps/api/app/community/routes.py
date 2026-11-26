"""Community social-core routes (CM-B2/B3/B4 + E14a social parity). Adults-only, no messenger (D3)."""
from datetime import datetime, timezone
import json
import math
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import store as cm
from .principal import resolve

router = APIRouter(tags=["community"])
HANDLE_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MENTION_RE = re.compile(r"@([A-Za-z0-9_]{3,30})")
HASHTAG_RE = re.compile(r"(?<![A-Za-z0-9_])#([A-Za-z0-9_]{2,40})(?![A-Za-z0-9_])")
TAG_RE = re.compile(r"^[a-z0-9_]{2,40}$")
ALLOWED_FLAIRS = frozenset({"", "Question", "Recommendation", "Event", "Warning", "Housing"})
POST_COLS = "id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at,flair,repost_of_id"


def scope(request: Request):
    return resolve(request)


# ---------------------------------------------------------------- helpers
def profile_by_owner(store, owner):
    return store.db.execute(
        "SELECT owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at FROM cm_profiles WHERE owner=?",
        (owner,)).fetchone()


def profile_by_handle(store, handle):
    return store.db.execute(
        "SELECT owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at FROM cm_profiles WHERE handle=?",
        ((handle or "").strip().lower(),)).fetchone()


def present_profile(row, requester):
    owner, handle, display, bio, area, interests, band, privacy, prov, created, updated = row
    return {"owner": owner, "user_id": owner, "handle": handle, "display_name": display, "bio": bio,
            "area": area, "interests": json.loads(interests or "[]"), "age_band": band, "privacy": privacy,
            "provenance": prov, "as_of": updated, "created_at": created, "updated_at": updated, "mine": owner == requester}


def require_profile_row(store, owner):
    row = profile_by_owner(store, owner)
    if not row:
        raise HTTPException(404, "Profile not found")
    return row


def group_row(store, group_id):
    return store.db.execute(
        "SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups WHERE id=?",
        (group_id,)).fetchone()


def require_group(store, group_id):
    row = group_row(store, group_id)
    if not row:
        raise HTTPException(404, "Group not found")
    return row


def member_row(store, group_id, owner):
    return store.db.execute(
        "SELECT group_id,owner,role,status,invited_by,created_at FROM cm_group_members WHERE group_id=? AND owner=?",
        (group_id, owner)).fetchone()


def is_active_member(store, group_id, owner):
    row = member_row(store, group_id, owner)
    return bool(row and row[3] == "active")


def group_access(store, group, owner):
    """Return member row; raise 404 for private groups invisible to non-members."""
    member = member_row(store, group[0], owner)
    if group[4] == "private" and not (member and member[3] == "active"):
        raise HTTPException(404, "Group not found")
    return member


def present_group(store, row, owner):
    member = member_row(store, row[0], owner)
    count = store.db.execute(
        "SELECT COUNT(*) FROM cm_group_members WHERE group_id=? AND status='active'", (row[0],)).fetchone()[0]
    return {"id": row[0], "name": row[1], "handle": row[2], "description": row[3], "visibility": row[4],
            "owner": row[5], "provenance": row[6], "as_of": row[7], "created_at": row[7],
            "members": count, "member_count": count,
            "my_role": member[2] if member else None, "my_status": member[3] if member else None,
            "is_member": bool(member and member[3] == "active")}


def _blocked_owners(store, owner: str) -> set[str]:
    try:
        rows = store.db.execute(
            "SELECT owner, blocked_owner FROM cm_user_blocks WHERE owner=? OR blocked_owner=?",
            (owner, owner),
        ).fetchall()
    except Exception:
        return set()
    blocked: set[str] = set()
    for b_owner, b_target in rows:
        if b_owner == owner:
            blocked.add(b_target)
        elif b_target == owner:
            blocked.add(b_owner)
    return blocked


def _is_blocked_pair(store, owner_a: str, owner_b: str) -> bool:
    if not owner_a or not owner_b or owner_a == owner_b:
        return False
    try:
        row = store.db.execute(
            "SELECT 1 FROM cm_user_blocks WHERE (owner=? AND blocked_owner=?) OR (owner=? AND blocked_owner=?)",
            (owner_a, owner_b, owner_b, owner_a),
        ).fetchone()
        return bool(row)
    except Exception:
        return False


def _muted_sets(store, owner: str) -> tuple[set[str], set[str], set[str]]:
    try:
        rows = store.db.execute("SELECT kind, target FROM cm_user_mutes WHERE owner=?", (owner,)).fetchall()
    except Exception:
        return set(), set(), set()
    owners: set[str] = set()
    groups: set[str] = set()
    tags: set[str] = set()
    for kind, target in rows:
        if kind == "owner":
            owners.add(target)
        elif kind == "group":
            groups.add(target)
        elif kind == "tag":
            tags.add(target)
    return owners, groups, tags


def _extract_tags(text: str, explicit_tags: list[str] | None = None) -> list[str]:
    seen: list[str] = []
    seen_set: set[str] = set()
    for raw in HASHTAG_RE.findall(text or ""):
        clean = raw.lower()
        if clean not in seen_set:
            seen_set.add(clean)
            seen.append(clean)
    for raw in explicit_tags or ():
        clean = (raw or "").strip().lstrip("#").lower()
        if TAG_RE.match(clean) and clean not in seen_set:
            seen_set.add(clean)
            seen.append(clean)
    return seen[:10]


def _sync_post_tags(store, post_id: str, text: str, explicit_tags: list[str] | None = None, stamp: str | None = None):
    tags = _extract_tags(text, explicit_tags)
    store.db.execute("DELETE FROM cm_post_tags WHERE post_id=?", (post_id,))
    ts = stamp or cm.now()
    for tag in tags:
        store.db.execute("INSERT OR IGNORE INTO cm_post_tags (post_id,tag,created_at) VALUES (?,?,?)", (post_id, tag, ts))


def _post_tags(store, post_id: str) -> list[str]:
    try:
        rows = store.db.execute(
            "SELECT tag FROM cm_post_tags WHERE post_id=? ORDER BY created_at, tag", (post_id,)
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def _vote_stats(store, target_type: str, target_id: str, requester: str) -> tuple[int, int, int, int, bool]:
    try:
        rows = store.db.execute(
            "SELECT owner, value FROM cm_votes WHERE target_type=? AND target_id=?",
            (target_type, target_id),
        ).fetchall()
    except Exception:
        return 0, 0, 0, 0, False
    upvotes = sum(1 for _, v in rows if int(v) > 0)
    downvotes = sum(1 for _, v in rows if int(v) < 0)
    vote_score = sum(int(v) for _, v in rows)
    my_vote = 0
    for v_owner, v_val in rows:
        if v_owner == requester:
            my_vote = 1 if int(v_val) > 0 else (-1 if int(v_val) < 0 else 0)
            break
    return upvotes, downvotes, vote_score, my_vote, bool(rows)


def _parse_ts(iso_str: str) -> float:
    raw = (iso_str or "").strip()
    if not raw:
        return 0.0
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def post_row(store, post_id):
    return store.db.execute(f"SELECT {POST_COLS} FROM cm_posts WHERE id=?", (post_id,)).fetchone()


def _post_removed(store, post_id) -> bool:
    try:
        order = "rowid DESC" if getattr(store.db, "dialect", "sqlite") == "sqlite" else "created_at DESC"
        row = store.db.execute(
            f"SELECT target_state FROM cm_moderation_events WHERE target_type='post' AND target_id=? ORDER BY {order} LIMIT 1",
            (post_id,),
        ).fetchone()
        return bool(row and row[0] == "removed")
    except Exception:
        return False


def require_visible_post(store, owner, post_id):
    row = post_row(store, post_id)
    if not row or row[6] or _post_removed(store, post_id) or _is_blocked_pair(store, owner, row[1]):
        raise HTTPException(404, "Post not found")
    if row[2]:
        group = group_row(store, row[2])
        if group and group[4] == "private" and not is_active_member(store, row[2], owner):
            raise HTTPException(404, "Post not found")
    return row


def _repost_preview(store, repost_of_id: str | None, requester: str) -> dict | None:
    if not repost_of_id:
        return None
    orig = post_row(store, repost_of_id)
    if not orig or orig[6] or _post_removed(store, repost_of_id) or _is_blocked_pair(store, requester, orig[1]):
        return None
    if orig[2]:
        group = group_row(store, orig[2])
        if group and group[4] == "private" and not is_active_member(store, orig[2], requester):
            return None
    orig_prof = profile_by_owner(store, orig[1])
    return {
        "id": orig[0],
        "owner": orig[1],
        "author": {
            "owner": orig[1],
            "user_id": orig[1],
            "handle": orig_prof[1] if orig_prof else ("demo" if orig[1] == "demo" else "you"),
            "display_name": orig_prof[2] if orig_prof else "",
        },
        "group_id": orig[2],
        "text": orig[3],
        "flair": orig[10] if len(orig) > 10 and orig[10] is not None else "",
        "tags": _post_tags(store, orig[0]),
        "created_at": orig[8],
        "updated_at": orig[9],
        "provenance": orig[7],
    }


def present_post(store, row, requester):
    pid, owner, group_id, text, revision, pinned, deleted, prov, created, updated = row[:10]
    flair = row[10] if len(row) > 10 and row[10] is not None else ""
    repost_of_id = row[11] if len(row) > 11 else None
    prof = profile_by_owner(store, owner)
    reactions = store.db.execute(
        "SELECT COUNT(*) FROM cm_reactions WHERE target_type='post' AND target_id=?", (pid,)).fetchone()[0]
    comments = store.db.execute("SELECT COUNT(*) FROM cm_comments WHERE post_id=?", (pid,)).fetchone()[0]
    reacted = bool(store.db.execute(
        "SELECT 1 FROM cm_reactions WHERE owner=? AND target_type='post' AND target_id=?", (requester, pid)).fetchone())
    bookmarked = bool(store.db.execute(
        "SELECT 1 FROM cm_bookmarks WHERE owner=? AND post_id=?", (requester, pid)).fetchone())
    upvotes, downvotes, vote_score, my_vote, has_votes = _vote_stats(store, "post", pid, requester)
    score = vote_score if has_votes else reactions
    return {"id": pid, "owner": owner, "author": {"owner": owner, "user_id": owner,
            "handle": prof[1] if prof else ("demo" if owner == "demo" else "you"),
            "display_name": prof[2] if prof else ""},
            "group_id": group_id, "text": text, "revision": revision, "pinned": bool(pinned),
            "flair": flair, "repost_of_id": repost_of_id,
            "repost_preview": _repost_preview(store, repost_of_id, requester),
            "tags": _post_tags(store, pid),
            "score": score, "vote_score": vote_score, "upvotes": upvotes, "downvotes": downvotes,
            "my_vote": my_vote,
            "provenance": prov, "as_of": updated, "created_at": created, "updated_at": updated,
            "reactions": reactions, "reaction_count": reactions, "reacted": reacted,
            "comments": comments, "comment_count": comments, "bookmarked": bookmarked,
            "mine": owner == requester}


def present_comment(store, row, requester):
    cid, post_id, owner, parent_id, text, prov, created = row
    prof = profile_by_owner(store, owner)
    _, _, score, my_vote, _ = _vote_stats(store, "comment", cid, requester)
    return {"id": cid, "post_id": post_id, "owner": owner, "parent_id": parent_id, "text": text,
            "author": {"owner": owner, "user_id": owner, "handle": prof[1] if prof else "you",
                       "display_name": prof[2] if prof else ""},
            "score": score, "my_vote": my_vote,
            "provenance": prov, "as_of": created, "created_at": created, "mine": owner == requester}


def notify_mentions(store, actor, text, post_id, comment_id=None, group_id=None):
    for handle in dict.fromkeys(m.lower() for m in MENTION_RE.findall(text or "")):
        target = profile_by_handle(store, handle)
        if target:
            cm.notify(store, target[0], actor, "mention", f"mention:{comment_id or post_id}:{target[0]}",
                      text=text, post_id=post_id, comment_id=comment_id, group_id=group_id)


def log_moderation(store, group_id, actor, action, target_type, target_id, detail):
    lid = uuid4().hex
    store.db.execute(
        "INSERT INTO cm_group_moderation_log (id,group_id,actor,action,target_type,target_id,detail,undone,created_at) VALUES (?,?,?,?,?,?,?,0,?)",
        (lid, group_id, actor, action, target_type, target_id, json.dumps(detail), cm.now()))
    return lid


def present_log(row):
    return {"id": row[0], "group_id": row[1], "actor": row[2], "action": row[3], "target_type": row[4],
            "target_id": row[5], "detail": json.loads(row[6] or "{}"), "undone": bool(row[7]),
            "undone_by": row[8], "created_at": row[9], "as_of": row[9]}


def resolve_member_target(store, identifier):
    """Identifier may be an owner id or a profile handle."""
    prof = profile_by_handle(store, identifier)
    return prof[0] if prof else identifier


# ---------------------------------------------------------------- models
class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handle: str = Field(min_length=3, max_length=30)
    display_name: str = Field(default="", max_length=80)
    bio: str = Field(default="", max_length=500)
    area: str = Field(default="", max_length=80)
    interests: list[str] = Field(default_factory=list, max_length=20)
    age_band: str = Field(min_length=1, max_length=30)
    privacy: str = Field(default="public", pattern="^(public|private|followers)$")

    @field_validator("handle")
    @classmethod
    def _handle(cls, v):
        v = v.strip().lower()
        if not HANDLE_RE.match(v):
            raise ValueError("Handle must be 3-30 chars of a-z, 0-9 or _")
        return v


class PostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    group_id: str | None = Field(default=None, max_length=100)
    flair: str = Field(default="", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Write something first")
        return v

    @field_validator("flair")
    @classmethod
    def _flair(cls, v):
        v = (v or "").strip()
        if v not in ALLOWED_FLAIRS:
            raise ValueError("Invalid flair")
        return v


class PostEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    flair: str | None = Field(default=None, max_length=40)
    tags: list[str] | None = Field(default=None, max_length=10)

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Write something first")
        return v

    @field_validator("flair")
    @classmethod
    def _flair(cls, v):
        if v is None:
            return None
        v = v.strip()
        if v not in ALLOWED_FLAIRS:
            raise ValueError("Invalid flair")
        return v


class VoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int

    @field_validator("value")
    @classmethod
    def _value(cls, v):
        if v not in (-1, 0, 1):
            raise ValueError("value must be -1, 0, or 1")
        return v


class RepostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=2000)
    group_id: str | None = Field(default=None, max_length=100)
    flair: str = Field(default="", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("flair")
    @classmethod
    def _flair(cls, v):
        v = (v or "").strip()
        if v not in ALLOWED_FLAIRS:
            raise ValueError("Invalid flair")
        return v


class MuteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(pattern="^(owner|group|tag)$")
    target: str = Field(min_length=1, max_length=100)


class CommentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    parent_id: str | None = Field(default=None, max_length=100)

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Write something first")
        return v


class ReactionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(default="like", max_length=20)


class GroupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    handle: str | None = Field(default=None, max_length=40)
    description: str = Field(default="", max_length=500)
    visibility: str = Field(default="public", pattern="^(public|private)$")


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handle: str | None = Field(default=None, max_length=100)
    owner: str | None = Field(default=None, max_length=100)


class PinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: str = Field(min_length=1, max_length=100)


class ModeratorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handle: str | None = Field(default=None, max_length=100)
    owner: str | None = Field(default=None, max_length=100)
    role: str = Field(default="moderator", pattern="^(moderator|member|owner)$")


class UndoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    log_id: str | None = Field(default=None, max_length=100)


# ---------------------------------------------------------------- profiles
@router.put("/api/community/profiles/me")
def upsert_profile(body: ProfileIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        if cm.is_non_adult_band(body.age_band):
            raise HTTPException(403, "Community is adults-only (18+) for this demo. Under-18 accounts are not admitted; no profile was created.")
        if not cm.is_adult_band(body.age_band):
            raise HTTPException(422, "age_band must declare an adult band (for example '18+')")
        existing = profile_by_handle(store, body.handle)
        if existing and existing[0] != owner:
            raise HTTPException(409, "Handle already taken")
        stamp = cm.now()
        if profile_by_owner(store, owner):
            store.db.execute(
                "UPDATE cm_profiles SET handle=?,display_name=?,bio=?,area=?,interests=?,age_band=?,privacy=?,updated_at=? WHERE owner=?",
                (body.handle, body.display_name, body.bio, body.area, json.dumps(body.interests), body.age_band, body.privacy, stamp, owner))
        else:
            store.db.execute(
                "INSERT INTO cm_profiles (owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,'user_supplied',?,?)",
                (owner, body.handle, body.display_name, body.bio, body.area, json.dumps(body.interests), body.age_band, body.privacy, stamp, stamp))
        store.db.commit()
        return {"profile": present_profile(profile_by_owner(store, owner), owner)}


@router.post("/api/community/profiles")
def create_profile(body: ProfileIn, request: Request):
    return upsert_profile(body, request)


@router.get("/api/community/profiles/me")
def my_profile(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = profile_by_owner(store, owner)
        # No profile yet is a normal state, not an error: 200 keeps the browser console clean (E6 FAIL 8).
        return {"profile": present_profile(row, owner) if row else None}


@router.get("/api/community/profiles/{handle}")
def get_profile(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = profile_by_handle(store, handle)
        if not row:
            raise HTTPException(404, "Profile not found")
        if row[0] != owner and _is_blocked_pair(store, owner, row[0]):
            raise HTTPException(404, "Profile not found")
        if row[7] == "private" and row[0] != owner:
            raise HTTPException(404, "Profile not found")
        if row[7] == "followers" and row[0] != owner:
            if not store.db.execute("SELECT 1 FROM cm_follows WHERE follower=? AND followee=?", (owner, row[0])).fetchone():
                # Followers-only: hide private fields, keep public identity.
                out = present_profile(row, owner)
                out.update(bio="", area="", interests=[])
                return {"profile": out}
        return {"profile": present_profile(row, owner)}


# ---------------------------------------------------------------- follows
def _follow(store, owner, handle):
    target = profile_by_handle(store, handle)
    if not target:
        raise HTTPException(404, "Profile not found")
    if target[0] == owner:
        raise HTTPException(400, "You cannot follow yourself")
    store.db.execute("INSERT OR IGNORE INTO cm_follows VALUES (?,?,?)", (owner, target[0], cm.now()))
    store.db.commit()
    return {"following": True, "handle": target[1], "followee": target[0]}


@router.post("/api/community/follows/{handle}")
def follow_handle(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return _follow(store, owner, handle)


@router.post("/api/community/follows")
def follow_body(body: InviteIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        ident = body.handle or body.owner
        if not ident:
            raise HTTPException(422, "handle is required")
        target_owner = resolve_member_target(store, ident)
        prof = profile_by_owner(store, target_owner)
        if not prof:
            raise HTTPException(404, "Profile not found")
        return _follow(store, owner, prof[1])


@router.delete("/api/community/follows/{handle}")
def unfollow_handle(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        target = profile_by_handle(store, handle)
        if not target:
            raise HTTPException(404, "Profile not found")
        store.db.execute("DELETE FROM cm_follows WHERE follower=? AND followee=?", (owner, target[0]))
        store.db.commit()
        return {"following": False, "handle": target[1]}


@router.get("/api/community/follows")
def list_follows(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        rows = store.db.execute(
            "SELECT f.followee,p.handle FROM cm_follows f LEFT JOIN cm_profiles p ON p.owner=f.followee WHERE f.follower=? ORDER BY f.created_at",
            (owner,)).fetchall()
        return {"follows": [{"owner": r[0], "handle": r[1]} for r in rows],
                "following": [{"owner": r[0], "handle": r[1]} for r in rows]}


# ---------------------------------------------------------------- posts
def _create_post(store, owner, text, group_id, flair="", tags=None, repost_of_id=None):
    if group_id:
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if not is_active_member(store, group_id, owner):
            raise HTTPException(403, "Join the group before posting")
    pid = uuid4().hex
    stamp = cm.now()
    clean_flair = (flair or "").strip()
    if clean_flair not in ALLOWED_FLAIRS:
        raise HTTPException(422, "Invalid flair")
    store.db.execute(
        "INSERT INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at,flair,repost_of_id) VALUES (?,?,?,?,1,0,0,'user_supplied',?,?,?,?)",
        (pid, owner, group_id, text, stamp, stamp, clean_flair, repost_of_id))
    store.db.execute("INSERT INTO cm_post_revisions VALUES (?,?,?,?)", (pid, 1, text, stamp))
    _sync_post_tags(store, pid, text, tags, stamp)
    return pid


def _split_pref_allows(store, owner: str, kind: str) -> bool:
    """When cm_memory_preferences has an explicit row, enforce its split switch; otherwise keep legacy consent behavior."""
    try:
        row = store.db.execute(
            "SELECT remember_saved_discussions, remember_public_posts FROM cm_memory_preferences WHERE owner=?",
            (owner,),
        ).fetchone()
    except Exception:
        return True
    if not row:
        return True
    return bool(row[0]) if kind == "saved" else bool(row[1])


def _remember_public_post(request, store, owner, post_id, text, group_id):
    if group_id:
        group = group_row(store, group_id)
        if group is None or group[4] != "public":
            return
    if not _split_pref_allows(store, owner, "public"):
        return
    from .memory import remember
    remember(request, record_id=f"cmpost:{post_id}", source_id=f"community:post:{post_id}", text=text, author_id=owner)


@router.post("/api/community/posts")
def create_post(body: PostIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        pid = _create_post(store, owner, body.text, body.group_id, flair=body.flair, tags=body.tags)
        notify_mentions(store, owner, body.text, pid, group_id=body.group_id)
        store.db.commit()
        _remember_public_post(request, store, owner, pid, body.text, body.group_id)
        return {"post": present_post(store, post_row(store, pid), owner)}


@router.post("/api/community/posts/{post_id}/repost")
def repost_post(post_id: str, request: Request, body: RepostIn | None = None):
    store, owner = scope(request)
    payload = body or RepostIn()
    with store.lock:
        cm.setup(store)
        orig = post_row(store, post_id)
        if not orig or orig[6] or _post_removed(store, post_id) or _is_blocked_pair(store, owner, orig[1]):
            raise HTTPException(404, "Post not found")
        if orig[2]:
            orig_group = group_row(store, orig[2])
            if orig_group and orig_group[4] == "private":
                if not is_active_member(store, orig[2], owner):
                    raise HTTPException(403, "Cannot repost from a private group")
                if payload.group_id != orig[2]:
                    raise HTTPException(403, "Private group posts cannot be reposted outside the group")
        quote_text = (payload.text or "").strip()
        pid = _create_post(
            store,
            owner,
            quote_text,
            payload.group_id,
            flair=payload.flair,
            tags=payload.tags,
            repost_of_id=post_id,
        )
        cm.notify(
            store,
            orig[1],
            owner,
            "repost",
            f"repost:{pid}",
            text=quote_text or orig[3],
            post_id=pid,
            group_id=payload.group_id,
        )
        if quote_text:
            notify_mentions(store, owner, quote_text, pid, group_id=payload.group_id)
        store.db.commit()
        if quote_text:
            _remember_public_post(request, store, owner, pid, quote_text, payload.group_id)
        return {"post": present_post(store, post_row(store, pid), owner)}


@router.get("/api/community/posts/{post_id}")
def get_post(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return {"post": present_post(store, require_visible_post(store, owner, post_id), owner)}


@router.put("/api/community/posts/{post_id}")
def edit_post_put(post_id: str, body: PostEditIn, request: Request):
    return _edit_post(post_id, body, request)


@router.patch("/api/community/posts/{post_id}")
def edit_post_patch(post_id: str, body: PostEditIn, request: Request):
    return _edit_post(post_id, body, request)


def _edit_post(post_id, body, request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = post_row(store, post_id)
        if not row or row[6] or row[1] != owner:
            raise HTTPException(404, "Post not found")
        revision = row[4] + 1
        stamp = cm.now()
        next_flair = body.flair if body.flair is not None else (row[10] if len(row) > 10 and row[10] is not None else "")
        store.db.execute(
            "UPDATE cm_posts SET text=?,flair=?,revision=?,updated_at=? WHERE id=?",
            (body.text, next_flair, revision, stamp, post_id),
        )
        store.db.execute("INSERT OR IGNORE INTO cm_post_revisions VALUES (?,?,?,?)", (post_id, revision, body.text, stamp))
        _sync_post_tags(store, post_id, body.text, body.tags, stamp)
        store.db.commit()
        return {"post": present_post(store, post_row(store, post_id), owner)}


@router.delete("/api/community/posts/{post_id}")
def delete_post(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = post_row(store, post_id)
        if not row or row[6] or row[1] != owner:
            raise HTTPException(404, "Post not found")
        store.db.execute("UPDATE cm_posts SET deleted=1,updated_at=? WHERE id=?", (cm.now(), post_id))
        store.db.commit()
        return {"deleted": post_id}


@router.get("/api/community/posts/{post_id}/revisions")
def post_revisions(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = require_visible_post(store, owner, post_id)
        rows = store.db.execute(
            "SELECT revision,text,created_at FROM cm_post_revisions WHERE post_id=? ORDER BY revision", (post_id,)).fetchall()
        return {"post_id": post_id, "revisions": [{"revision": r[0], "text": r[1], "created_at": r[2]} for r in rows],
                "current_revision": row[4]}


# ---------------------------------------------------------------- comments
@router.post("/api/community/posts/{post_id}/comments")
def add_comment(post_id: str, body: CommentIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        post = require_visible_post(store, owner, post_id)
        parent = None
        if body.parent_id:
            parent = store.db.execute(
                "SELECT id,post_id,owner,parent_id,text,provenance,created_at FROM cm_comments WHERE id=?",
                (body.parent_id,)).fetchone()
            if not parent:
                raise HTTPException(404, "Parent comment not found")
            if parent[1] != post_id:
                raise HTTPException(400, "Parent comment belongs to a different post")
        cid = uuid4().hex
        store.db.execute(
            "INSERT INTO cm_comments (id,post_id,owner,parent_id,text,provenance,created_at) VALUES (?,?,?,?,?,'user_supplied',?)",
            (cid, post_id, owner, body.parent_id, body.text, cm.now()))
        cm.notify(store, post[1], owner, "reply", f"reply:comment:{cid}", text=body.text,
                  post_id=post_id, comment_id=cid, group_id=post[2])
        if parent and parent[2] != post[1]:
            cm.notify(store, parent[2], owner, "reply", f"reply:parent:{cid}", text=body.text,
                      post_id=post_id, comment_id=cid, group_id=post[2])
        notify_mentions(store, owner, body.text, post_id, comment_id=cid, group_id=post[2])
        store.db.commit()
        row = store.db.execute(
            "SELECT id,post_id,owner,parent_id,text,provenance,created_at FROM cm_comments WHERE id=?", (cid,)).fetchone()
        return {"comment": present_comment(store, row, owner)}


@router.get("/api/community/posts/{post_id}/comments")
def list_comments(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        require_visible_post(store, owner, post_id)
        blocked = _blocked_owners(store, owner)
        rows = store.db.execute(
            "SELECT id,post_id,owner,parent_id,text,provenance,created_at FROM cm_comments WHERE post_id=? ORDER BY created_at",
            (post_id,)).fetchall()
        return {"comments": [present_comment(store, r, owner) for r in rows if r[2] not in blocked]}


# ---------------------------------------------------------------- voting
def _set_vote(store, owner: str, target_type: str, target_id: str, value: int):
    store.db.execute(
        "DELETE FROM cm_votes WHERE owner=? AND target_type=? AND target_id=?",
        (owner, target_type, target_id),
    )
    if value != 0:
        store.db.execute(
            "INSERT INTO cm_votes (owner,target_type,target_id,value,created_at) VALUES (?,?,?,?,?)",
            (owner, target_type, target_id, value, cm.now()),
        )
    store.db.commit()


@router.post("/api/community/posts/{post_id}/vote")
def vote_post(post_id: str, body: VoteIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        require_visible_post(store, owner, post_id)
        _set_vote(store, owner, "post", post_id, body.value)
        upvotes, downvotes, vote_score, my_vote, has_votes = _vote_stats(store, "post", post_id, owner)
        reactions = store.db.execute(
            "SELECT COUNT(*) FROM cm_reactions WHERE target_type='post' AND target_id=?", (post_id,)
        ).fetchone()[0]
        score = vote_score if has_votes else reactions
        return {"post_id": post_id, "score": score, "upvotes": upvotes, "downvotes": downvotes, "my_vote": my_vote}


@router.post("/api/community/comments/{comment_id}/vote")
def vote_comment(comment_id: str, body: VoteIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        crow = store.db.execute(
            "SELECT id,post_id,owner FROM cm_comments WHERE id=?", (comment_id,)
        ).fetchone()
        if not crow or _is_blocked_pair(store, owner, crow[2]):
            raise HTTPException(404, "Comment not found")
        require_visible_post(store, owner, crow[1])
        _set_vote(store, owner, "comment", comment_id, body.value)
        _, _, score, my_vote, _ = _vote_stats(store, "comment", comment_id, owner)
        return {"comment_id": comment_id, "score": score, "my_vote": my_vote}


# ---------------------------------------------------------------- reactions / bookmarks
def _toggle_reaction(store, owner, post_id, kind):
    require_visible_post(store, owner, post_id)
    existing = store.db.execute(
        "SELECT 1 FROM cm_reactions WHERE owner=? AND target_type='post' AND target_id=? AND kind=?",
        (owner, post_id, kind)).fetchone()
    if existing:
        store.db.execute("DELETE FROM cm_reactions WHERE owner=? AND target_type='post' AND target_id=? AND kind=?",
                         (owner, post_id, kind))
        reacted = False
    else:
        store.db.execute("INSERT INTO cm_reactions VALUES (?, 'post', ?, ?, ?)", (owner, post_id, kind, cm.now()))
        reacted = True
    store.db.commit()
    count = store.db.execute(
        "SELECT COUNT(*) FROM cm_reactions WHERE target_type='post' AND target_id=?", (post_id,)).fetchone()[0]
    return {"post_id": post_id, "kind": kind, "reacted": reacted, "active": reacted, "count": count, "reactions": count}


@router.post("/api/community/posts/{post_id}/reactions")
def toggle_reaction(post_id: str, body: ReactionIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return _toggle_reaction(store, owner, post_id, body.kind)


@router.post("/api/community/posts/{post_id}/react")
def toggle_reaction_alias(post_id: str, request: Request, body: ReactionIn | None = None):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return _toggle_reaction(store, owner, post_id, (body.kind if body else "like"))


@router.post("/api/community/posts/{post_id}/bookmarks")
def add_bookmark(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        require_visible_post(store, owner, post_id)
        store.db.execute("INSERT OR IGNORE INTO cm_bookmarks VALUES (?,?,?)", (owner, post_id, cm.now()))
        store.db.commit()
        row = post_row(store, post_id)
        if _split_pref_allows(store, owner, "saved"):
            from .memory import remember
            remember(request, record_id=f"cmsave:{post_id}", source_id=f"community:post:{post_id}", text=row[3], author_id=row[1])
        return {"post_id": post_id, "bookmarked": True}


@router.delete("/api/community/posts/{post_id}/bookmarks")
def remove_bookmark(post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        store.db.execute("DELETE FROM cm_bookmarks WHERE owner=? AND post_id=?", (owner, post_id))
        store.db.commit()
        return {"post_id": post_id, "bookmarked": False}


@router.post("/api/community/bookmarks/{post_id}")
def add_bookmark_alias(post_id: str, request: Request):
    return add_bookmark(post_id, request)


@router.delete("/api/community/bookmarks/{post_id}")
def remove_bookmark_alias(post_id: str, request: Request):
    return remove_bookmark(post_id, request)


@router.get("/api/community/bookmarks")
def list_bookmarks(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        rows = store.db.execute(
            """SELECT p.id,p.owner,p.group_id,p.text,p.revision,p.pinned,p.deleted,p.provenance,p.created_at,p.updated_at,p.flair,p.repost_of_id
               FROM cm_bookmarks b JOIN cm_posts p ON p.id=b.post_id
               WHERE b.owner=? AND p.deleted=0 ORDER BY b.created_at DESC""", (owner,)).fetchall()
        posts = []
        for r in rows:
            try:
                require_visible_post(store, owner, r[0])
            except HTTPException:
                continue
            posts.append(present_post(store, r, owner))
        return {"bookmarks": posts, "posts": posts}


# ---------------------------------------------------------------- tags / feed / search
def _can_see_post_row(store, row, owner: str, active_groups: set[str], blocked: set[str]) -> bool:
    if row[1] in blocked or _post_removed(store, row[0]):
        return False
    if row[2]:
        g = group_row(store, row[2])
        if g and g[4] == "private" and row[2] not in active_groups:
            return False
    return True


def _feed_sort_key(post: dict, sort: str, now_ts: float):
    ts = _parse_ts(post.get("created_at", ""))
    pid = post["id"]
    upvotes = post.get("upvotes", 0)
    downvotes = post.get("downvotes", 0)
    vote_score = post.get("vote_score", 0)
    reactions = post.get("reactions", 0)
    comments = post.get("comments", 0)
    score = post.get("score", 0)
    if sort == "hot":
        sign = 1 if score > 0 else (-1 if score < 0 else 0)
        hot = sign * math.log10(max(1, abs(score))) + ts / 45000.0
        return (round(hot, 9), score, ts, pid)
    if sort == "top":
        return (vote_score + reactions, ts, pid)
    if sort == "rising":
        age_hours = max(0.0, (now_ts - ts) / 3600.0)
        net = upvotes - downvotes
        if net < 0:
            velocity = net / (age_hours + 0.25)
        else:
            velocity = (net + reactions + comments * 1.5) / (age_hours + 0.25)
        return (velocity, net + comments, ts, pid)
    if sort == "controversial":
        total = upvotes + downvotes
        if upvotes <= 0 or downvotes <= 0:
            controversy = 0.0
        else:
            balance = min(upvotes, downvotes) / max(upvotes, downvotes)
            controversy = float(total) ** balance
        return (controversy, total, ts, pid)
    # default: "new"
    return (post.get("created_at", ""), pid)


@router.get("/api/community/tags/trending")
def trending_tags(request: Request, limit: int = Query(default=15, ge=1, le=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        blocked = _blocked_owners(store, owner)
        groups = {
            r[0]
            for r in store.db.execute(
                "SELECT group_id FROM cm_group_members WHERE owner=? AND status='active'", (owner,)
            ).fetchall()
        }
        rows = store.db.execute(
            f"SELECT {POST_COLS} FROM cm_posts WHERE deleted=0"
        ).fetchall()
        counts: dict[str, int] = {}
        for r in rows:
            if not _can_see_post_row(store, r, owner, groups, blocked):
                continue
            for t in _post_tags(store, r[0]):
                counts[t] = counts.get(t, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return {"tags": [{"tag": t, "count": c} for t, c in ranked]}


@router.get("/api/community/feed")
def feed(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    sort: str = Query(default="new", pattern="^(hot|top|new|rising|controversial)$"),
    tag: str | None = Query(default=None, max_length=60),
):
    store, owner = scope(request)
    clean_tag = (tag or "").strip().lstrip("#").lower()
    with store.lock:
        cm.setup(store)
        followed = {r[0] for r in store.db.execute("SELECT followee FROM cm_follows WHERE follower=?", (owner,)).fetchall()}
        groups = {r[0] for r in store.db.execute(
            "SELECT group_id FROM cm_group_members WHERE owner=? AND status='active'", (owner,)).fetchall()}
        blocked = _blocked_owners(store, owner)
        muted_owners, muted_groups, muted_tags = _muted_sets(store, owner)
        rows = store.db.execute(
            f"SELECT {POST_COLS} FROM cm_posts WHERE deleted=0 ORDER BY created_at DESC, id DESC"
        ).fetchall()
        out = []
        for r in rows:
            if not _can_see_post_row(store, r, owner, groups, blocked):
                continue
            if r[1] in muted_owners or (r[2] and r[2] in muted_groups):
                continue
            tags = _post_tags(store, r[0])
            if muted_tags and (set(tags) & muted_tags):
                continue
            if clean_tag:
                if clean_tag not in tags:
                    continue
            elif not (r[1] == owner or r[1] in followed or (r[2] and r[2] in groups)):
                continue
            out.append(present_post(store, r, owner))
        now_ts = datetime.now(timezone.utc).timestamp()
        out.sort(key=lambda p: _feed_sort_key(p, sort, now_ts), reverse=True)
        out = out[:limit]
        return {"posts": out, "empty": len(out) == 0, "sort": sort, "tag": clean_tag or None}


@router.get("/api/community/search")
def search(request: Request, q: str = Query(default="", max_length=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        blocked = _blocked_owners(store, owner)
        term = f"%{q.strip().lower()}%"
        grows = store.db.execute("SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups").fetchall()
        groups_out = []
        for g in grows:
            member = member_row(store, g[0], owner)
            if g[4] == "private" and not (member and member[3] == "active"):
                continue
            if not q.strip() or q.strip().lower() in (g[1] + " " + g[2] + " " + g[3]).lower():
                groups_out.append(present_group(store, g, owner))
        prows = store.db.execute(
            "SELECT owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at FROM cm_profiles WHERE privacy='public'").fetchall()
        profiles_out = [present_profile(r, owner) for r in prows
                        if r[0] not in blocked and (not q.strip() or q.strip().lower() in (r[1] + " " + r[2] + " " + r[4]).lower())]
        posts_out = []
        if q.strip():
            for r in store.db.execute(
                    f"SELECT {POST_COLS} FROM cm_posts WHERE deleted=0 AND lower(text) LIKE ?", (term,)).fetchall():
                try:
                    require_visible_post(store, owner, r[0])
                except HTTPException:
                    continue
                posts_out.append(present_post(store, r, owner))
        return {"groups": groups_out, "profiles": profiles_out, "posts": posts_out, "q": q}


# ---------------------------------------------------------------- groups (CM-B3)
@router.post("/api/community/groups")
def create_group(body: GroupIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        handle = (body.handle or re.sub(r"[^a-z0-9_]+", "-", body.name.strip().lower()).strip("-") or "group")[:40]
        if store.db.execute("SELECT 1 FROM cm_groups WHERE handle=?", (handle,)).fetchone():
            raise HTTPException(409, "Group handle already taken")
        gid = uuid4().hex
        stamp = cm.now()
        store.db.execute(
            "INSERT INTO cm_groups (id,name,handle,description,visibility,owner,provenance,created_at) VALUES (?,?,?,?,?,?,'user_supplied',?)",
            (gid, body.name.strip(), handle, body.description, body.visibility, owner, stamp))
        store.db.execute(
            "INSERT INTO cm_group_members VALUES (?,?, 'owner', 'active', NULL, ?)", (gid, owner, stamp))
        store.db.commit()
        return {"group": present_group(store, group_row(store, gid), owner)}


@router.get("/api/community/groups")
def list_groups(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        rows = store.db.execute("SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups ORDER BY created_at").fetchall()
        out = []
        for g in rows:
            member = member_row(store, g[0], owner)
            if g[4] == "private" and not (member and member[3] == "active"):
                continue
            out.append(present_group(store, g, owner))
        return {"groups": out}


@router.get("/api/community/groups/{group_id}")
def get_group(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        return {"group": present_group(store, group, owner)}


@router.post("/api/community/groups/{group_id}/join")
def join_group(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        member = member_row(store, group_id, owner)
        if member and member[3] == "active":
            return {"group": present_group(store, group, owner), "membership": {"role": member[2], "status": "active"}}
        if group[4] == "private":
            # Invited users stay pending until a moderator approves; no invite -> refused.
            raise HTTPException(403, "This is a private group. An invitation and moderator approval are required to join.")
        store.db.execute(
            "INSERT OR IGNORE INTO cm_group_members VALUES (?,?, 'member', 'active', NULL, ?)", (group_id, owner, cm.now()))
        store.db.commit()
        from .memory import remember
        remember(request, record_id=f"cmjoin:{group_id}", source_id=f"community:group:{group_id}", text=group[1], author_id=owner, subject_path=group[2])
        return {"group": present_group(store, group_row(store, group_id), owner), "membership": {"role": "member", "status": "active"}}


@router.post("/api/community/groups/{group_id}/leave")
def leave_group(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if group[5] == owner:
            raise HTTPException(400, "The group owner cannot leave their own group")
        store.db.execute("DELETE FROM cm_group_members WHERE group_id=? AND owner=?", (group_id, owner))
        store.db.commit()
        return {"left": group_id}


@router.get("/api/community/groups/{group_id}/members")
def list_members(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        rows = store.db.execute(
            "SELECT group_id,owner,role,status,invited_by,created_at FROM cm_group_members WHERE group_id=? ORDER BY created_at",
            (group_id,)).fetchall()
        out = []
        for r in rows:
            prof = profile_by_owner(store, r[1])
            out.append({"owner": r[1], "user_id": r[1], "handle": prof[1] if prof else None,
                        "role": r[2], "status": r[3], "invited_by": r[4], "created_at": r[5]})
        return {"members": out}


@router.post("/api/community/groups/{group_id}/invite")
def invite_member(group_id: str, body: InviteIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        actor = member_row(store, group_id, owner)
        if not (actor and actor[3] == "active"):
            raise HTTPException(403, "Only group members can invite")
        ident = body.handle or body.owner
        if not ident:
            raise HTTPException(422, "handle is required")
        target_owner = resolve_member_target(store, ident)
        if not profile_by_owner(store, target_owner) and not member_row(store, group_id, target_owner):
            # Invitee must be identifiable (profile handle or known owner id from a profile).
            if not profile_by_handle(store, ident):
                raise HTTPException(404, "Invitee not found")
        existing = member_row(store, group_id, target_owner)
        if existing and existing[3] == "active":
            raise HTTPException(409, "Already a member")
        if existing:
            store.db.execute("UPDATE cm_group_members SET status='pending', invited_by=? WHERE group_id=? AND owner=?",
                             (owner, group_id, target_owner))
        else:
            store.db.execute("INSERT INTO cm_group_members VALUES (?,?, 'member', 'pending', ?, ?)",
                             (group_id, target_owner, owner, cm.now()))
        cm.notify(store, target_owner, owner, "group_activity", f"group-invite:{group_id}:{target_owner}",
                  text=f"You were invited to {group[1]}", group_id=group_id)
        store.db.commit()
        return {"invited": target_owner, "status": "pending", "group_id": group_id}


@router.post("/api/community/groups/{group_id}/members/{identifier}/approve")
def approve_member(group_id: str, identifier: str, request: Request):
    return _approve_member(group_id, identifier, request)


@router.post("/api/community/groups/{group_id}/approve")
def approve_member_body(group_id: str, body: InviteIn, request: Request):
    ident = body.handle or body.owner
    if not ident:
        raise HTTPException(422, "handle is required")
    return _approve_member(group_id, ident, request)


def _approve_member(group_id, identifier, request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        actor = member_row(store, group_id, owner)
        if not (actor and actor[3] == "active" and actor[2] in ("owner", "moderator")):
            raise HTTPException(403, "Only the owner or a moderator can approve members")
        target_owner = resolve_member_target(store, identifier)
        target = member_row(store, group_id, target_owner)
        if not target:
            raise HTTPException(404, "Membership not found")
        if target[3] == "active":
            return {"member": {"owner": target_owner, "role": target[2], "status": "active"}}
        store.db.execute("UPDATE cm_group_members SET status='active' WHERE group_id=? AND owner=?", (group_id, target_owner))
        cm.notify(store, target_owner, owner, "group_activity", f"group-approved:{group_id}:{target_owner}",
                  text=f"You were approved for {group[1]}", group_id=group_id)
        store.db.commit()
        return {"member": {"owner": target_owner, "role": target[2], "status": "active"}}


@router.post("/api/community/groups/{group_id}/moderators")
def name_moderator(group_id: str, body: ModeratorIn, request: Request):
    return _set_role(group_id, body, request)


@router.post("/api/community/groups/{group_id}/members/{identifier}/role")
def set_member_role(group_id: str, identifier: str, body: ModeratorIn, request: Request):
    merged = ModeratorIn(handle=identifier, role=body.role)
    return _set_role(group_id, merged, request)


def _set_role(group_id, body, request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if group[5] != owner:
            raise HTTPException(403, "Only the group owner can name moderators")
        ident = body.handle or body.owner
        if not ident:
            raise HTTPException(422, "handle is required")
        target_owner = resolve_member_target(store, ident)
        target = member_row(store, group_id, target_owner)
        if not target or target[3] != "active":
            raise HTTPException(404, "Active member not found")
        previous = target[2]
        store.db.execute("UPDATE cm_group_members SET role=? WHERE group_id=? AND owner=?", (body.role, group_id, target_owner))
        lid = log_moderation(store, group_id, owner, "set_role", "member", target_owner,
                             {"previous_role": previous, "new_role": body.role, "owner": target_owner})
        store.db.commit()
        return {"member": {"owner": target_owner, "role": body.role, "status": "active"}, "log_id": lid}


@router.post("/api/community/groups/{group_id}/members/{identifier}/remove")
def remove_member(group_id: str, identifier: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        actor = member_row(store, group_id, owner)
        if not (actor and actor[3] == "active" and actor[2] in ("owner", "moderator")):
            raise HTTPException(403, "Only the owner or a moderator can remove members")
        target_owner = resolve_member_target(store, identifier)
        target = member_row(store, group_id, target_owner)
        if not target:
            raise HTTPException(404, "Member not found")
        if target_owner == group[5]:
            raise HTTPException(400, "The group owner cannot be removed")
        store.db.execute("DELETE FROM cm_group_members WHERE group_id=? AND owner=?", (group_id, target_owner))
        lid = log_moderation(store, group_id, owner, "remove_member", "member", target_owner,
                             {"previous_role": target[2], "previous_status": target[3], "owner": target_owner})
        store.db.commit()
        return {"removed": target_owner, "log_id": lid}


def _pin_post(store, owner, group_id, post_id):
    group = require_group(store, group_id)
    group_access(store, group, owner)
    actor = member_row(store, group_id, owner)
    if not (actor and actor[3] == "active" and actor[2] in ("owner", "moderator")):
        raise HTTPException(403, "Only the owner or a moderator can pin posts")
    post = post_row(store, post_id)
    if not post or post[6]:
        raise HTTPException(404, "Post not found")
    if post[2] != group_id:
        raise HTTPException(400, "Post does not belong to this group")
    store.db.execute("UPDATE cm_posts SET pinned=1 WHERE id=?", (post_id,))
    lid = log_moderation(store, group_id, owner, "pin", "post", post_id, {"post_id": post_id})
    cm.notify(store, post[1], owner, "group_activity", f"group-pin:{group_id}:{post_id}:{lid}",
              text="Your post was pinned", post_id=post_id, group_id=group_id)
    store.db.commit()
    return {"pinned": post_id, "group_id": group_id, "log_id": lid}


@router.post("/api/community/groups/{group_id}/pin")
def pin_post(group_id: str, body: PinIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return _pin_post(store, owner, group_id, body.post_id)


@router.post("/api/community/groups/{group_id}/posts/{post_id}/pin")
def pin_post_path(group_id: str, post_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        return _pin_post(store, owner, group_id, post_id)


@router.post("/api/community/groups/{group_id}/posts")
def create_group_post(group_id: str, body: PostIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        merged = PostIn(text=body.text, group_id=group_id, flair=body.flair, tags=body.tags)
        pid = _create_post(store, owner, merged.text, group_id, flair=merged.flair, tags=merged.tags)
        notify_mentions(store, owner, merged.text, pid, group_id=group_id)
        store.db.commit()
        _remember_public_post(request, store, owner, pid, merged.text, group_id)
        return {"post": present_post(store, post_row(store, pid), owner)}


@router.get("/api/community/groups/{group_id}/posts")
def list_group_posts(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        blocked = _blocked_owners(store, owner)
        if group[4] == "public" or is_active_member(store, group_id, owner):
            rows = store.db.execute(
                f"SELECT {POST_COLS} FROM cm_posts WHERE group_id=? AND deleted=0 ORDER BY pinned DESC, created_at DESC",
                (group_id,)).fetchall()
            visible = [r for r in rows if r[1] not in blocked and not _post_removed(store, r[0])]
            return {"posts": [present_post(store, r, owner) for r in visible], "group": present_group(store, group, owner)}
        raise HTTPException(404, "Group not found")


@router.get("/api/community/groups/{group_id}/search")
def search_group(group_id: str, request: Request, q: str = Query(default="", max_length=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        blocked = _blocked_owners(store, owner)
        term = f"%{q.strip().lower()}%"
        rows = store.db.execute(
            f"SELECT {POST_COLS} FROM cm_posts WHERE group_id=? AND deleted=0 AND lower(text) LIKE ? ORDER BY created_at DESC",
            (group_id, term)).fetchall()
        visible = [r for r in rows if r[1] not in blocked and not _post_removed(store, r[0])]
        return {"posts": [present_post(store, r, owner) for r in visible], "q": q}


@router.get("/api/community/groups/{group_id}/moderation-log")
def moderation_log(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        actor = member_row(store, group_id, owner)
        if not (actor and actor[3] == "active" and actor[2] in ("owner", "moderator")):
            raise HTTPException(403, "Only the owner or a moderator can view the moderation log")
        rows = store.db.execute(
            "SELECT id,group_id,actor,action,target_type,target_id,detail,undone,undone_by,created_at FROM cm_group_moderation_log WHERE group_id=? ORDER BY created_at, id",
            (group_id,)).fetchall()
        logs = [present_log(r) for r in rows]
        return {"log": logs, "logs": logs, "moderation_log": logs}


@router.post("/api/community/groups/{group_id}/moderation/{log_id}/undo")
def undo_moderation(group_id: str, log_id: str, request: Request):
    return _undo_moderation(group_id, log_id, request)


@router.post("/api/community/groups/{group_id}/moderation/undo")
def undo_moderation_body(group_id: str, body: UndoIn, request: Request):
    if not body.log_id:
        raise HTTPException(422, "log_id is required")
    return _undo_moderation(group_id, body.log_id, request)


def _undo_moderation(group_id, log_id, request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if group[5] != owner:
            raise HTTPException(403, "Only the group owner can undo moderation actions")
        row = store.db.execute(
            "SELECT id,group_id,actor,action,target_type,target_id,detail,undone,undone_by,created_at FROM cm_group_moderation_log WHERE id=? AND group_id=?",
            (log_id, group_id)).fetchone()
        if not row:
            raise HTTPException(404, "Moderation log entry not found")
        if row[7]:
            raise HTTPException(409, "This action has already been undone")
        detail = json.loads(row[6] or "{}")
        if row[3] == "pin":
            store.db.execute("UPDATE cm_posts SET pinned=0 WHERE id=?", (row[5],))
        elif row[3] == "remove_member":
            target_owner = detail.get("owner") or row[5]
            store.db.execute(
                "INSERT OR IGNORE INTO cm_group_members VALUES (?,?,?, ?, NULL, ?)",
                (group_id, target_owner, detail.get("previous_role", "member"), detail.get("previous_status", "active"), cm.now()))
            store.db.execute("UPDATE cm_group_members SET role=?, status=? WHERE group_id=? AND owner=?",
                             (detail.get("previous_role", "member"), detail.get("previous_status", "active"), group_id, target_owner))
        elif row[3] == "set_role":
            target_owner = detail.get("owner") or row[5]
            store.db.execute("UPDATE cm_group_members SET role=? WHERE group_id=? AND owner=?",
                             (detail.get("previous_role", "member"), group_id, target_owner))
        store.db.execute("UPDATE cm_group_moderation_log SET undone=1, undone_by=? WHERE id=?", (owner, log_id))
        store.db.commit()
        updated = store.db.execute(
            "SELECT id,group_id,actor,action,target_type,target_id,detail,undone,undone_by,created_at FROM cm_group_moderation_log WHERE id=?",
            (log_id,)).fetchone()
        return {"undone": True, "log": present_log(updated)}


# ---------------------------------------------------------------- notifications / inbox (CM-B4, D3: no messenger)
def _present_notification(row):
    return {"id": row[0], "owner": row[1], "actor": row[2], "kind": row[3], "type": row[3],
            "post_id": row[4], "comment_id": row[5], "group_id": row[6], "text": row[7],
            "dedupe_key": row[8], "read": bool(row[9]), "is_read": bool(row[9]),
            "created_at": row[10], "as_of": row[10], "provenance": "user_supplied"}


@router.get("/api/community/notifications")
def list_notifications(request: Request, unread_only: bool = Query(default=False)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        blocked = _blocked_owners(store, owner)
        sql = "SELECT id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at FROM cm_notifications WHERE owner=?"
        if unread_only:
            sql += " AND is_read=0"
        sql += " ORDER BY created_at DESC, id DESC"
        rows = store.db.execute(sql, (owner,)).fetchall()
        filtered = []
        for r in rows:
            if r[2] and r[2] in blocked:
                continue
            if r[4]:
                if _post_removed(store, r[4]):
                    continue
                prow = post_row(store, r[4])
                if prow and prow[1] in blocked:
                    continue
            filtered.append(r)
        unread = sum(1 for r in filtered if not r[9])
        items = [_present_notification(r) for r in filtered]
        return {"notifications": items, "inbox": items, "unread": unread, "unread_count": unread}


@router.get("/api/community/inbox")
def inbox(request: Request, unread_only: bool = Query(default=False)):
    return list_notifications(request, unread_only=unread_only)


@router.post("/api/community/notifications/read-all")
def mark_all_read_first(request: Request):
    return mark_all_read(request)


@router.post("/api/community/notifications/{notification_id}/read")
def mark_read(notification_id: str, request: Request):
    return _mark_read(notification_id, request)


@router.post("/api/community/inbox/{notification_id}/read")
def mark_read_inbox(notification_id: str, request: Request):
    return _mark_read(notification_id, request)


@router.put("/api/community/notifications/{notification_id}/read")
def mark_read_put(notification_id: str, request: Request):
    return _mark_read(notification_id, request)


def _mark_read(notification_id, request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = store.db.execute("SELECT id FROM cm_notifications WHERE id=? AND owner=?", (notification_id, owner)).fetchone()
        if not row:
            raise HTTPException(404, "Notification not found")
        store.db.execute("UPDATE cm_notifications SET is_read=1 WHERE id=?", (notification_id,))
        store.db.commit()
        updated = store.db.execute(
            "SELECT id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at FROM cm_notifications WHERE id=?",
            (notification_id,)).fetchone()
        return {"notification": _present_notification(updated), "read": True}


@router.post("/api/community/notifications/read-all")
def mark_all_read(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        store.db.execute("UPDATE cm_notifications SET is_read=1 WHERE owner=?", (owner,))
        store.db.commit()
        return {"read_all": True, "unread_count": 0}


# ---------------------------------------------------------------- safety: block & mute
def _normalize_mute_target(store, kind: str, target: str) -> str:
    raw = (target or "").strip()
    if kind == "tag":
        return raw.lstrip("#").lower()
    if kind == "owner":
        prof = profile_by_handle(store, raw)
        return prof[0] if prof else raw
    if kind == "group":
        g = store.db.execute("SELECT id FROM cm_groups WHERE handle=?", (raw.lower(),)).fetchone()
        return g[0] if g else raw
    return raw


@router.post("/api/community/blocks/{handle}")
def block_user(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        target = profile_by_handle(store, handle)
        if not target:
            raise HTTPException(404, "Profile not found")
        if target[0] == owner:
            raise HTTPException(400, "You cannot block yourself")
        store.db.execute(
            "INSERT OR IGNORE INTO cm_user_blocks (owner,blocked_owner,created_at) VALUES (?,?,?)",
            (owner, target[0], cm.now()),
        )
        store.db.commit()
        return {"blocked": True, "handle": target[1], "blocked_owner": target[0]}


@router.delete("/api/community/blocks/{handle}")
def unblock_user(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        target = profile_by_handle(store, handle)
        if not target:
            raise HTTPException(404, "Profile not found")
        store.db.execute("DELETE FROM cm_user_blocks WHERE owner=? AND blocked_owner=?", (owner, target[0]))
        store.db.commit()
        return {"blocked": False, "handle": target[1], "blocked_owner": target[0]}


@router.post("/api/community/mutes")
def create_mute(body: MuteIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        norm_target = _normalize_mute_target(store, body.kind, body.target)
        if not norm_target:
            raise HTTPException(422, "target is required")
        store.db.execute(
            "INSERT OR IGNORE INTO cm_user_mutes (owner,kind,target,created_at) VALUES (?,?,?,?)",
            (owner, body.kind, norm_target, cm.now()),
        )
        store.db.commit()
        return {"muted": True, "kind": body.kind, "target": norm_target}


@router.delete("/api/community/mutes")
def delete_mute(
    request: Request,
    kind: str = Query(pattern="^(owner|group|tag)$"),
    target: str = Query(min_length=1, max_length=100),
):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        norm_target = _normalize_mute_target(store, kind, target)
        store.db.execute(
            "DELETE FROM cm_user_mutes WHERE owner=? AND kind=? AND (target=? OR target=?)",
            (owner, kind, norm_target, target.strip()),
        )
        store.db.commit()
        return {"muted": False, "kind": kind, "target": norm_target}


@router.get("/api/community/safety")
def get_safety(request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        block_rows = store.db.execute(
            """SELECT b.blocked_owner, p.handle, p.display_name
               FROM cm_user_blocks b LEFT JOIN cm_profiles p ON p.owner=b.blocked_owner
               WHERE b.owner=? ORDER BY b.created_at""",
            (owner,),
        ).fetchall()
        mute_rows = store.db.execute(
            "SELECT kind, target FROM cm_user_mutes WHERE owner=? ORDER BY created_at",
            (owner,),
        ).fetchall()
        return {
            "blocks": [
                {"owner": r[0], "handle": r[1] or "", "display_name": r[2] or ""}
                for r in block_rows
            ],
            "mutes": [{"kind": r[0], "target": r[1]} for r in mute_rows],
        }

