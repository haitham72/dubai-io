"""Diwan events (MCP + Supabase images, max 3), the MCP client, the sticker builder's 3 options, and GIF search off."""
import datetime as dt
import json
import random
from dataclasses import replace

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from mirsal_agents.app import Services, build_app
from mirsal_agents.chat_skills import Msg, Stickers
from mirsal_agents.config import ROOT, Settings
from mirsal_agents.diwan import Diwan, SupabaseImages
from mirsal_agents.mcp_client import McpClient, McpError
from mirsal_agents.sticker_builder import StickerBuilder, giphy
from mirsal_agents.store import MemoryStore


async def test_demo_event_shows_yesterday_with_three_local_images():
    out = await Diwan(MemoryStore(), None, "upcoming_events", None).upcoming(dt.date(2026, 10, 8))
    (e,) = out["events"]
    assert e["when"] == "Yesterday" and e["date"] == "2026-10-07" and len(e["images"]) == 3
    assert e["source"] == "Diwan · demo" and out["mode"] == "demo"


@pytest.mark.parametrize("today,count,when", [("2026-10-02", 1, "360 days ago"), ("2026-10-09", 1, "2 days ago"), ("2026-09-20", 1, "348 days ago")])
async def test_pinned_anniversary_uses_most_recent_occurrence(today, count, when):
    out = await Diwan(MemoryStore(), None, "t", None).upcoming(dt.date.fromisoformat(today))
    assert len(out["events"]) == count and (not count or out["events"][0]["when"] == when)


async def test_pinned_demo_event_stays_after_its_date():
    out = await Diwan(MemoryStore(), None, "t", None).upcoming(dt.date(2026, 10, 14))
    (e,) = out["events"]
    assert e["id"] == "rashid-bin-saeed-anniversary" and e["date"] == "2026-10-07" and e["when"] == "7 days ago"


def mcp_server(events: list[dict], sse: bool = False):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        calls.append(body["method"])
        if "id" not in body:
            return httpx.Response(202)
        if body["method"] == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {}, "serverInfo": {"name": "diwan"}}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result}, headers={"mcp-session-id": "s1"})
        assert req.headers["mcp-session-id"] == "s1" and body["params"]["name"] == "upcoming_events"
        msg = {"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text", "text": json.dumps({"events": events})}]}}
        if sse:
            return httpx.Response(200, text=f"event: message\ndata: {json.dumps(msg)}\n\n", headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json=msg)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), calls


@pytest.mark.parametrize("sse", [False, True])
async def test_mcp_client_handshake_and_tool_call(sse):
    http, calls = mcp_server([{"title": "Flag Day", "date": "2026-11-03"}], sse)
    out = await McpClient("https://diwan.example/mcp", http=http).call("upcoming_events", {"days": 7})
    assert out["events"][0]["title"] == "Flag Day" and calls == ["initialize", "notifications/initialized", "tools/call"]


async def test_live_diwan_takes_only_three_supabase_images():
    mcp_http, _ = mcp_server([{"title": "Sheikh Rashid bin Saeed Al Maktoum death anniversary", "date": "2026-10-07", "image_folder": "rashid"}])

    def storage(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/storage/v1/object/list/diwan" and json.loads(req.content)["prefix"] == "rashid"
        return httpx.Response(200, json=[{"name": f"{i}.jpg"} for i in range(5)] + [{"name": "notes.txt"}])

    images = SupabaseImages("https://x.supabase.co", "anon", "diwan", httpx.AsyncClient(transport=httpx.MockTransport(storage)))
    out = await Diwan(MemoryStore(), McpClient("https://d/mcp", http=mcp_http), "upcoming_events", images).upcoming(dt.date(2026, 10, 8))
    assert out["mode"] == "live" and out["events"][0]["images"] == [
        f"https://x.supabase.co/storage/v1/object/public/diwan/rashid/{i}.jpg" for i in range(3)]


async def test_mcp_tool_error_is_raised():
    def handler(req):
        body = json.loads(req.content)
        if "id" not in body:
            return httpx.Response(202)
        result = {"isError": True, "content": [{"type": "text", "text": "boom"}]} if body["method"] == "tools/call" else {}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})
    with pytest.raises(McpError, match="boom"):
        await McpClient("https://d/mcp", http=httpx.AsyncClient(transport=httpx.MockTransport(handler))).call("t", {})


async def test_builder_demo_returns_three_options_best_match_first():
    out = await StickerBuilder(Stickers(ROOT / "public" / "stickers"), None).options(
        "sticker of this", [Msg("Arif", "Egypt in January? pyramids!")], random.Random(2))
    assert out["mode"] == "demo" and len(out["options"]) == 3 and out["options"][0]["id"] == "nile-days"
    assert all(len(o["stickers"]) == 8 for o in out["options"])


async def test_gifs_off_without_key():
    assert await giphy("", "cats") == {"mode": "off", "gifs": []}


def test_routes(tmp_path):
    cfg = replace(Settings(), live=False, watch_enabled=False, data_dir=tmp_path, diwan_mcp_url="", supabase_url="",
                  builder_mcp_url="", giphy_key="")
    with TestClient(build_app(Services(cfg, MemoryStore()))) as c:
        assert c.get("/agents/diwan/events").status_code == 200
        assert len(c.post("/agents/stickers/generate", json={"request": "x"}).json()["options"]) == 3
        assert c.get("/agents/gifs?q=hi").json()["mode"] == "off"


async def test_nadi_uses_its_mcp_when_connected():
    from mirsal_agents.chat_skills import Nadi
    calls = []

    def handler(req):
        body = json.loads(req.content)
        if "id" not in body:
            return httpx.Response(202)
        if body["method"] == "tools/call":
            calls.append(body["params"])
            out = {"ref": "NADI-LIVE-1", "status": "Submitted"}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"structuredContent": out, "content": []}})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {}})
    mcp = McpClient("https://nadi/mcp", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    out = await Nadi(MemoryStore(), mcp=mcp).file("demo", "2027-01-01", "2027-01-12", 7, "Trip")
    assert out["ref"] == "NADI-LIVE-1" and calls[0]["name"] == "file_leave" and calls[0]["arguments"]["leaveDays"] == 7


def test_connectors_report_what_they_wait_for(tmp_path):
    cfg = replace(Settings(), live=False, watch_enabled=False, data_dir=tmp_path, diwan_mcp_url="", supabase_url="",
                  builder_mcp_url="", giphy_key="", nadi_mcp_url="")
    with TestClient(build_app(Services(cfg, MemoryStore()))) as c:
        rows = {r["name"]: r for r in c.get("/agents/connectors").json()["connectors"]}
    assert rows["Diwan"]["state"] == "demo" and "DIWAN_MCP_URL" in rows["Diwan"]["waitsFor"]
    assert rows["Mirsal Builder (stickers)"]["kind"] == "mcp" and rows["GIPHY"]["waitsFor"] == ["GIPHY_API_KEY"]


# ---------------------------------------------------------------- "More from this picture" (Diwan more_from_image)
TODAY = dt.date(2026, 10, 8)


async def test_demo_event_marks_which_picture_has_more_and_returns_its_three_variations():
    diwan = Diwan(MemoryStore(), None, "upcoming_events", None)
    (e,) = (await diwan.upcoming(TODAY))["events"]
    assert e["more"] == ["/diwan/rashid-bin-saeed-anniversary/03.jpg"]
    out = await diwan.more_from_image(e["id"], e["more"][0], today=TODAY)
    assert [i["url"] for i in out["images"]] == [f"/diwan/rashid-bin-saeed-anniversary/03/03-0{n}.jpg" for n in (1, 2, 3)]
    assert out["images"][0]["width"] == 768 and out["source"] == "Diwan · demo" and out["image"] == "03.jpg"
    assert (await diwan.more_from_image(e["id"], "01.jpg", today=TODAY))["images"] == []  # no variations: honest empty


@pytest.mark.parametrize("image", ["", "..", "notes.txt", "03.jpg/..", ".hidden.jpg", "..\03.jpg", "a" * 130 + ".jpg"])
async def test_more_rejects_anything_but_a_plain_picture_name(image):
    with pytest.raises(ValueError):
        await Diwan(MemoryStore(), None, "t", None).more_from_image("rashid-bin-saeed-anniversary", image, today=TODAY)


@pytest.mark.parametrize("event,image", [("no-such-event", "03.jpg"), ("rashid-bin-saeed-anniversary", "99.jpg")])
async def test_more_only_for_this_events_own_pictures(event, image):
    with pytest.raises(LookupError):
        await Diwan(MemoryStore(), None, "t", None).more_from_image(event, image, today=TODAY)


def diwan_mcp(events: list[dict], more: dict | None = None, error: str = ""):
    """Mock Diwan MCP with both tools; records each tools/call (name, arguments)."""
    calls: list[tuple[str, dict]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        if "id" not in body:
            return httpx.Response(202)
        if body["method"] == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"capabilities": {}}})
        name, args = body["params"]["name"], body["params"]["arguments"]
        calls.append((name, args))
        if name == "more_from_image" and error:
            result = {"isError": True, "content": [{"type": "text", "text": error}]}
        else:
            result = {"structuredContent": {"events": events} if name == "upcoming_events" else more}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), calls


async def test_live_more_asks_the_diwan_mcp_with_the_contract_arguments():
    event = {"id": "ev", "title": "Flag Day", "date": "2026-10-08", "images": ["https://cdn/ev/02.jpg"], "more_from": ["02.jpg"]}
    more = {"images": [{"url": f"https://cdn/ev/02/02-0{n}.jpg", "width": 1080, "height": 1350} for n in (1, 2, 3, 4)]}
    http, calls = diwan_mcp([event], more)
    diwan = Diwan(MemoryStore(), McpClient("https://d/mcp", http=http), "upcoming_events", None)
    (e,) = (await diwan.upcoming(TODAY))["events"]
    assert e["more"] == ["https://cdn/ev/02.jpg"]
    out = await diwan.more_from_image("ev", "https://cdn/ev/02.jpg?v=2", 3, today=TODAY)
    assert calls[-1] == ("more_from_image", {"event_id": "ev", "image": "02.jpg", "count": 3})
    assert len(out["images"]) == 3 and out["mode"] == "live" and out["source"] == "Diwan"
    await diwan.more_from_image("ev", "02.jpg", 3, today=TODAY)
    assert sum(c[0] == "more_from_image" for c in calls) == 1  # cached for an hour


async def test_live_more_tool_error_surfaces():
    event = {"id": "ev", "title": "Flag Day", "date": "2026-10-08", "images": ["https://cdn/ev/02.jpg"]}
    http, _ = diwan_mcp([event], error="no variations stored")
    diwan = Diwan(MemoryStore(), McpClient("https://d/mcp", http=http), "upcoming_events", None)
    with pytest.raises(McpError, match="no variations"):
        await diwan.more_from_image("ev", "02.jpg", today=TODAY)


async def test_supabase_subfolder_named_after_a_picture_means_more():
    prefixes = []

    def storage(req: httpx.Request) -> httpx.Response:
        prefix = json.loads(req.content)["prefix"]
        prefixes.append(prefix)
        if prefix == "rashid":
            return httpx.Response(200, json=[{"name": "01.jpg", "id": "a"}, {"name": "03.jpg", "id": "b"}, {"name": "03", "id": None}])
        return httpx.Response(200, json=[{"name": f"03-0{n}.jpg", "id": str(n)} for n in (1, 2, 3)])

    images = SupabaseImages("https://x.supabase.co", "anon", "diwan", httpx.AsyncClient(transport=httpx.MockTransport(storage)))
    raw = [{"id": "rashid-bin-saeed-anniversary", "title": "Anniversary", "month": 10, "day": 7, "image_folder": "rashid"}]
    diwan = Diwan(MemoryStore(), None, "t", images)
    diwan._raw = lambda today: _async(raw)  # demo events, live pictures
    (e,) = (await diwan.upcoming(TODAY))["events"]
    assert e["more"] == ["https://x.supabase.co/storage/v1/object/public/diwan/rashid/03.jpg"]
    out = await diwan.more_from_image(e["id"], "03.jpg", today=TODAY)
    assert prefixes[-1] == "rashid/03" and out["images"][2]["url"].endswith("/diwan/rashid/03/03-03.jpg")


async def _async(value):
    return value


def test_more_route_status_codes(tmp_path):
    cfg = replace(Settings(), live=False, watch_enabled=False, data_dir=tmp_path, diwan_mcp_url="", supabase_url="")
    services = Services(cfg, MemoryStore())
    services.diwan.clock = lambda: TODAY
    with TestClient(build_app(services)) as c:
        ok = c.get("/agents/diwan/more", params={"event": "rashid-bin-saeed-anniversary", "image": "03.jpg"})
        assert ok.status_code == 200 and len(ok.json()["images"]) == 3
        assert c.get("/agents/diwan/more", params={"event": "rashid-bin-saeed-anniversary", "image": "../x"}).status_code == 400
        assert c.get("/agents/diwan/more", params={"event": "nope", "image": "03.jpg"}).status_code == 404
        assert any(t.get("tool") == "more_from_image" for t in c.get("/agents/trace").json())
