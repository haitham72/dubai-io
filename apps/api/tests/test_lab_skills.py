"""Source skills (chat vs email), the two scoring models, embedded memory, and the follow-up flag."""
import re
from pathlib import Path

import pytest

from app.config import settings
from app.lab import circle as circle_mod
from app.lab import followups, llm, rows, scoring
from app.lab.parse import parse_chat
from app.lab.parse_email import parse_mailbox
from app.lab.skills import Context, UnknownSource, skill_for
from app.lab.store import Lab

FIX = Path(__file__).parent / "fixtures" / "lab"
NOW = "2026-11-16T00:00:00+00:00"
CIRCLE = circle_mod.Circle(owner="Sam", profile_summary="Sam is a freelance video editor.", owner_emails=("sam@example.com",),
                           people={"ios_sample": {"name": "Lina", "relation": "colleague", "nicknames": ["Linaa"]}})


class FakeScorer:
    available = True

    def __init__(self):
        self.calls = []

    def score(self, texts):
        self.calls.append(list(texts))
        return [{"polarity": {}, "sentiment": -0.6 if "angry" in t else 0.4,
                 "emotions": {"anger": 0.8} if "angry" in t else {"joy": 0.5}} for t in texts]

    def info(self):
        return {"status": "ok", "sentiment_model": "fake-sentiment", "emotion_model": "fake-emotion"}


@pytest.fixture(autouse=True)
def fake_scorer():
    s = FakeScorer()
    scoring.set_scorer(s)
    yield s
    scoring.set_scorer(None)


@pytest.fixture
def mail(tmp_path, monkeypatch):
    lab = Lab(tmp_path, "lab-test")
    lab.ingest_messages("email", "inbox", parse_mailbox(FIX / "mail_sample.mbox"), NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [[1.0, 0.0] for _ in texts])
    return lab


@pytest.fixture
def chat(tmp_path, monkeypatch):
    lab = Lab(tmp_path, "lab-test")
    lab.ingest_messages("whatsapp", "ios_sample", parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "ios_sample").messages, NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [[1.0, 0.0] for _ in texts])
    return lab


def email_model(system, user, schema, **kw):
    if "privacy screen" in system:
        lines = re.findall(r"^(\d+)\. ", user, re.M)
        return {"items": [{"n": int(n), "category": "none"} for n in lines]}
    items = []
    for n, body in zip(*[iter(re.split(r"^ROW (\d+)$", user, flags=re.M)[1:])] * 2):
        item = {"row": int(n), "topics": ["misc"], "names": [], "category": "other", "user": "Owner received a mail.",
                "memory": "A mail arrived.", "entities": [], "action": {"needed": False, "what": "", "due": ""},
                "salience": [], "followups": [], "sensitive": False}
        if "CV and showreel" in body:
            item.update(category="job", topics=["job search"], names=["Rana Hadi", "Bizfy Labs"], memory="Bizfy Labs wants a CV and showreel.",
                        entities=[{"kind": "amount", "value": "AED 12,000"}, {"kind": "deadline", "value": "30 October 2026"},
                                  {"kind": "amount", "value": "AED 99,999"}],  # the last one is not in the mail
                        action={"needed": True, "what": "send CV and showreel", "due": "30 October 2026"})
        elif "A-77231" in body:
            item.update(category="shopping", topics=["order"], entities=[{"kind": "order_id", "value": "#A-77231"},
                        {"kind": "amount", "value": "AED 249.00"}], action={"needed": True, "what": "track parcel", "due": ""})
        elif "editing tools" in body:
            item.update(category="newsletter", topics=["video tools"])
        elif "tell me what you think" in body:
            item.update(category="personal", topics=["shared plan"], names=["Karim"], followups=["What is the plan about?"])
        elif "blood test" in body.lower():
            item.update(category="other", memory="Results are ready.")
        items.append(item)
    return {"items": items}


def test_registry_maps_every_source_to_a_skill():
    for source in ("whatsapp", "telegram", "messenger", "instagram", "imessage", "sms", "signal"):
        assert skill_for(source).name == "chat"
    for source in ("gmail", "imap", "outlook", "email"):
        assert skill_for(source).name == "email"
    with pytest.raises(UnknownSource):
        skill_for("fax")


def test_prompts_differ_by_source_and_never_ask_for_feelings():
    chat_ctx = Context(owner="Sam", circle=CIRCLE, source="ios_sample")
    chat_prompt, mail_prompt = skill_for("whatsapp").system(chat_ctx), skill_for("gmail").system(chat_ctx)
    assert "Lina" in chat_prompt and "colleague" in chat_prompt and "slices of a private chat" in chat_prompt
    assert "THREAD SLICE" in mail_prompt and "RECEIVED or SENT" in mail_prompt and "Lina" not in mail_prompt
    for skill in (skill_for("whatsapp"), skill_for("gmail")):
        props = skill.schema["properties"]["items"]["items"]["properties"]
        assert "sentiment" not in props and "emotions" not in props  # the two local classifiers do that


def test_email_parse_threads_bulk_attachments_and_quote_stripping():
    recs = parse_mailbox(FIX / "mail_sample.mbox")
    assert [r.idx for r in recs] == list(range(6)) and [r.ts for r in recs] == sorted(r.ts for r in recs)
    assert recs[0].meta["thread"] == recs[1].meta["thread"] != recs[2].meta["thread"]
    assert [r.meta["bulk"] for r in recs] == [False, False, True, True, False, False]
    assert recs[1].text == "Thanks Rana, I will send the CV and showreel this week."  # quote + signature removed
    assert recs[4].meta["attachments"] == ["plan.pdf (application/pdf)"] and recs[0].meta["from_addr"] == "rana@bizfylabs.example"


def test_email_units_group_threads_and_render_direction(mail):
    skill = skill_for("gmail")
    ctx = Context(owner="Sam", circle=CIRCLE, source="inbox", owner_emails=CIRCLE.owner_emails)
    units = skill.units(mail.load_messages("email", "inbox"), ctx)
    assert len(units) == 5 and sorted(len(u.records) for u in units) == [1, 1, 1, 1, 2]
    thread = next(u for u in units if len(u.records) == 2)
    text = skill.render(thread, ctx)
    assert "SUBJECT: Video editor role - next steps" in text and "RECEIVED from Rana Hadi" in text and "SENT from Sam" in text
    assert "BULK" in skill.render(next(u for u in units if u.records[0].meta["bulk"]), ctx)


def run_email(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", email_model)
    return rows.process(lab, "inbox", "Sam", CIRCLE, connector_id="email")


def test_email_rows_are_mail_shaped_and_code_checked(mail, monkeypatch, fake_scorer):
    stats = run_email(mail, monkeypatch)
    assert stats["skill"] == "email" and stats["rows_stored"] == 5
    by_subject = {r["extra"].get("subject") or "": r for r in mail.rows()}
    job = by_subject["Video editor role - next steps"]
    assert job["kind"] == "email" and job["extra"]["category"] == "job"
    values = {e["value"] for e in job["extra"]["entities"]}
    assert values == {"AED 12,000", "30 October 2026"} and stats["entities_unverified"] == 1  # invented AED 99,999 dropped
    e = job["extra"]["entities"][0]
    assert e["provenance"] == "inferred" and e["as_of"].startswith("2026-10-20") and e["source_idx"] == 0
    assert job["extra"]["action"] == {"needed": True, "what": "send CV and showreel", "due": "30 October 2026"}
    assert job["extra"]["direction"] == {"RECEIVED": 1, "SENT": 1}
    shop = by_subject["Your order #A-77231 has shipped"]
    assert shop["extra"]["bulk"] and shop["extra"]["action"]["needed"] is False  # bulk mail never asks the owner to act
    assert any("plan.pdf" in m for m in by_subject["check this"]["multimodal"])
    line = rows.format_row(job)
    assert "[job] Video editor role" in line and "amount=AED 12,000" in line and "TODO send CV and showreel by 30 October 2026" in line


def test_email_scoring_skips_promos_and_scores_personal_mail(mail, monkeypatch, fake_scorer):
    run_email(mail, monkeypatch)
    scored_text = " ".join(" ".join(c) for c in fake_scorer.calls)
    assert "A-77231" not in scored_text and "editing tools" not in scored_text  # receipts / newsletters carry no mood
    assert "CV and showreel" in scored_text
    by_subject = {r["extra"].get("subject"): r for r in mail.rows()}
    job = by_subject["Video editor role - next steps"]
    assert job["sentiment"] == 0.4 and job["emotions"] == {"joy": 0.5}  # owner = the SENT mail
    assert job["scores_other"]["sentiment"] == 0.4  # the RECEIVED mail is scored separately
    assert job["scorers"]["emotion_model"] == "fake-emotion"
    assert by_subject["Your order #A-77231 has shipped"]["sentiment"] is None


def test_email_sensitive_row_is_withheld_whole(mail, monkeypatch):
    run_email(mail, monkeypatch)
    clinic = next(r for r in mail.rows() if "Blood" in (r["extra"].get("subject") or "") or r["sensitive"])
    assert clinic["sensitive"] == 1 and clinic["memory"] == "" and clinic["extra"] == {} and clinic["multimodal"] == []
    assert clinic["sentiment"] is None and clinic["followup"] == 0


def test_followup_flag_and_deterministic_attachment_question(mail, monkeypatch):
    stats = run_email(mail, monkeypatch)
    karim = next(r for r in mail.rows() if r["extra"].get("subject") == "check this")
    open_q = [f["question"] for f in mail.followups("open") if f["row_id"] == karim["id"]]
    assert karim["followup"] == 1 and "What is the plan about?" in open_q and "What is in the attachment plan.pdf?" in open_q
    assert stats["followups_opened"] == 1 and stats["followups_attachment"] == 1
    shop = next(r for r in mail.rows() if r["extra"].get("subject", "").startswith("Your order"))
    assert shop["followup"] == 0


def test_memory_is_semantically_embedded_when_the_row_is_stored(mail, monkeypatch):
    stats = run_email(mail, monkeypatch)
    vectors = mail.vectors("window")
    stored = {r["id"]: r for r in mail.rows()}
    assert stats["memory_embedded"] == len(vectors) == sum(1 for r in stored.values() if not r["sensitive"])
    assert all(rid in stored for rid in vectors)


def test_memory_embedding_outage_is_reported_not_fatal(mail, monkeypatch):
    def down(texts, kind="document"):
        raise llm.LabLLMError("embedding model not loaded")

    monkeypatch.setattr(llm, "embed", down)
    stats = run_email(mail, monkeypatch)
    assert stats["rows_stored"] == 5 and stats["memory_embedding"].startswith("unavailable")
    assert mail.vectors("window") == {}


def test_chat_rows_use_the_two_classifiers_per_speaker(chat, monkeypatch, fake_scorer):
    def chat_model(system, user, schema, **kw):
        blocks = re.split(r"^ROW (\d+)$", user, flags=re.M)[1:]
        return {"items": [{"row": int(n), "topics": ["work"], "names": [], "user": "u", "memory": "m", "salience": [],
                           "followups": [], "sensitive": False} for n, _ in zip(blocks[0::2], blocks[1::2])]}

    monkeypatch.setattr(llm, "chat_json", chat_model)
    rows.process(chat, "ios_sample", "Sam", CIRCLE)
    sam_only = [t for c in fake_scorer.calls for t in c]
    assert any("freelance" in t for t in sam_only) and any("Orbit promo" in t for t in sam_only)
    r = chat.rows()[0]
    assert r["sentiment"] == 0.4 and r["emotions"] == {"joy": 0.5} and r["scores_other"] and r["scorers"]["sentiment_model"] == "fake-sentiment"
    assert "sentiment:0.4" in rows.format_row(r) and "other:" in rows.format_row(r)


def test_scorers_unavailable_leaves_null_scores_and_says_why(chat, monkeypatch):
    scoring.set_scorer(scoring.NullScorer("no torch in this interpreter"))
    monkeypatch.setattr(llm, "chat_json", lambda s, u, sc, **k: {"items": [
        {"row": int(n), "topics": [], "names": [], "user": "", "memory": "m", "salience": [], "followups": [], "sensitive": False}
        for n in re.findall(r"^ROW (\d+)$", u, re.M)]})
    stats = rows.process(chat, "ios_sample", "Sam", CIRCLE)
    r = chat.rows()[0]
    assert r["sentiment"] is None and r["emotions"] == {} and r["scorers"]["status"] == "unavailable"
    assert stats["rows_unscored"] == stats["rows_stored"] and stats["scorers"]["reason"] == "no torch in this interpreter"


def test_aggregate_means_sentiment_and_keeps_strongest_emotion():
    got = scoring.aggregate([{"sentiment": 0.5, "emotions": {"joy": 0.5}}, {"sentiment": -0.1, "emotions": {"joy": 0.9, "anger": 0.5}}, None])
    assert got == {"sentiment": 0.2, "emotions": {"anger": 0.5, "joy": 0.9}, "n": 2}
    assert scoring.aggregate([None, None]) is None and scoring.aggregate([]) is None


def test_followup_agent_uses_its_own_model_and_clears_the_flag(chat, monkeypatch):
    seen = []

    def model(system, user, schema, **kw):
        seen.append((("follow-up question" in system), kw.get("model")))
        if "follow-up question" in system:
            return {"status": "resolved", "answer": "It is due Friday.", "evidence": [1]}
        blocks = re.split(r"^ROW (\d+)$", user, flags=re.M)[1:]
        return {"items": [{"row": int(n), "topics": ["orbit promo"], "names": [], "user": "u", "memory": "Work on Orbit.",
                           "salience": [], "followups": ["When is it due?"], "sensitive": False} for n, _ in zip(blocks[0::2], blocks[1::2])]}

    monkeypatch.setattr(llm, "chat_json", model)
    rows.process(chat, "ios_sample", "Sam", CIRCLE)
    assert all(r["followup"] == 1 for r in chat.rows() if chat.followups("open"))
    monkeypatch.setattr(settings, "lab_followup_model", "stronger-model")
    followups.resolve(chat)
    assert ("follow-up question" in "follow-up question", "stronger-model") in [(True, m) for flag, m in seen if flag]
    assert all(m is None for flag, m in seen if not flag)  # the extractor keeps the default model
    resolved_rows = {f["row_id"] for f in chat.followups("resolved")}
    assert resolved_rows and all(
        r["followup"] == 0 for r in chat.rows() if r["id"] in resolved_rows and not [f for f in chat.followups("open") if f["row_id"] == r["id"]])


def test_days_option_keeps_only_the_most_recent_units(chat, monkeypatch):
    from app.lab import engine

    monkeypatch.setattr(llm, "chat_json", lambda s, u, sc, **k: {"items": [
        {"row": int(n), "topics": [], "names": [], "user": "", "memory": "m", "salience": [], "followups": [], "sensitive": False}
        for n in re.findall(r"^ROW (\d+)$", u, re.M)]})
    ctx = Context(owner="Sam", circle=CIRCLE, source="ios_sample")
    stats = engine.process(chat, "whatsapp", "ios_sample", ctx, days=10)  # fixture runs 3 Oct - 7 Nov
    assert 0 < stats["rows_stored"] < len(skill_for("whatsapp").units(chat.load_messages("whatsapp", "ios_sample"), ctx))
    assert min(r["t_end"] for r in chat.rows()) >= "2026-10-28"
