"""Semantic chunking: cut only at max size, placed by meaning; days and pauses are not boundaries by themselves."""
from datetime import datetime, timedelta

from app.lab import chunking
from app.lab.chunking import boundary_scores, message_tokens, render, split, tags_for
from app.lab.parse import Message

VOCAB = {
    "phone": "phone samsung battery screen charger iphone cover data apps contacts".split(),
    "car": "car engine garage wheel parking driver petrol brake mechanic seat".split(),
    "trip": "flight hotel ticket airport luggage visa booking suitcase passport taxi".split(),
    "food": "bread soup rice eggs falafel breakfast dinner lunch cheese tea".split(),
}


def conv(start: str, n: int, topic: str, step_min: float = 5.0, first_idx: int = 0, gap_before_min: float | None = None) -> list[Message]:
    """n messages about one topic. Words rotate through the topic vocabulary, so any window shares vocabulary."""
    t = datetime.fromisoformat(start)
    if gap_before_min is not None:
        t += timedelta(minutes=gap_before_min)
    words = VOCAB[topic]
    out = []
    for i in range(n):
        text = " ".join(words[(i * 3 + k) % len(words)] for k in range(4))
        out.append(Message(idx=first_idx + i, ts=(t + timedelta(minutes=i * step_min)).isoformat(timespec="seconds"),
                           sender="Sam" if i % 2 else "Lina", text=text))
    return out


def thread(*parts: tuple[str, int, dict]) -> list[Message]:
    msgs: list[Message] = []
    for topic, n, kw in parts:
        start = (datetime.fromisoformat(msgs[-1].ts) + timedelta(minutes=kw.pop("step", 5))).isoformat() if msgs else kw.pop("start")
        msgs += conv(start, n, topic, first_idx=len(msgs), **kw)
    return msgs


def cut_positions(chunks) -> list[int]:
    return [c.messages[0].idx for c in chunks[1:]]


SMALL = dict(min_tokens=500, max_tokens=1000, overlap=8)


def test_a_thread_that_fits_is_one_chunk():
    msgs = conv("2026-01-01T10:00:00", 30, "phone")
    chunks = split(msgs, min_tokens=500, max_tokens=5000)
    assert len(chunks) == 1 and chunks[0].reason == "full" and chunks[0].messages == msgs and chunks[0].context == []


def test_midnight_is_not_a_boundary_the_topic_change_is():
    # 35 messages about phones, then cars until well past midnight: the cut must be the topic change, not the date change
    msgs = thread(("phone", 35, {"start": "2026-01-01T20:00:00"}), ("car", 40, {}))
    midnight = next(i for i, m in enumerate(msgs) if m.ts.startswith("2026-01-02"))
    chunks = split(msgs, **SMALL)
    assert chunks[0].messages[-1].idx + 1 == 35 and 35 != midnight
    assert midnight in range(*[chunks[0].messages[0].idx, len(msgs)])  # the date change was inside the allowed zone


def test_a_long_pause_inside_one_conversation_is_not_a_cut():
    # the user leaves for 6 hours and comes back to the same topic; the real topic change comes later with no pause
    msgs = thread(("phone", 30, {"start": "2026-01-01T09:00:00"}), ("phone", 12, {"step": 360}), ("car", 30, {}))
    pause_at = 30
    chunks = split(msgs, **SMALL)
    assert chunks[0].messages[-1].idx + 1 == 42 != pause_at


def test_a_pause_strengthens_a_real_topic_change():
    # two equally sharp topic changes; the one that comes after a long silence wins
    msgs = thread(("phone", 30, {"start": "2026-01-01T09:00:00"}), ("car", 12, {}), ("trip", 30, {"step": 300}))
    chunks = split(msgs, **SMALL)
    assert chunks[0].messages[-1].idx + 1 == 42


def test_scores_are_lexical_and_use_idf_so_filler_carries_no_weight():
    filler = [Message(idx=i, ts=f"2026-01-01T10:{i:02d}:00", sender="A", text="ايه ده يا ايه ده") for i in range(30)]
    scores = boundary_scores(filler)
    assert all(s == 0.5 * 0.6 or s <= 0.7 for s in scores)  # nothing distinctive -> no strong boundary anywhere
    mixed = conv("2026-01-01T10:00:00", 20, "phone") + conv("2026-01-01T11:40:00", 20, "car", first_idx=20)
    s = boundary_scores(mixed)
    assert max(range(1, 40), key=lambda i: s[i]) == 20  # the topic change is the global best cut


def test_every_message_is_in_exactly_one_chunk_in_order_with_sized_chunks():
    msgs = thread(("phone", 60, {"start": "2026-01-01T08:00:00"}), ("car", 60, {}), ("trip", 60, {}), ("food", 60, {}))
    chunks = split(msgs, **SMALL)
    assert [m.idx for c in chunks for m in c.messages] == [m.idx for m in msgs]
    assert len(chunks) > 2
    for c in chunks[:-1]:
        assert 500 <= c.tokens <= 1000 and c.reason == "cut"
    assert chunks[-1].reason == "end"


def test_overlap_context_is_the_tail_of_the_previous_chunk():
    msgs = thread(("phone", 60, {"start": "2026-01-01T08:00:00"}), ("car", 60, {}), ("trip", 60, {}))
    chunks = split(msgs, **SMALL)
    assert chunks[0].context == []
    for prev, cur in zip(chunks, chunks[1:]):
        assert cur.context == prev.messages[-8:]
        assert cur.context[-1].idx + 1 == cur.messages[0].idx


def test_the_last_chunk_is_never_tiny():
    for extra in range(1, 25):
        msgs = conv("2026-01-01T08:00:00", 50 + extra, "phone")  # total just above one max chunk
        chunks = split(msgs, **SMALL)
        assert len(chunks) == 1 or chunks[-1].tokens >= int(500 * chunking.TAIL_FRACTION), (extra, [c.tokens for c in chunks])


def test_render_uses_local_ids_a_date_separator_and_marks_context():
    msgs = thread(("phone", 40, {"start": "2026-01-01T22:30:00"}), ("car", 40, {}))
    msgs[3] = Message(idx=3, ts=msgs[3].ts, sender="Lina", text="", kind="media")
    chunks = split(msgs, **SMALL)
    tags = tags_for(msgs, "Sam")
    assert tags == {"Lina": "P", "Sam": "U"}
    text, id_map = render(chunks[0], tags)
    lines = text.splitlines()
    assert lines[0] == "--- 2026-01-01 ---" and lines[1].startswith("1 22:30 P: ")
    assert "4 " in text and "[image omitted]" in text
    assert any(line.startswith("--- 2026-01-02 ---") for line in lines)  # the date is a display separator only
    assert list(id_map) == list(range(1, len(chunks[0].messages) + 1)) and id_map[1] == chunks[0].first_idx
    text2, _ = render(chunks[1], tags)
    assert text2.startswith("CONTEXT (already processed") and "\nCHAT:\n" in text2


def test_split_is_deterministic_and_accepts_another_scorer():
    msgs = thread(("phone", 60, {"start": "2026-01-01T08:00:00"}), ("car", 60, {}), ("trip", 60, {}))
    assert [c.last_idx for c in split(msgs, **SMALL)] == [c.last_idx for c in split(msgs, **SMALL)]
    forced = split(msgs, scorer=lambda m: [1.0 if i == 40 else 0.0 for i in range(len(m))], **SMALL)
    assert forced[0].last_idx == 39  # a custom (e.g. embedding) scorer decides the cut


def test_token_cost_uses_the_measured_ratio():
    m = Message(idx=0, ts="2026-01-01T10:00:00", sender="A", text="x" * 100)
    assert message_tokens(m) == int((100 + chunking.LINE_OVERHEAD_CHARS) / chunking.CHARS_PER_TOKEN) + 1
    assert chunking.CHARS_PER_TOKEN == 1.9
