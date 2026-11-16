"""Official productivity APIs: Notion, Todoist, Trello, Linear."""
from __future__ import annotations

from ..base import RestConnector
from ..transport import bearer, call, require_credentials
from ..types import Page, PermanentFailure, RawItem
from . import register


def notion_probe(client, credentials) -> str:
    data = call(client, "GET", "https://api.notion.com/v1/users/me", headers=_notion(credentials))
    return data.get("name") or "Notion"


def notion_fetch(client, credentials, cursor) -> Page:
    body = {"page_size": 20, "filter": {"property": "object", "value": "page"}}
    if cursor and cursor.get("start_cursor"):
        body["start_cursor"] = cursor["start_cursor"]
    data = call(client, "POST", "https://api.notion.com/v1/search", headers=_notion(credentials), json_body=body)
    items = []
    for page in data.get("results") or []:
        title = _notion_title(page)
        items.append(
            RawItem(
                source_id=str(page.get("id") or ""),
                source_timestamp=str(page.get("last_edited_time") or ""),
                title=title,
                text=title,
                kind="page",
                metadata={"url": page.get("url") or ""},
            )
        )
    nxt = {"start_cursor": data["next_cursor"]} if data.get("has_more") and data.get("next_cursor") else None
    return Page(items=items, next_cursor=nxt)


def _notion(credentials) -> dict:
    require_credentials(credentials, "token")
    return {**bearer(credentials["token"]), "Notion-Version": "2022-06-28"}


def _notion_title(page: dict) -> str:
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            text = "".join(part.get("plain_text", "") for part in prop.get("title") or [])
            if text:
                return text
    return page.get("url") or str(page.get("id") or "Notion page")


def todoist_probe(client, credentials) -> str:
    require_credentials(credentials, "token")
    data = call(client, "GET", "https://api.todoist.com/api/v1/projects", headers=bearer(credentials["token"]))
    return "Todoist" if isinstance(data, list) else "Todoist"


def todoist_fetch(client, credentials, cursor) -> Page:
    require_credentials(credentials, "token")
    data = call(client, "GET", "https://api.todoist.com/api/v1/tasks", headers=bearer(credentials["token"]))
    items = []
    for task in data if isinstance(data, list) else data.get("results") or []:
        updated = str(task.get("updated_at") or task.get("added_at") or "")
        content = task.get("content") or ""
        description = task.get("description") or ""
        text = f"{content} — {description}".strip(" —") if description else content
        items.append(
            RawItem(
                source_id=str(task.get("id") or ""),
                source_timestamp=updated,
                title=content,
                text=text,
                kind="task",
                metadata={},
            )
        )
    return Page(items=items, next_cursor=None)


def trello_probe(client, credentials) -> str:
    data = call(client, "GET", "https://api.trello.com/1/members/me", headers={"Accept": "application/json"}, params=_trello_params(credentials, fields="username"))
    return data.get("username") or "Trello"


def trello_fetch(client, credentials, cursor) -> Page:
    params = _trello_params(credentials, fields="id,name,desc,dateLastActivity")
    data = call(client, "GET", "https://api.trello.com/1/members/me/cards", headers={"Accept": "application/json"}, params=params)
    items = []
    for card in data if isinstance(data, list) else []:
        name = card.get("name") or ""
        items.append(
            RawItem(
                source_id=str(card.get("id") or ""),
                source_timestamp=str(card.get("dateLastActivity") or ""),
                title=name,
                text=card.get("desc") or name,
                kind="card",
                metadata={},
            )
        )
    return Page(items=items, next_cursor=None)


def _trello_params(credentials, **extra):
    require_credentials(credentials, "key", "token")
    params = {"key": credentials["key"], "token": credentials["token"]}
    params.update(extra)
    return params


def linear_probe(client, credentials) -> str:
    data = _linear(client, credentials, "query { viewer { name email } }")
    viewer = (data.get("data") or {}).get("viewer") or {}
    return viewer.get("email") or viewer.get("name") or "Linear"


def linear_fetch(client, credentials, cursor) -> Page:
    data = _linear(
        client,
        credentials,
        "query { viewer { assignedIssues(first: 20) { nodes { id identifier title updatedAt description } } } }",
    )
    nodes = (((data.get("data") or {}).get("viewer") or {}).get("assignedIssues") or {}).get("nodes") or []
    items = []
    for issue in nodes:
        title = issue.get("title") or issue.get("identifier") or ""
        items.append(
            RawItem(
                source_id=str(issue.get("identifier") or issue.get("id") or ""),
                source_timestamp=str(issue.get("updatedAt") or ""),
                title=title,
                text=issue.get("description") or title,
                kind="issue",
                metadata={"linear_id": str(issue.get("id") or "")},
            )
        )
    return Page(items=items, next_cursor=None)


def _linear(client, credentials, query: str):
    require_credentials(credentials, "token")
    data = call(client, "POST", "https://api.linear.app/graphql", headers=bearer(credentials["token"]), json_body={"query": query})
    if data.get("errors"):
        raise PermanentFailure("Linear refused the request")
    return data


@register("notion")
def build_notion(spec):
    return RestConnector(spec, probe=notion_probe, fetch=notion_fetch)


@register("todoist")
def build_todoist(spec):
    return RestConnector(spec, probe=todoist_probe, fetch=todoist_fetch)


@register("trello")
def build_trello(spec):
    return RestConnector(spec, probe=trello_probe, fetch=trello_fetch)


@register("linear")
def build_linear(spec):
    return RestConnector(spec, probe=linear_probe, fetch=linear_fetch)
