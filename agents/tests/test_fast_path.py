"""The fast path: unambiguous in-app commands are decided by rules without a model call; names always reach the model."""
import pytest

from mirsal_agents.deciders import NOBODY, NO_SCREEN, Decision, FastPathDecider, RuleDecider
from mirsal_agents.engine import IntentEngine


class CountingModel:
    """Stands in for the Decisions API: records calls, answers like the rules but labelled "model"."""
    def __init__(self):
        self.calls = []

    async def decide(self, clause, utterance, contacts):
        self.calls.append(clause)
        d = await RuleDecider().decide(clause, utterance, contacts)
        d.source = "model"
        return d


class UnsureModel:
    """The live model on a reply clause it hesitates on (trace: send 0.52): records calls, never sure."""
    def __init__(self):
        self.calls = []

    async def decide(self, clause, utterance, contacts):
        self.calls.append(clause)
        return Decision({"send_message": 0.52, "open_screen": 0.30, "none": 0.18},
                        {NOBODY: 1.0}, {NO_SCREEN: 1.0}, "model")


@pytest.mark.parametrize("said,action", [("check my notifications", "check_notifications"), ("what's new", "check_notifications"),
                                         ("read my messages", "read_messages"), ("open my mail", "open_screen"),
                                         ("show my calendar", "open_screen")])
async def test_clear_in_app_commands_skip_the_model(contacts, said, action):
    model = CountingModel()
    d = await FastPathDecider(model).decide(said, said, contacts)
    assert d.source == "fast" and Decision.top(d.action)[0] == action and model.calls == []


@pytest.mark.parametrize("said", ["read Mazen's messages", "what did Omar say", "text Mazen I'm late", "open my chat with Lina",
                                  "plan a trip to Egypt", "research electric cars", "send them the photos",
                                  "check notifications and then tell Sara I'm on my way please now"])
async def test_names_paid_actions_and_long_clauses_go_to_the_model(contacts, said):
    model = CountingModel()
    d = await FastPathDecider(model).decide(said, said, contacts)
    assert d.source == "model" and model.calls == [said]


async def test_engine_acts_on_fast_decisions_and_reads_a_named_person_only_by_exact_name(contacts):
    eng = IntentEngine(FastPathDecider(CountingModel()), contacts)
    eng.partial("check my notifications", 0.0)
    acts = [e for e in await eng.end(1.0) if e.type == "act"]
    assert acts[0].action == "check_notifications" and acts[0].source == "fast"

    eng = IntentEngine(RuleDecider(), contacts)
    eng.partial("read Mazen's messages", 0.0)
    act = next(e for e in await eng.end(1.0) if e.type == "act")
    assert act.action == "read_messages" and act.args == {"contactId": "mazen", "name": "Mazen"}

    eng = IntentEngine(RuleDecider(), contacts)
    eng.partial("plan a trip to Egypt on 2 January with Arif Khan", 0.0)
    plan = next(e for e in await eng.end(1.0) if e.type in ("confirm", "act"))
    assert plan.type == "confirm" and plan.args["contactId"] == "arif" and "2 January" in plan.args["request"]


async def test_a_dangling_verb_asks_and_completes_with_the_next_turn(contacts):
    from mirsal_agents.engine import Conversation
    conv = Conversation(RuleDecider(), contacts)
    conv.begin().partial("Open.", 0.0)
    (ask,) = await conv.finish(1.0)
    assert ask.type == "ask" and ask.label == "Open what?"                     # not sent to the chat model
    conv.begin().partial("my last chat", 2.0)
    acts = [e for e in await conv.finish(3.0) if e.type == "act"]
    assert acts[0].action == "open_chat" and acts[0].args["contactId"] == contacts[0].id


async def test_a_full_command_is_not_held(contacts):
    from mirsal_agents.engine import Conversation
    conv = Conversation(RuleDecider(), contacts)
    conv.begin().partial("open my mail", 0.0)
    assert [e.action for e in await conv.finish(1.0) if e.type == "act"] == ["open_screen"] and conv.carry == ""


async def test_rules_backstop_rescues_an_unsure_model(contacts):
    model = UnsureModel()
    d = await FastPathDecider(model).decide("tell him I am coming now, tomorrow or someday",
                                           "open my last message and tell him I am coming now, tomorrow or someday",
                                           contacts)
    assert Decision.top(d.action)[0] == "send_message" and d.source == "rules" and len(model.calls) == 1


async def test_both_unsure_stays_with_the_model(contacts):
    model = UnsureModel()
    d = await FastPathDecider(model).decide("open the thing from yesterday", "open the thing from yesterday", contacts)
    assert d.source == "model" and Decision.top(d.action)[0] == "send_message"  # model unsure, rules unsure


async def test_backstop_drives_the_trace_two_shape_end_to_end(contacts):
    eng = IntentEngine(FastPathDecider(UnsureModel()), contacts)
    eng.partial("open my last message and tell him I am coming now", 0.0)
    out = await eng.end(2.0)
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("undo", "send_message")]
    assert out[1].args["contactId"] == "arif" and out[1].args["text"] == "I am coming now"
