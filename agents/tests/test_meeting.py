import pytest
from datetime import date

from mirsal_agents.deciders import RuleDecider
from mirsal_agents.engine import Conversation
from mirsal_agents.meeting import meeting_args
from mirsal_agents.session import Conversations
from mirsal_agents.engine import Policy
from mirsal_agents.text import split_clauses


STREAM = ("reply to him that i will be late tonight but we can meet tomorrow in on the wood restaurant plan for it "
          "and send to sara hey do you wanna meet tomorrow in on the wood restaurant "
          "then make a plan for this event between us")
FIRST = "I will be late tonight but we can meet tomorrow in on the wood restaurant"
SECOND = "Hey do you wanna meet tomorrow in on the wood restaurant"


@pytest.mark.parametrize("streaming", [False, True])
async def test_full_case_recovers_without_early_decisions_and_resumes_sara_dependencies(contacts, streaming):
    sessions = Conversations(RuleDecider(), Policy())
    conv = sessions.get("long", contacts)
    engine = conv.begin()
    early = []
    if streaming:
        for i in range(1, len(STREAM.split()) + 1):
            engine.partial(" ".join(STREAM.split()[:i]), i * .5)
            early += await conv.tick(i * .5 + .4)
    else:
        engine.partial(STREAM, 0)
    assert not any(e.type in ("undo", "confirm") or e.action == "plan_meeting" for e in early)
    result = await conv.finish(40)
    assert [(e.type, e.action) for e in result] == [("undo", "send_message"), ("act", "plan_meeting"), ("ask", "send_message")]
    assert result[0].args["text"] == FIRST and result[0].args["contactId"] == "arif"
    assert result[1].args["context"] == FIRST and result[1].args["name"] == "Arif Khan"
    assert result[1].args["location"] == "on the wood restaurant" and result[1].args["startTime"] == ""
    assert "Sara Ali or Sarah Malik" in result[2].label
    assert conv.pending.rest == ["make a plan for this event between us"]
    # Opening/sending can reorder the browser's contact list before the spoken answer.
    conv = sessions.get("long", list(reversed(contacts)))
    conv.begin().partial("Sara Ali", 0)
    resumed = await conv.finish(1)
    assert [(e.type, e.action) for e in resumed] == [("undo", "send_message"), ("act", "plan_meeting")]
    assert resumed[0].args["text"] == SECOND and resumed[0].args["contactId"] == "sara"
    assert resumed[1].args["context"] == SECOND and resumed[1].args["contactId"] == "sara"
    assert not await conv.finish(2)  # repeated final pass cannot send or plan twice


@pytest.mark.parametrize("body", ["we can plan for it", "we should plan for it", 'say "plan for it"', "do not plan for it"])
def test_ordinary_or_quoted_planning_words_stay_dictation(body):
    text = f"reply to him that we can meet tomorrow at the restaurant and {body}"
    # "and we …" and quoted content are not imperative command heads.
    assert split_clauses(text) == [text]


def test_meeting_draft_keeps_missing_fields_and_resolves_relative_date():
    args = meeting_args("plan for it", FIRST, "arif", "Arif Khan", date(2026, 10, 8))
    assert args["date"] == "2026-10-09" and args["startTime"] == args["endTime"] == ""
    assert args["location"] == "on the wood restaurant"
    blank = meeting_args("plan a meeting", today=date(2026, 10, 8))
    assert blank["date"] == blank["location"] == blank["name"] == ""
    explicit = meeting_args("plan a meeting on 2026-11-05 at 7 pm", FIRST, today=date(2026, 10, 8))
    assert explicit["date"] == "2026-11-05" and explicit["startTime"] == "19:00"


async def test_meeting_for_another_person_does_not_inherit_previous_message(contacts):
    conv = Conversation(RuleDecider(), contacts)
    conv.begin().partial("reply to him that meet tomorrow at the restaurant", 0)
    await conv.finish(1)
    conv.begin().partial("plan a meeting with Mazen", 0)
    events = await conv.finish(1)
    assert events[0].args["name"] == "Mazen" and events[0].args["context"] == ""
    assert events[0].args["date"] == events[0].args["location"] == ""
