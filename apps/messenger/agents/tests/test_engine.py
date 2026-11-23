"""Intent engine policy: what may run early, what waits, what asks. Rule decider only (no network)."""
import pytest
import asyncio

from messenger_agents.catalog import BY_NAME
from messenger_agents.deciders import RuleDecider
from messenger_agents.engine import Conversation, IntentEngine, Policy


async def test_transcript_correction_during_request_discards_the_old_action(contacts):
    entered, release = asyncio.Event(), asyncio.Event()

    class DelayedDecider:
        async def decide(self, clause, utterance, people):
            entered.set()
            await release.wait()
            return await RuleDecider().decide(clause, utterance, people)

    engine = IntentEngine(DelayedDecider(), contacts)
    engine.partial("open my mail", 0)
    decision = asyncio.create_task(engine.tick(1))
    await asyncio.wait_for(entered.wait(), 1)
    engine.partial("open my mail actually calendar", 1.1)
    release.set()
    assert await decision == []
    assert engine.decisions[-1]["stale"] and not engine.events
    events = await engine.end(2)
    assert [e.args["screen"] for e in events if e.type == "act"] == ["calendar"]


async def speak(eng_or_conv, text: str, gap: float = 0.45):
    conv = eng_or_conv if isinstance(eng_or_conv, Conversation) else None
    eng = conv.begin() if conv else eng_or_conv
    words, out, t = text.split(), [], 0.0
    for i in range(len(words)):
        t += gap
        eng.partial(" ".join(words[: i + 1]), t)
        out += await (conv.tick(t + 0.2) if conv else eng.tick(t + 0.2))
    out += await (conv.finish(t + 0.6) if conv else eng.end(t + 0.6))
    return out, t


async def test_in_app_acts_before_end_of_speech(contacts):
    eng = IntentEngine(RuleDecider(), contacts)
    out, last_word = await speak(eng, "open my messages and text Mazen I'm on my way")
    act = next(e for e in out if e.type == "act")
    assert act.args["screen"] == "chats" and act.t < last_word  # ran while the person was still speaking


async def test_send_waits_for_end_of_speech_and_has_undo(contacts):
    eng = IntentEngine(RuleDecider(), contacts)
    out, last_word = await speak(eng, "text Mazen I'm running late")
    (send,) = [e for e in out if e.action == "send_message"]
    assert send.type == "undo" and send.t > last_word
    assert send.args == {"contactId": "mazen", "name": "Mazen", "text": "I'm running late"}


@pytest.mark.parametrize("text", ["generate an image of a falcon", "research the best supercars this week",
                                  "find flights from Dubai to London", "make a video of the sea"])
async def test_paid_actions_only_ever_ask_for_confirmation(contacts, text):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), text)
    paid = [e for e in out if e.action and BY_NAME[e.action].kind == "paid"]
    assert paid and all(e.type == "confirm" for e in paid)


@pytest.mark.parametrize("text,question", [
    ("text Sarah I'm outside", "Sarah Malik or Sara Ali?"),
    ("tell Hannah happy birthday", "Did you mean Hana?"),
    ("text Ahmed hi", "Ahmed isn't in your contacts. Who should get it?"),
    ("tell Arif Kahn I'm here", "Did you mean Arif Khan?"),
    ("send it", "Who should I send it to?"),
])
async def test_uncertain_recipient_asks_and_sends_nothing(contacts, text, question):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), text)
    assert [e.type for e in out] == ["ask"] and out[0].label == question


async def test_correction_withdraws_the_first_reading(contacts):
    # At an eager setting the first reading runs mid-sentence, and the correction withdraws it.
    out, _ = await speak(IntentEngine(RuleDecider(), contacts, Policy(stable_s=0.1)), "open mail, actually calendar")
    assert [(e.type, e.args.get("screen")) for e in out] == [("act", "mail"), ("cancel", None), ("act", "calendar")]
    assert out[1].ref == out[0].id


async def test_default_waits_long_enough_that_a_quick_correction_never_opens_the_wrong_screen(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "open mail, actually calendar")
    assert [(e.type, e.args.get("screen")) for e in out] == [("act", "calendar")]


async def test_correction_of_recipient_never_sends_to_the_first_name(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "text Lina, no, Mazen, that dinner is at 9")
    sends = [e for e in out if e.action == "send_message"]
    assert [s.args["contactId"] for s in sends] == ["mazen"] and sends[0].args["text"] == "Dinner is at 9"


async def test_never_mind_cancels_without_chat(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "tell Mazen I'll be late, actually never mind")
    assert not [e for e in out if e.type in ("undo", "chat")]


async def test_answer_resolves_the_question_in_the_next_utterance(contacts):
    conv = Conversation(RuleDecider(), contacts)
    first, _ = await speak(conv, "text Sarah I'm outside")
    assert first[0].type == "ask"
    second, _ = await speak(conv, "Sarah Malik")
    assert [(e.type, e.args.get("contactId"), e.args.get("text")) for e in second] == [("undo", "sarah", "I'm outside")]


async def test_no_answer_cancels(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "tell Hannah happy birthday")
    out, _ = await speak(conv, "no")
    assert [e.type for e in out] == ["cancel"]


async def test_small_talk_goes_to_chat(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "how are you today")
    assert [e.type for e in out] == ["chat"]

async def test_bare_reply_answers_the_chat_this_turn_opened(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "open the last chat and reply with I am on my way")
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("undo", "send_message")]
    assert out[1].args == {"contactId": "arif", "name": "Arif Khan", "text": "I am on my way"}


async def test_bare_reply_with_no_context_asks_instead_of_chatting(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "reply with I am on my way")
    assert [e.type for e in out] == ["ask"] and out[0].action == "send_message"


async def test_open_chat_opens_the_chats_screen(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "open chat")
    assert [(e.type, e.args.get("screen")) for e in out] == [("act", "chats")]


async def test_reply_inherits_the_opened_chat_in_the_next_turn(contacts):
    conv = Conversation(RuleDecider(), contacts)
    first, _ = await speak(conv, "open my last chat")
    assert first[0].action == "open_chat"
    second, _ = await speak(conv, "reply with I am on my way")
    assert [(e.type, e.action) for e in second] == [("undo", "send_message")]
    assert second[0].args["contactId"] == "arif"


async def test_open_act_holds_the_turn_while_the_reply_is_dictated(contacts):
    eng = IntentEngine(RuleDecider(), contacts)
    eng.partial("open the last chat and reply with", 0.0)
    out = await eng.tick(1.0)
    assert [e.awaiting for e in out if e.type == "act"] == ["reply"]


async def test_but_also_routes_message_plus_command(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts),
                         "reply to Arif that i am free this week and also plan the trip")
    assert [(e.type, e.action) for e in out] == [("undo", "send_message"), ("confirm", "plan_trip")]
    assert out[0].args["text"] == "I am free this week" and out[1].args["contactId"] == "arif"


async def test_but_also_keeps_dictation_whole(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "tell Arif i am free but also bring chips")
    assert [(e.type, e.action) for e in out] == [("undo", "send_message")]
    assert out[0].args["text"] == "I am free but also bring chips"

async def test_answer_with_last_chat_settles_the_recipient(contacts):
    conv = Conversation(RuleDecider(), contacts)
    first, _ = await speak(conv, "reply with hello")
    assert first[0].type == "ask"
    second, _ = await speak(conv, "my last chat")
    assert [(e.type, e.action) for e in second] == [("undo", "send_message")]
    assert second[0].args == {"contactId": "arif", "name": "Arif Khan", "text": "Hello"}


async def test_answer_with_a_bare_name_settles_the_recipient(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "reply with hello")
    second, _ = await speak(conv, "Arif")
    assert [(e.type, e.action) for e in second] == [("undo", "send_message")]
    assert second[0].args["contactId"] == "arif" and second[0].args["text"] == "Hello"


async def test_dictation_answers_what_should_i_say(contacts):
    conv = Conversation(RuleDecider(), contacts)
    first, _ = await speak(conv, "tell Arif")
    assert first[0].label == "What should I say to Arif Khan?"
    second, _ = await speak(conv, "I am on my way")
    assert [(e.type, e.action) for e in second] == [("undo", "send_message")]
    assert second[0].args == {"contactId": "arif", "name": "Arif Khan", "text": "I am on my way"}


async def test_full_command_as_answer_runs_as_a_new_command(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "reply with hello")
    second, _ = await speak(conv, "tell Mazen hi")
    assert [(e.type, e.action) for e in second] == [("undo", "send_message")]
    assert second[0].args["contactId"] == "mazen"


async def test_tell_him_after_opening_sends_to_the_last_chat(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "open my last message and tell him that i am free")
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("undo", "send_message")]
    assert out[1].args == {"contactId": "arif", "name": "Arif Khan", "text": "I am free"}

async def test_dangling_pronoun_defaults_to_the_last_interacted_chat(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "reply him I am on my way")
    assert [(e.type, e.action) for e in out] == [("undo", "send_message")]
    assert out[0].args == {"contactId": "arif", "name": "Arif Khan", "text": "I am on my way"}

async def test_question_answer_survives_a_reordered_contact_list(contacts):
    from messenger_agents.deciders import RuleDecider
    from messenger_agents.engine import Policy
    from messenger_agents.session import Conversations
    convs = Conversations(RuleDecider(), Policy())
    first = convs.get("s", contacts)
    first.begin().partial("Open.", 0.0)
    (ask,) = await first.finish(1.0)
    assert ask.type == "ask" and first.carry
    reordered = [contacts[1], contacts[0], *contacts[2:]]  # a message arrived between turns
    second = convs.get("s", reordered)
    assert second.carry  # the dangling verb survived the rebuild
    second.begin().partial("my last chat", 2.0)
    out = await second.finish(3.0)
    assert [(e.type, e.action) for e in out] == [("act", "open_chat")]

async def test_last_chat_answers_which_app_to_open(contacts):
    conv = Conversation(RuleDecider(), contacts)
    first, _ = await speak(conv, "open my last shot")  # STT mishearing of "chat": asks, never chats
    assert first[0].type == "ask" and first[0].action == "open_screen"
    second, _ = await speak(conv, "my last chat")
    assert [(e.type, e.action) for e in second] == [("act", "open_chat")]
    assert second[0].args["contactId"] == "arif"


async def test_live_trace_sentence_opens_sends_clean_text_and_asks_about_visit(contacts):
    said = "Open my last chat. and reply to him saying I will see you tomorrow. And plan for the visit in 2nd of January"
    conv = Conversation(RuleDecider(), contacts)
    out, _ = await speak(conv, said)
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("undo", "send_message"), ("ask", "plan_trip")]
    assert out[1].args == {"contactId": "arif", "name": "Arif Khan", "text": "I will see you tomorrow"}
    assert [c["text"] for c in conv.engine.plan["clauses"]] == [
        "Open my last chat", "reply to him saying I will see you tomorrow", "plan for the visit in 2nd of January"]
    answer, _ = await speak(conv, "yes")
    assert [(e.type, e.action) for e in answer] == [("confirm", "plan_trip")]
    assert "2nd of January" in answer[0].args["request"] and answer[0].args["contactId"] == "arif"


@pytest.mark.parametrize("body", ["Arif is coming too", "I will see you in January", "my last chat was with Arif"])
async def test_dictation_names_and_last_chat_never_override_the_recipient(contacts, body):
    study = next(c for c in contacts if c.id == "study")
    reordered = [study, *(c for c in contacts if c.id != "study")]
    out, _ = await speak(IntentEngine(RuleDecider(), reordered), f"open my last chat and reply to him saying {body}")
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("undo", "send_message")]
    assert out[1].args == {"contactId": "study", "name": "Study Group", "text": body[0].upper() + body[1:]}


async def test_unknown_explicit_reply_never_inherits_open_chat(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "open my last chat and reply to Ahmed saying Mazen is coming too")
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("ask", "send_message")]


@pytest.mark.parametrize("tail", ["reply to him", "reply to him saying", "reply to him that"])
async def test_unfinished_reply_asks_for_dictation_then_sends_answer(contacts, tail):
    conv = Conversation(RuleDecider(), contacts)
    out, _ = await speak(conv, f"open my last chat and {tail}")
    assert [(e.type, e.action) for e in out] == [("act", "open_chat"), ("ask", "send_message")]
    answer, _ = await speak(conv, "Mazen is coming in January")
    assert [(e.type, e.action) for e in answer] == [("undo", "send_message")]
    assert answer[0].args == {"contactId": "arif", "name": "Arif Khan", "text": "Mazen is coming in January"}


async def test_plain_and_imperative_is_preserved_in_sent_message(contacts):
    out, _ = await speak(IntentEngine(RuleDecider(), contacts), "tell Arif I will go and bring chips")
    assert [(e.type, e.action) for e in out] == [("undo", "send_message")]
    assert out[0].args["text"] == "I will go and bring chips"


async def test_plan_clarification_does_not_fall_to_chat_or_run_paid_work(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "plan the visit on 2 January")
    out, _ = await speak(conv, "an appointment")
    assert [(e.type, e.action) for e in out] == [("ask", "open_screen")]
    out, _ = await speak(conv, "yes")
    assert [(e.type, e.args.get("screen")) for e in out] == [("act", "calendar")]


async def test_declining_plan_only_cancels_the_plan(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "tell Arif hello and plan the visit")
    out, _ = await speak(conv, "no")
    assert [e.type for e in out] == ["cancel"] and not out[0].args.get("all")


async def test_plan_question_accepts_a_fresh_command(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "plan the visit")
    out, _ = await speak(conv, "open mail")
    assert [(e.type, e.args.get("screen")) for e in out] == [("act", "mail")]


async def test_confirmed_misspelled_surname_is_not_sent_as_message_text(contacts):
    conv = Conversation(RuleDecider(), contacts)
    await speak(conv, "tell Arif Kahn I'm here")
    out, _ = await speak(conv, "yes")
    assert [(e.type, e.action) for e in out] == [("undo", "send_message")]
    assert out[0].args["text"] == "I'm here"


def test_eval_rejects_leaked_prefixes_and_missing_or_reordered_message_words():
    from eval.run_eval import arg_ok
    assert arg_ok("text", "Hello, I'm coming.", "hello I'm coming")
    assert not arg_ok("text", "To him saying I will see you tomorrow", "I will see you tomorrow")
    assert not arg_ok("text", "I will go", "I will go and bring chips")
    assert not arg_ok("text", "Tomorrow I will see you", "I will see you tomorrow")
