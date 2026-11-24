"""A voice transcript stays a draft until the person confirms the send."""

from app.messenger.store import ChatStore


def test_messenger_voice_does_not_send_unconfirmed(tmp_path):
    store = ChatStore(tmp_path / "chat.sqlite3")
    conv = store.create_conversation("usr_rana", ["usr_layla"], kind="direct")
    draft = store.stage_voice(conv, "usr_rana", "Send the Friday note")
    held = store.confirm_voice(conv, "usr_rana", draft, confirmed=False, client_msg_id="voice-1")
    assert held is None
    assert store.count_messages(conv) == 0
    sent = store.confirm_voice(conv, "usr_rana", draft, confirmed=True, client_msg_id="voice-1")
    assert sent["body"] == "Send the Friday note"
    assert store.count_messages(conv) == 1
