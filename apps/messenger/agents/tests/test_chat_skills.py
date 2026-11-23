"""@messenger chat skills, offline: planner, leave optimiser, stickers, fact check, image ideas, and their routes."""
import datetime as dt
import json
import random
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from messenger_agents.app import Services, build_app
from messenger_agents.chat_skills import FactChecker, Msg, Planner, Stickers, best_leave, companions, extract_trip, image_ideas
from messenger_agents.config import ROOT, Settings
from messenger_agents.store import MemoryStore

EGYPT = [Msg(s, t) for s, t in [
    ("Arif Khan", "Random idea… Egypt in January? 🇪🇬"), ("me", "I'm in! I've wanted to see the pyramids for years"),
    ("Arif Khan", "Omar and Hana said they're taking leave in January too"), ("me", "Nice, let's make it a group trip. 10–12 days?"),
    ("Arif Khan", "Yes, but I only have 8 days of leave left 😅"), ("me", "Then we stretch it around the weekends"),
    ("Arif Khan", "Also heard the Grand Egyptian Museum is fully open now"),
    ("me", "Budget-wise I'm thinking around 1500 AED spending money"),
    ("Arif Khan", "Cairo + a Nile day trip. Flights from DXB are short, under 4 hours"), ("me", "Let's plan it properly this week")]]


def test_leave_window_uses_weekends_and_holidays():
    w = best_leave(2027, 1, 12, max_leave=8)
    assert (w["from"], w["to"], w["leaveDays"]) == ("2027-01-01", "2027-01-12", 7)  # New Year + 2 weekends
    assert "New Year's Day" in w["holidays"]


def test_companions_are_exact_contacts_from_leave_messages(contacts):
    people = companions(EGYPT, contacts, "arif")
    assert [c.id for c in people] == ["omar", "hana"]  # never Omer Farooq, never the partner unmentioned


def test_companions_empty_without_a_mention(contacts):
    ctx = [Msg("me", "plan a trip to europe next december")]
    assert companions(ctx, contacts, "arif") == []  # planning alone never suggests a group


async def test_plan_suggests_unrecognized_names_for_confirmation(contacts):
    ctx = [Msg("Arif Khan", "Omar and Zane said they're taking leave in January too")]
    out = await Planner(MemoryStore()).plan("u", ctx, contacts, "arif", today=dt.date(2026, 10, 8),
                                                  request="plan egypt in january with Omar and Zane")
    group = next(s for s in out["steps"] if s["kind"] == "group")
    assert group["data"]["members"] == ["omar"] and group["data"]["suggested"] == ["Zane"]
    assert "Zane" in group["detail"]


async def test_plan_has_no_group_step_without_any_mention(contacts):
    ctx = [Msg("me", "plan a trip to europe next december")]
    out = await Planner(MemoryStore()).plan("u", ctx, contacts, "arif", today=dt.date(2026, 10, 8),
                                                  request="plan spain in december")
    assert [s["kind"] for s in out["steps"]] and not any(s["kind"] == "group" for s in out["steps"])


async def test_plan_files_leave_and_builds_every_step(contacts):
    store = MemoryStore()
    plan = await Planner(store).plan("demo", EGYPT, contacts, "arif", dt.date(2026, 10, 8),
                                           request="plan egypt from 2027-01-01 to 2027-01-12")
    kinds = [s["kind"] for s in plan["steps"]]
    assert kinds[:5] == ["leave", "email", "flights", "budget", "reminder"]  # nobody named → solo, no group
    assert not any(s["kind"] == "docs" for s in plan["steps"])  # no passport-check step
    flights = plan["steps"][2]["data"]["query"]
    assert flights == {"from": "DXB", "to": "CAI", "depart": "2027-01-01", "return": "2027-01-12", "passengers": 1, "cabin": "economy"}
    assert plan["steps"][3]["data"]["aed"] == 1500 and plan["steps"][3]["data"]["currency"] == "EGP"
    nadi = await store.get("nadi:" + "demo")
    assert len(nadi) == 1 and nadi[0]["balanceAfter"] == 23
    again = await Planner(store).plan("demo", EGYPT, contacts, "arif", dt.date(2026, 10, 8),
                                            request="plan egypt from 2027-01-01 to 2027-01-12")
    assert again["steps"][0]["data"]["nadi"]["duplicate"] and len(await store.get("nadi:" + "demo")) == 1


async def test_plan_without_dates_asks_instead_of_picking_a_window(contacts):
    store = MemoryStore()
    plan = await Planner(store).plan("demo", EGYPT, contacts, "arif", dt.date(2026, 10, 8))
    assert plan.get("needsDates") is True and plan["summary"] == "DXB → CAI · 1 traveller"
    assert [s["kind"] for s in plan["steps"]] == ["dates"]  # minimal: no Omar/Hana from history, no flights yet
    assert (await store.get("nadi:demo") or []) == []  # no leave filed while dates are missing


def test_stickers_missing_packs_refuse_traversal(tmp_path):
    st = Stickers(tmp_path)
    assert st.pick(EGYPT, random.Random(1)) is None
    assert st.packs() == []
    assert st.file("nile-days", "../../index.html") is None and st.file("nile-days", "01-pyramids.svg") is None


async def test_fact_check_demo_and_fallback():
    out = await FactChecker(None, None).check("Also heard the Grand Egyptian Museum is fully open now", EGYPT)
    assert out["verdict"] == "mostly_true" and out["mode"] == "demo"
    assert (await FactChecker(None, None).check("the moon is cheese", EGYPT))["fallback"] is True


async def test_image_ideas_offline_are_three_and_about_the_chat():
    out = await image_ideas(None, EGYPT, "create image about this")
    assert len(out["ideas"]) == 3 and "pyramids" in out["ideas"][0]["prompt"]
    assert "falcon" in (await image_ideas(None, EGYPT, "create an image of a falcon"))["subject"]


@pytest.fixture
def client(tmp_path):
    cfg = replace(Settings(), live=False, watch_enabled=False, data_dir=tmp_path)
    with TestClient(build_app(Services(cfg, MemoryStore()))) as c:
        yield c


def test_skill_routes(client, contacts):
    ctx = [{"sender": m.sender, "text": m.text} for m in EGYPT]
    plan = client.post("/agents/messenger/plan", json={"context": ctx, "contacts": [c.__dict__ for c in contacts],
                                                    "chatPartner": "arif",
                                                    "request": "plan egypt from 2027-01-01 to 2027-01-12"}).json()
    assert plan["title"].startswith("Egypt")
    assert client.post("/agents/messenger/stickers", json={"context": ctx}).status_code == 404
    assert client.post("/agents/messenger/factcheck", json={"context": ctx, "target": ctx[6]["text"]}).json()["verdict"] == "mostly_true"


# ---------------------------------------------------------------- "is this true" on photos (multimodal)
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
BALI = PNG


class RecordingLLM:
    """Answers each step and records what it was given (no network)."""
    def __init__(self):
        self.calls = []

    async def json(self, system, user, schema, name, images=None):
        self.calls.append({"name": name, "user": user, "images": images})
        if name == "factcheck_photo":
            return {"seen": "Rice terraces with palm trees", "claim": "This is Tegalalang", "query": "Tegalalang rice terraces Bali"}
        return {"claim": "This is Tegalalang", "verdict": "mostly_true", "answer": "Looks like it.", "sources": [1]}


class RecordingSearch:
    def __init__(self):
        self.queries = []

    async def search(self, query, recent):
        self.queries.append(query)
        return [{"title": "Tegallalang", "url": "https://en.wikipedia.org/wiki/Tegallalang", "content": "Rice terraces near Ubud."}]


async def test_photo_check_looks_then_searches_what_it_saw_then_judges_with_the_photo():
    llm, search = RecordingLLM(), RecordingSearch()
    out = await FactChecker(llm, search).check("[photo: Tegalalang terraces — adding this to day 2]", EGYPT, [BALI])
    assert [c["name"] for c in llm.calls] == ["factcheck_photo", "factcheck"]
    assert llm.calls[0]["images"] == [BALI] and llm.calls[1]["images"] == [BALI]       # the verdict sees the photo too
    assert search.queries == ["Tegalalang rice terraces Bali"]                       # searched what the photo shows
    assert "Rice terraces with palm trees" in llm.calls[1]["user"]
    assert out["photos"] == 1 and out["status"].startswith("Looked at 1 photo · Checked 1 sources")
    assert out["sources"][0]["domain"] == "en.wikipedia.org" and out["mode"] == "live"


async def test_text_claims_still_skip_the_photo_step():
    llm, search = RecordingLLM(), RecordingSearch()
    await FactChecker(llm, search).check("Grand Egyptian Museum is fully open", EGYPT)
    assert [c["name"] for c in llm.calls] == ["factcheck"] and llm.calls[0]["images"] is None


async def test_photo_without_a_local_seed_is_not_invented():
    out = await FactChecker(None, None).check("[photo]", [], [PNG])
    assert out["mode"] == "offline" and out["fallback"] is True and out["photos"] == 1


def test_photo_inputs_inline_app_pictures_and_refuse_everything_else(tmp_path):
    public = tmp_path / "public"
    (public / "photos").mkdir(parents=True)
    (public / "photos" / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")
    (tmp_path / "secret.jpg").write_bytes(b"x")
    (public / "notes.txt").write_text("x")
    checker = FactChecker(None, None, public)
    from messenger_agents.chat_skills import photo_inputs
    assert photo_inputs(["/photos/a.jpg"], public)[0].startswith("data:image/jpeg;base64,")
    assert photo_inputs([BALI, PNG], public) == [BALI, PNG]
    for bad in ["/../secret.jpg", "/photos/../../secret.jpg", "/notes.txt", "/photos/missing.jpg", "http://evil.test/a.jpg",
                "file:///etc/passwd", "data:text/html;base64,PHNjcmlwdD4=", "javascript:alert(1)"]:
        with pytest.raises(ValueError):
            photo_inputs([bad], public)
    with pytest.raises(ValueError):
        photo_inputs([BALI] * 4, public)
    assert checker.public == public


def test_factcheck_route_takes_photos_and_rejects_bad_ones(client):
    ok = client.post("/agents/messenger/factcheck", json={"target": "[photo]", "images": [PNG]}).json()
    assert ok["mode"] == "offline" and ok["photos"] == 1
    assert client.post("/agents/messenger/factcheck", json={"target": "x", "images": ["file:///etc/passwd"]}).status_code == 400
    assert client.post("/agents/messenger/factcheck", json={"target": "x", "images": [BALI] * 4}).status_code == 422


async def test_look_answers_from_the_photo_itself():
    seen = []

    class LookLLM:
        async def json(self, system, user, schema, name, images=None):
            seen.append((name, images))
            return {"answer": "A man harvesting rice."}

    from messenger_agents.skills.look import look
    out = await look(LookLLM(), "What is he doing in the image?", EGYPT, [BALI])
    assert seen[0] == ("messenger_look", [BALI])
    assert out["mode"] == "live" and out["answer"] == "A man harvesting rice." and out["photos"] == 1
    demo = await look(None, "What is this?", [], [PNG])
    assert demo["mode"] == "offline" and demo["fallback"] is True


def test_look_route_answers_and_rejects_bad_ones(client):
    ok = client.post("/agents/messenger/look", json={"target": "What is he doing?", "images": [PNG]}).json()
    assert ok["mode"] == "offline" and ok["photos"] == 1 and ok["fallback"] is True
    assert client.post("/agents/messenger/look", json={"target": "x", "images": ["file:///etc/passwd"]}).status_code == 400


async def test_plan_keeps_the_date_in_the_request_and_books_an_all_day_trip(contacts):
    out = await Planner(MemoryStore()).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                                 request="@messenger plan the vacation to egypt on 2 january")
    assert out["calendar"]["from"] == "2027-01-02"                        # the asked date, not the optimiser's pick
    leave = next(s for s in out["steps"] if s["kind"] == "leave")["data"]["leave"]
    assert leave["fixed"] is True and leave["from"] == "2027-01-02"
    trip = next(s for s in out["steps"] if s["kind"] == "reminder")["data"]["events"][1]
    assert trip["start"] == "2027-01-02T00:00:00" and trip["end"].endswith("T00:00:00")   # all-day in the calendar


def test_start_date_phrasings():
    from messenger_agents.chat_skills import start_date
    today = dt.date(2026, 10, 8)
    for text in ["on 2 january", "2nd of Jan", "January 2", "from jan 2nd for 5 days"]:
        assert start_date(text, today) == dt.date(2027, 1, 2), text
    assert start_date("plan egypt", today) is None and start_date("on 31 february", today) is None
    assert start_date("on 20 october", today) == dt.date(2026, 10, 20)


async def test_plan_drafts_the_leave_email_to_the_approver(contacts):
    out = await Planner(MemoryStore()).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                                 request="plan egypt on 2 january")
    email = next(s for s in out["steps"] if s["kind"] == "email")
    assert email["data"]["to"] == "r.khalfan@nadi.ae" and email["title"] == "Added draft email to r.khalfan@nadi.ae"
    assert "NADI-" in email["data"]["body"] and "2 Jan" in email["data"]["subject"] and "not sent" in email["detail"]


async def test_repro_kazakhistan_with_sara_asks_for_dates(contacts):
    """The reported bug: "@messenger plan trip to kazakhistan with sara aswell" in the Arif chat planned
    Egypt/Cairo in January with Omar/Hana. It must plan Kazakhstan with you + Sara and ask for dates."""
    store = MemoryStore()
    out = await Planner(store).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                          request="@messenger plan trip to kazakhistan with sara aswell")
    assert out.get("needsDates") is True
    assert "Egypt" not in out["title"] and "Cairo" not in out["summary"] and "CAI" not in out["summary"]
    assert out["summary"] == "With Sara · DXB → ALA · 2 travellers"
    assert [s["kind"] for s in out["steps"]] == ["dates", "group"]
    group = next(s for s in out["steps"] if s["kind"] == "group")
    assert group["data"]["members"] == ["sara"]  # only who the request named: not the partner, never Omar/Hana
    assert (await store.get("nadi:u") or []) == []  # no leave filed while dates are missing


def test_kazakhistan_typo_resolves_to_kazakhstan():
    from messenger_agents.chat_skills import extract_trip
    for text in ["plan trip to kazakhistan", "plan trip to kazakstan", "plan trip to almaty"]:
        trip = extract_trip([], dt.date(2026, 10, 8), text)
        assert trip["place"]["name"] == "Kazakhstan" and trip["place"]["iata"] == "ALA", text
    trip = extract_trip([], dt.date(2026, 10, 8), "plan trip to astana")
    assert trip["place"]["name"] == "Kazakhstan" and trip["place"]["iata"] == "NQZ"


async def test_unknown_destination_asks_and_never_reuses_history(contacts):
    store = MemoryStore()
    out = await Planner(store).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                          request="plan trip to atlantis")
    assert "ask" in out and "Egypt" not in out["ask"] and "Cairo" not in out["ask"]
    assert (await store.get("nadi:u") or []) == []


async def test_repro_complete_with_dates_uses_actual_range_and_passengers(contacts):
    store = MemoryStore()
    out = await Planner(store).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                          request="@messenger plan trip to kazakhistan with sara aswell "
                                                  "from 2027-05-01 to 2027-05-07")
    assert out.get("needsDates") is None and out["title"].startswith("Kazakhstan")
    assert out["destination"] == {"country": "Kazakhstan", "city": "Almaty", "iata": "ALA"}
    leave = next(s for s in out["steps"] if s["kind"] == "leave")["data"]["leave"]
    # The weekend stays in the range (7 days); only the 5 workdays count as leave.
    assert (leave["from"], leave["to"], leave["days"], leave["leaveDays"]) == ("2027-05-01", "2027-05-07", 7, 5)
    flights = next(s for s in out["steps"] if s["kind"] == "flights")["data"]["query"]
    assert flights == {"from": "DXB", "to": "ALA", "depart": "2027-05-01", "return": "2027-05-07",
                       "passengers": 2, "cabin": "economy"}
    group = next(s for s in out["steps"] if s["kind"] == "group")
    assert group["data"]["members"] == ["sara"]
    assert not any(s["kind"] == "docs" for s in out["steps"])  # no passport-check step
    assert next(s for s in out["steps"] if s["kind"] == "budget")["data"]["currency"] == "KZT"
    assert len(await store.get("nadi:" + "u")) == 1


async def test_date_change_keeps_participants(contacts):
    store = MemoryStore()
    first = await Planner(store).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                            request="plan trip to kazakhistan with sara "
                                                    "from 2027-05-01 to 2027-05-07")
    members = next(s for s in first["steps"] if s["kind"] == "group")["data"]["members"]
    second = await Planner(store).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 8),
                                             request="plan trip to kazakhistan from 2027-06-04 to 2027-06-08",
                                             keep_members=members)
    group = next(s for s in second["steps"] if s["kind"] == "group")
    assert group["data"]["members"] == members == ["sara"]  # nobody asked twice
    assert "kept when the dates changed" in group["detail"]
    leave = next(s for s in second["steps"] if s["kind"] == "leave")["data"]["leave"]
    assert (leave["from"], leave["to"], leave["days"], leave["leaveDays"]) == ("2027-06-04", "2027-06-08", 5, 3)
    flights = next(s for s in second["steps"] if s["kind"] == "flights")["data"]["query"]
    assert (flights["depart"], flights["return"], flights["passengers"]) == ("2027-06-04", "2027-06-08", 2)


def test_request_names_resolve_exact_despite_similar_namesake(contacts):
    """Typed "sara" is exactly Sara Ali — the near-namesake Sarah Malik must not steal or block it."""
    from messenger_agents.chat_skills import resolve_request_companions
    found, ambiguous, unknown, named = resolve_request_companions(
        "@messenger plan trip to kazakhistan with sara aswell", contacts, "arif")
    assert [c.id for c in found] == ["sara"] and ambiguous == [] and unknown == [] and named is True


async def test_ambiguous_first_name_asks():
    from messenger_agents.contacts import Contact
    dupes = [Contact("sara1", "Sara One"), Contact("sara2", "Sara Two")]
    out = await Planner(MemoryStore()).plan("u", [], dupes, None, today=dt.date(2026, 10, 8),
                                                  request="plan trip to spain with sara")
    assert "ask" in out and "Sara One" in out["ask"] and "Sara Two" in out["ask"]


def test_fixed_leave_keeps_weekends_and_counts_workdays():
    from messenger_agents.chat_skills import fixed_leave
    w = fixed_leave(dt.date(2027, 5, 1), dt.date(2027, 5, 4))  # Sat–Tue
    assert (w["from"], w["to"], w["days"], w["leaveDays"]) == ("2027-05-01", "2027-05-04", 4, 2)


def test_request_dates_iso_range_and_day_month():
    from messenger_agents.chat_skills import request_dates
    today = dt.date(2026, 10, 8)
    assert request_dates("from 2027-05-01 to 2027-05-07", today) == (dt.date(2027, 5, 1), dt.date(2027, 5, 7))
    assert request_dates("plan egypt", today) == (None, None)
    assert request_dates("on 2 january for 5 days", today) == (dt.date(2027, 1, 2), dt.date(2027, 1, 6))


def test_relative_start_days():
    from messenger_agents.chat_skills import relative_start
    fri = dt.date(2026, 10, 9)  # a Friday
    assert relative_start("visit alexandria next friday", fri) == dt.date(2026, 10, 16)
    assert relative_start("this friday", fri) == dt.date(2026, 10, 16)  # today is Friday: the coming one
    assert relative_start("on sunday", fri) == dt.date(2026, 10, 11)
    assert relative_start("next sun", fri) == dt.date(2026, 10, 18)
    assert relative_start("tomorrow", fri) == dt.date(2026, 10, 10)
    assert relative_start("this weekend", fri) == dt.date(2026, 10, 10)
    assert relative_start("next week", fri) == dt.date(2026, 10, 12)
    assert relative_start("sunny beach, money saved", fri) is None  # short forms only after next/this/on


async def test_repro_alexandria_typo_next_friday_is_solo(contacts):
    """The reported bug: "@messenger plan a visit to alesxandria next friday" planned Cairo with Omar and Hana
    and asked for dates. It must plan Alexandria, start next Friday, and be just you."""
    out = await Planner(MemoryStore()).plan("u", EGYPT, contacts, "arif", today=dt.date(2026, 10, 9),
                                                  request="@messenger plan a visit to alesxandria next friday")
    assert out.get("needsDates") is None and out["destination"]["iata"] == "HBE"
    assert out["calendar"]["from"] == "2026-10-16"
    assert not any(s["kind"] == "group" for s in out["steps"])
    flights = next(s for s in out["steps"] if s["kind"] == "flights")["data"]["query"]
    assert flights["passengers"] == 1


def test_partner_travels_only_when_named(contacts):
    from messenger_agents.chat_skills import resolve_request_companions
    found, _, _, named = resolve_request_companions("plan trip to spain with arif and sara", contacts, "arif")
    assert [c.id for c in found] == ["arif", "sara"] and named
    found, _, _, named = resolve_request_companions("plan trip to spain", contacts, "arif")
    assert found == [] and not named


def test_airport_codes_and_new_places_resolve():
    for text, iata in [("plan a trip to CPH on 2027-01-02", "CPH"), ("prepare trip to denmark", "CPH"),
                       ("prepare plan trip for khazakhistan", "ALA"), ("visit to alesxandria", "HBE")]:
        assert extract_trip([], dt.date(2026, 10, 9), text)["place"]["iata"] == iata, text
