import pytest

from mirsal_agents.contacts import mentions, resolve, similar
from mirsal_agents.text import apply_correction, message_text, split_clauses


def test_similar_names():
    assert similar("Sarah", "sara") and similar("Omer", "omar") and similar("Mazin", "mazen") and similar("Amr", "omar")
    assert not similar("Mazen", "Hana") and not similar("Sara", "sara")


def test_full_name_wins_over_first_name(contacts):
    (_, c, _), = mentions("tell Sarah Malik hi", contacts)
    assert c.id == "sarah"


def test_full_multiword_name_with_namesake_is_accepted(contacts):
    assert resolve("text Sara Ali hi", contacts).contact.id == "sara"
    assert resolve("text Sara hi", contacts).status == "ask"
    assert resolve("text Omar hi", contacts).status == "ask"  # "Omar" may be the transcriber's "Omer"


def test_model_disagreement_asks(contacts):
    assert resolve("text Mazen hi", contacts, model_pick="arif", model_p=0.9).status == "ask"


def test_clause_split_keeps_message_bodies_whole():
    assert split_clauses("tell Mazen I need bread and milk") == ["tell Mazen I need bread and milk"]
    assert split_clauses("open mail and then text Hana hi") == ["open mail", "text Hana hi"]


def test_router_splits_also_only_for_preset_commands():
    assert split_clauses("reply to Arif that i am free this week and also plan the trip") == [
        "reply to Arif that i am free this week", "plan the trip"]
    assert split_clauses("tell Arif i am free but also bring chips") == ["tell Arif i am free but also bring chips"]
    assert split_clauses("text Omar good luck and also research the best e-bikes") == [
        "text Omar good luck", "research the best e-bikes"]
    assert split_clauses("open the last chat and also reply with hello") == [
        "open the last chat", "reply with hello"]


def test_past_tense_heads_split_and_extract():
    assert split_clauses("Opened the last message and replied yes I am coming") == [
        "Opened the last message", "replied yes I am coming"]
    assert message_text("replied yes I am coming", "Arif Khan") == "yes I am coming"
    assert message_text("told Omar I will be late", "Omar") == "I will be late"


def test_and_plan_splits_and_periods_split():
    assert split_clauses("reply to him saying I will see you tomorrow. And plan for the visit") == [
        "reply to him saying I will see you tomorrow", "plan for the visit"]
    assert split_clauses("open mail. text Mazen hi") == ["open mail", "text Mazen hi"]
    assert split_clauses("tell Mazen I need bread and milk") == ["tell Mazen I need bread and milk"]


def test_message_text_forms():
    assert message_text("send Mazen a message saying good luck today", "Mazen") == "good luck today"
    assert message_text("let the Gaming Squad know I can't play", "Gaming Squad") == "I can't play"
    assert message_text("ask Mazen if he's free on Friday", "Mazen") == "Are you free on Friday?"
    assert message_text("send see you soon to Arif", "Arif") == "see you soon"
    assert message_text("reply with I am on my way", "Arif Khan") == "I am on my way"
    assert message_text("reply saying hello", "Arif Khan") == "hello"
    assert message_text("reply yes", "Arif Khan") == "yes"
    assert message_text("reply", "Arif Khan") == "" and message_text("reply with", "Arif Khan") == ""


def test_corrections():
    assert apply_correction("research electric cars, I mean electric motorbikes", set()).text == "research electric motorbikes"
    assert apply_correction("what's the weather in Dubai, no wait, in Sharjah", set()).text == "what's the weather in Sharjah"


@pytest.mark.parametrize("said", ["reply to him", "reply to him saying", "reply to him that", "reply to her with"])
def test_unfinished_pronoun_reply_has_no_message(said):
    assert message_text(said, "Arif Khan") == ""


@pytest.mark.parametrize("said", [
    "reply to him saying I will see you in January",
    "reply to him saying Arif is coming too",
])
def test_reply_prefix_is_never_dictation(said):
    assert message_text(said, "Study Group") == said.split("saying ", 1)[1]


@pytest.mark.parametrize("body", ["I will go and bring chips", "Bring chips. Bring drinks too", "Get milk and make sandwiches"])
def test_ordinary_imperatives_stay_in_dictation(body):
    said = f"tell Arif {body}"
    assert split_clauses(said) == [said]


def test_read_and_app_opening_heads_split():
    assert split_clauses("open mail and read my messages") == ["open mail", "read my messages"]
    assert split_clauses("tell Arif hello and bring up mail") == ["tell Arif hello", "bring up mail"]
    assert split_clauses("open mail. And also read my messages") == ["open mail", "read my messages"]


def test_recipient_guard_ignores_names_in_the_dictation(contacts):
    match = resolve("reply to him saying Arif is coming too", contacts)
    assert match.status == "ask" and not match.candidates and not match.phrase
    assert resolve("text Ahmed saying Mazen is coming too", contacts).status == "ask"
