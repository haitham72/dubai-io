"""Official social and media reads with narrow scopes. No scrapers."""
from __future__ import annotations

from ..base import RestConnector
from ..stamp import preserve_timestamp
from ..transport import bearer, call, require_credentials
from ..types import Page, PermanentFailure, RawItem
from . import register


def reddit_probe(client, credentials) -> str:
    data = call(client, "GET", "https://oauth.reddit.com/api/v1/me", headers=_reddit(credentials))
    return data.get("name") or "Reddit"


def reddit_fetch(client, credentials, cursor) -> Page:
    headers = _reddit(credentials)
    me = call(client, "GET", "https://oauth.reddit.com/api/v1/me", headers=headers)
    name = me.get("name")
    if not name:
        raise PermanentFailure("Reddit did not return the account name")
    params = {"limit": "25"}
    if cursor and cursor.get("after"):
        params["after"] = cursor["after"]
    data = call(client, "GET", f"https://oauth.reddit.com/user/{name}/saved", headers=headers, params=params)
    items = []
    for child in ((data.get("data") or {}).get("children") or []):
        post = child.get("data") or {}
        title = post.get("title") or post.get("link_title") or ""
        body = post.get("selftext") or title
        items.append(
            RawItem(
                source_id=str(post.get("name") or post.get("id") or ""),
                source_timestamp=preserve_timestamp(post.get("created_utc")),
                title=title,
                text=body,
                kind="saved_post",
                metadata={},
            )
        )
    after = (data.get("data") or {}).get("after")
    return Page(items=items, next_cursor={"after": after} if after else None)


def _reddit(credentials) -> dict:
    require_credentials(credentials, "token")
    return {**bearer(credentials["token"]), "User-Agent": "dubai-io/1.0 (personal connector)"}


def x_probe(client, credentials) -> str:
    data = call(client, "GET", "https://api.x.com/2/users/me", headers=bearer(_token(credentials)))
    return ((data.get("data") or {}).get("username")) or "X"


def x_fetch(client, credentials, cursor) -> Page:
    headers = bearer(_token(credentials))
    me = call(client, "GET", "https://api.x.com/2/users/me", headers=headers)
    user_id = (me.get("data") or {}).get("id")
    if not user_id:
        raise PermanentFailure("X did not return the account id")
    params = {"max_results": "10", "tweet.fields": "created_at"}
    if cursor and cursor.get("next_token"):
        params["pagination_token"] = cursor["next_token"]
    data = call(client, "GET", f"https://api.x.com/2/users/{user_id}/tweets", headers=headers, params=params)
    items = []
    for tweet in data.get("data") or []:
        text = tweet.get("text") or ""
        items.append(
            RawItem(
                source_id=str(tweet.get("id") or ""),
                source_timestamp=str(tweet.get("created_at") or ""),
                title=text[:120],
                text=text,
                kind="post",
                metadata={},
            )
        )
    token = (data.get("meta") or {}).get("next_token")
    return Page(
        items=items,
        next_cursor={"next_token": token} if token else None,
        notice="These are the authenticated user's own posts. Direct messages were not requested.",
    )


def _token(credentials) -> str:
    require_credentials(credentials, "token")
    return credentials["token"]


def spotify_probe(client, credentials) -> str:
    data = call(client, "GET", "https://api.spotify.com/v1/me", headers=bearer(_token(credentials)))
    return data.get("display_name") or data.get("id") or "Spotify"


def spotify_fetch(client, credentials, cursor) -> Page:
    params = {"limit": "20"}
    if cursor and cursor.get("offset"):
        params["offset"] = cursor["offset"]
    data = call(client, "GET", "https://api.spotify.com/v1/me/tracks", headers=bearer(_token(credentials)), params=params)
    items = []
    for entry in data.get("items") or []:
        track = entry.get("track") or {}
        name = track.get("name") or ""
        artists = ", ".join(artist.get("name") or "" for artist in track.get("artists") or [])
        items.append(
            RawItem(
                source_id=str(track.get("id") or ""),
                source_timestamp=str(entry.get("added_at") or ""),
                title=name,
                text=f"{artists} — {name}".strip(" —"),
                kind="track",
                metadata={"artists": artists},
            )
        )
    nxt = None
    if data.get("next"):
        offset = int((cursor or {}).get("offset") or 0) + len(data.get("items") or [])
        nxt = {"offset": str(offset)}
    return Page(items=items, next_cursor=nxt)


def dropbox_probe(client, credentials) -> str:
    data = call(
        client,
        "POST",
        "https://api.dropboxapi.com/2/users/get_current_account",
        headers=bearer(_token(credentials)),
    )
    name = (data.get("name") or {}).get("display_name")
    return name or data.get("email") or "Dropbox"


def dropbox_fetch(client, credentials, cursor) -> Page:
    headers = {**bearer(_token(credentials)), "Content-Type": "application/json"}
    if cursor and cursor.get("cursor"):
        data = call(
            client,
            "POST",
            "https://api.dropboxapi.com/2/files/list_folder/continue",
            headers=headers,
            json_body={"cursor": cursor["cursor"]},
        )
    else:
        data = call(
            client,
            "POST",
            "https://api.dropboxapi.com/2/files/list_folder",
            headers=headers,
            json_body={"path": "", "limit": 30, "recursive": False},
        )
    items = []
    for entry in data.get("entries") or []:
        if entry.get(".tag") != "file":
            continue
        items.append(
            RawItem(
                source_id=str(entry.get("id") or ""),
                source_timestamp=str(entry.get("server_modified") or ""),
                title=entry.get("name") or "",
                text=entry.get("name") or "",
                kind="file",
                metadata={"size": entry.get("size"), "path": entry.get("path_display") or ""},
            )
        )
    nxt = {"cursor": data["cursor"]} if data.get("cursor") else None
    return Page(items=items, next_cursor=nxt)


@register("reddit")
def build_reddit(spec):
    return RestConnector(spec, probe=reddit_probe, fetch=reddit_fetch)


@register("x")
def build_x(spec):
    return RestConnector(spec, probe=x_probe, fetch=x_fetch)


@register("spotify")
def build_spotify(spec):
    return RestConnector(spec, probe=spotify_probe, fetch=spotify_fetch)


@register("dropbox")
def build_dropbox(spec):
    return RestConnector(spec, probe=dropbox_probe, fetch=dropbox_fetch)
