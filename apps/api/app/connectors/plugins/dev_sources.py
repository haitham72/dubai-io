"""Official developer APIs: GitHub, GitLab, Jira Cloud."""
from __future__ import annotations

from ..base import RestConnector
from ..hosts import public_https_origin
from ..transport import bearer, call, require_credentials
from ..types import Page, RawItem
from . import register


def github_probe(client, credentials) -> str:
    require_credentials(credentials, "token")
    data = call(client, "GET", "https://api.github.com/user", headers={**bearer(credentials["token"]), "X-GitHub-Api-Version": "2022-11-28"})
    return data.get("login") or "GitHub"


def github_fetch(client, credentials, cursor) -> Page:
    require_credentials(credentials, "token")
    headers = {**bearer(credentials["token"]), "X-GitHub-Api-Version": "2022-11-28"}
    params = {"per_page": "30", "all": "false"}
    if cursor and cursor.get("since"):
        params["since"] = cursor["since"]
    data = call(client, "GET", "https://api.github.com/notifications", headers=headers, params=params)
    items = []
    newest = (cursor or {}).get("since") or ""
    for note in data if isinstance(data, list) else []:
        updated = str(note.get("updated_at") or "")
        if updated > newest:
            newest = updated
        subject = (note.get("subject") or {}).get("title") or "Notification"
        repo = ((note.get("repository") or {}).get("full_name")) or ""
        items.append(
            RawItem(
                source_id=str(note.get("id") or ""),
                source_timestamp=updated,
                title=subject,
                text=f"{repo}: {subject}".strip(": "),
                kind="notification",
                metadata={"repository": repo},
            )
        )
    nxt = {"since": newest} if newest else None
    return Page(items=items, next_cursor=nxt)


def gitlab_probe(client, credentials) -> str:
    require_credentials(credentials, "token")
    base = _gitlab_base(credentials)
    data = call(client, "GET", f"{base}/api/v4/user", headers={"PRIVATE-TOKEN": credentials["token"], "Accept": "application/json"})
    return data.get("username") or "GitLab"


def gitlab_fetch(client, credentials, cursor) -> Page:
    require_credentials(credentials, "token")
    base = _gitlab_base(credentials)
    params = {"per_page": "20"}
    if cursor and cursor.get("after"):
        params["after"] = cursor["after"]
    data = call(
        client,
        "GET",
        f"{base}/api/v4/events",
        headers={"PRIVATE-TOKEN": credentials["token"], "Accept": "application/json"},
        params=params,
    )
    items = []
    newest = ""
    for event in data if isinstance(data, list) else []:
        created = str(event.get("created_at") or "")
        if created > newest:
            newest = created
        title = event.get("target_title") or event.get("action_name") or "GitLab event"
        items.append(
            RawItem(
                source_id=str(event.get("id") or ""),
                source_timestamp=created,
                title=str(title),
                text=f"{event.get('action_name') or ''} {title}".strip(),
                kind="event",
                metadata={"action": event.get("action_name") or ""},
            )
        )
    return Page(items=items, next_cursor={"after": newest} if newest else None)


def _gitlab_base(credentials) -> str:
    raw = credentials.get("api_base") or "https://gitlab.com"
    return public_https_origin(raw)


def jira_probe(client, credentials) -> str:
    site = _jira_site(credentials)
    data = call(client, "GET", f"{site}/rest/api/3/myself", headers=_jira_headers(credentials))
    return data.get("emailAddress") or data.get("displayName") or "Jira"


def jira_fetch(client, credentials, cursor) -> Page:
    site = _jira_site(credentials)
    params = {"jql": "assignee=currentUser() ORDER BY updated DESC", "maxResults": "20", "fields": "summary,updated,status"}
    if cursor and cursor.get("next_page_token"):
        params["nextPageToken"] = cursor["next_page_token"]
    data = call(client, "GET", f"{site}/rest/api/3/search/jql", headers=_jira_headers(credentials), params=params)
    items = []
    for issue in data.get("issues") or []:
        fields = issue.get("fields") or {}
        key = str(issue.get("key") or issue.get("id") or "")
        items.append(
            RawItem(
                source_id=key,
                source_timestamp=str(fields.get("updated") or ""),
                title=fields.get("summary") or key,
                text=fields.get("summary") or key,
                kind="issue",
                metadata={"jira_id": str(issue.get("id") or ""), "status": ((fields.get("status") or {}).get("name")) or ""},
            )
        )
    token = data.get("nextPageToken")
    return Page(items=items, next_cursor={"next_page_token": token} if token else None)


def _jira_site(credentials) -> str:
    require_credentials(credentials, "site", "email", "api_token")
    return public_https_origin(credentials["site"])


def _jira_headers(credentials) -> dict:
    import base64

    raw = f"{credentials['email']}:{credentials['api_token']}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode(), "Accept": "application/json"}


@register("github")
def build_github(spec):
    return RestConnector(spec, probe=github_probe, fetch=github_fetch)


@register("gitlab")
def build_gitlab(spec):
    return RestConnector(spec, probe=gitlab_probe, fetch=gitlab_fetch)


@register("jira")
def build_jira(spec):
    return RestConnector(spec, probe=jira_probe, fetch=jira_fetch)
