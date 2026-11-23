"""Community social-core routes (CM-B2/B3/B4). Adults-only, no messenger (D3)."""
import json
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..actions import COOKIE, engine
from . import store as cm

router = APIRouter(tags=["community"])
HANDLE_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MENTION_RE = re.compile(r"@([A-Za-z0-9_]{3,30})")


def scope(request: Request):
    store = engine().store
    return store, store.owner(request.cookies.get(COOKIE))


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


def post_row(store, post_id):
    return store.db.execute(
        "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE id=?",
        (post_id,)).fetchone()


def require_visible_post(store, owner, post_id):
    row = post_row(store, post_id)
    if not row or row[6]:
        raise HTTPException(404, "Post not found")
    if row[2]:
        group = group_row(store, row[2])
        if group and group[4] == "private" and not is_active_member(store, row[2], owner):
            raise HTTPException(404, "Post not found")
    return row


def present_post(store, row, requester):
    pid, owner, group_id, text, revision, pinned, deleted, prov, created, updated = row
    prof = profile_by_owner(store, owner)
    reactions = store.db.execute(
        "SELECT COUNT(*) FROM cm_reactions WHERE target_type='post' AND target_id=?", (pid,)).fetchone()[0]
    comments = store.db.execute("SELECT COUNT(*) FROM cm_comments WHERE post_id=?", (pid,)).fetchone()[0]
    reacted = bool(store.db.execute(
        "SELECT 1 FROM cm_reactions WHERE owner=? AND target_type='post' AND target_id=?", (requester, pid)).fetchone())
    bookmarked = bool(store.db.execute(
        "SELECT 1 FROM cm_bookmarks WHERE owner=? AND post_id=?", (requester, pid)).fetchone())
    return {"id": pid, "owner": owner, "author": {"owner": owner, "user_id": owner,
            "handle": prof[1] if prof else ("demo" if owner == "demo" else "you"),
            "display_name": prof[2] if prof else ""},
            "group_id": group_id, "text": text, "revision": revision, "pinned": bool(pinned),
            "provenance": prov, "as_of": updated, "created_at": created, "updated_at": updated,
            "reactions": reactions, "reaction_count": reactions, "reacted": reacted,
            "comments": comments, "comment_count": comments, "bookmarked": bookmarked,
            "mine": owner == requester}


def present_comment(store, row, requester):
    cid, post_id, owner, parent_id, text, prov, created = row
    prof = profile_by_owner(store, owner)
    return {"id": cid, "post_id": post_id, "owner": owner, "parent_id": parent_id, "text": text,
            "author": {"owner": owner, "user_id": owner, "handle": prof[1] if prof else "you",
                       "display_name": prof[2] if prof else ""},
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

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Write something first")
        return v


class PostEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def _text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Write something first")
        return v


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
        return {"profile": present_profile(require_profile_row(store, owner), owner)}


@router.get("/api/community/profiles/{handle}")
def get_profile(handle: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        row = profile_by_handle(store, handle)
        if not row:
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
def _create_post(store, owner, text, group_id):
    if group_id:
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if not is_active_member(store, group_id, owner):
            raise HTTPException(403, "Join the group before posting")
    pid = uuid4().hex
    stamp = cm.now()
    store.db.execute(
        "INSERT INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at) VALUES (?,?,?,?,1,0,0,'user_supplied',?,?)",
        (pid, owner, group_id, text, stamp, stamp))
    store.db.execute("INSERT INTO cm_post_revisions VALUES (?,?,?,?)", (pid, 1, text, stamp))
    return pid


@router.post("/api/community/posts")
def create_post(body: PostIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        pid = _create_post(store, owner, body.text, body.group_id)
        notify_mentions(store, owner, body.text, pid, group_id=body.group_id)
        store.db.commit()
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
        store.db.execute("UPDATE cm_posts SET text=?,revision=?,updated_at=? WHERE id=?", (body.text, revision, stamp, post_id))
        store.db.execute("INSERT OR IGNORE INTO cm_post_revisions VALUES (?,?,?,?)", (post_id, revision, body.text, stamp))
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
        rows = store.db.execute(
            "SELECT id,post_id,owner,parent_id,text,provenance,created_at FROM cm_comments WHERE post_id=? ORDER BY created_at",
            (post_id,)).fetchall()
        return {"comments": [present_comment(store, r, owner) for r in rows]}


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
            """SELECT p.id,p.owner,p.group_id,p.text,p.revision,p.pinned,p.deleted,p.provenance,p.created_at,p.updated_at
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


# ---------------------------------------------------------------- feed / search
@router.get("/api/community/feed")
def feed(request: Request, limit: int = Query(default=50, ge=1, le=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        followed = [r[0] for r in store.db.execute("SELECT followee FROM cm_follows WHERE follower=?", (owner,)).fetchall()]
        groups = [r[0] for r in store.db.execute(
            "SELECT group_id FROM cm_group_members WHERE owner=? AND status='active'", (owner,)).fetchall()]
        rows = store.db.execute(
            "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE deleted=0 ORDER BY created_at DESC, id DESC").fetchall()
        out = []
        for r in rows:
            if r[1] == owner or r[1] in followed or (r[2] and r[2] in groups):
                # Private-group fencing is redundant here (membership required) but keep it explicit.
                if r[2]:
                    g = group_row(store, r[2])
                    if g and g[4] == "private" and r[2] not in groups and r[1] != owner:
                        continue
                out.append(present_post(store, r, owner))
        out = out[:limit]
        return {"posts": out, "empty": len(out) == 0}


@router.get("/api/community/search")
def search(request: Request, q: str = Query(default="", max_length=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
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
                        if not q.strip() or q.strip().lower() in (r[1] + " " + r[2] + " " + r[4]).lower()]
        posts_out = []
        if q.strip():
            for r in store.db.execute(
                    "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE deleted=0 AND lower(text) LIKE ?", (term,)).fetchall():
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
        merged = PostIn(text=body.text, group_id=group_id)
        pid = _create_post(store, owner, merged.text, group_id)
        notify_mentions(store, owner, merged.text, pid, group_id=group_id)
        store.db.commit()
        return {"post": present_post(store, post_row(store, pid), owner)}


@router.get("/api/community/groups/{group_id}/posts")
def list_group_posts(group_id: str, request: Request):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        if group[4] == "public" or is_active_member(store, group_id, owner):
            rows = store.db.execute(
                "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE group_id=? AND deleted=0 ORDER BY pinned DESC, created_at DESC",
                (group_id,)).fetchall()
            return {"posts": [present_post(store, r, owner) for r in rows], "group": present_group(store, group, owner)}
        raise HTTPException(404, "Group not found")


@router.get("/api/community/groups/{group_id}/search")
def search_group(group_id: str, request: Request, q: str = Query(default="", max_length=100)):
    store, owner = scope(request)
    with store.lock:
        cm.setup(store)
        group = require_group(store, group_id)
        group_access(store, group, owner)
        term = f"%{q.strip().lower()}%"
        rows = store.db.execute(
            "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE group_id=? AND deleted=0 AND lower(text) LIKE ? ORDER BY created_at DESC",
            (group_id, term)).fetchall()
        return {"posts": [present_post(store, r, owner) for r in rows], "q": q}


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
        sql = "SELECT id,owner,actor,kind,post_id,comment_id,group_id,text,dedupe_key,is_read,created_at FROM cm_notifications WHERE owner=?"
        if unread_only:
            sql += " AND is_read=0"
        sql += " ORDER BY created_at DESC, id DESC"
        rows = store.db.execute(sql, (owner,)).fetchall()
        unread = store.db.execute("SELECT COUNT(*) FROM cm_notifications WHERE owner=? AND is_read=0", (owner,)).fetchone()[0]
        items = [_present_notification(r) for r in rows]
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

