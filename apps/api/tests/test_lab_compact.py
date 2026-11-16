"""The compact chat design: rows follow day / session / pause (max 50 messages), memory at most half the source."""
import re
from datetime import datetime, timedelta

import pytest

from app.lab import circle as circle_mod
from app.lab import llm, rows, scoring
from app.lab.parse import parse_chat
from app.lab.skills import Context, chat, skill_for
from app.lab.store import Lab

NOW = "2026-11-16T00:00:00+00:00"
CIRCLE = circle_mod.Circle(owner="Sam", people={"c": {"name": "Lina", "relation": "colleague", "nicknames": ["Linaa"]}})


def burst(start: str, n: int, step_min: float = 1.0, tag: str = "m") -> list[str]:
    """n chat lines from `start` (YYYY-MM-DD HH:MM), one every step_min minutes."""
    t0 = datetime.strptime(start, "%Y-%m-%d %H:%M")
    return [f"[{(t0 + timedelta(minutes=i * step_min)).strftime('%d/%m/%Y, %H:%M:%S')}] {'Sam' if i % 2 else 'Lina'}: {tag} {i} about the Orbit promo"
            for i in range(n)]


def sizes(lines: list[str]) -> list[int]:
    return [sum(m.kind == "message" for m in s) for s in chat.segment(parse_chat("\n".join(lines), "x").messages)]


class NoScorer:
    available = False

    def score(self, texts):
        return [None] * len(texts)

    def info(self):
        return {"status": "unavailable", "reason": "test"}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    scoring.set_scorer(NoScorer())
    lab = Lab(tmp_path, "lab-test")
    lines = burst("2026-01-01 10:00", 30) + burst("2026-01-01 16:00", 12, tag="later")
    lab.ingest_messages("whatsapp", "c", parse_chat("\n".join(lines), "c").messages, NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [[1.0, 0.0] for _ in texts])
    yield lab
    scoring.set_scorer(None)


def test_defaults():
    assert (chat.ROW_MIN, chat.ROW_MAX, chat.SESSION_GAP_MIN) == (10, 50, 90) and chat.VARIANT == "compact"


def test_a_pause_over_the_session_gap_ends_a_row_but_a_short_one_does_not():
    assert sizes(burst("2026-01-01 10:00", 30) + burst("2026-01-01 16:00", 12)) == [30, 12]  # 5h pause -> two sessions
    assert sizes(burst("2026-01-01 10:00", 30) + burst("2026-01-01 11:20", 12)) == [42]  # 51 min pause -> one session


def test_a_new_day_always_starts_a_new_row():
    assert sizes(burst("2026-01-01 23:00", 12, 2) + burst("2026-01-02 00:10", 12, 2)) == [12, 12]


def test_tiny_sessions_merge_with_a_neighbour_of_the_same_day_only():
    assert sizes(burst("2026-01-01 09:00", 6) + burst("2026-01-01 13:00", 6)) == [12]  # same day, both tiny
    assert sizes(burst("2026-01-01 09:00", 6) + burst("2026-01-02 09:00", 6)) == [6, 6]  # different days never merge
    assert sizes(burst("2026-01-01 09:00", 8) + burst("2026-01-01 14:00", 47)) == [8, 47]  # merging would break the cap


def test_a_long_session_is_split_in_balanced_pieces_at_its_longest_pause():
    assert sizes(burst("2026-01-01 08:00", 120)) == [40, 40, 40]  # not 50, 50, 20
    lines = burst("2026-01-01 08:00", 45) + burst("2026-01-01 09:20", 40)  # one session with a 36 min pause after message 45
    assert sizes(lines) == [45, 40]


def test_every_message_lands_in_exactly_one_row_in_order():
    lines = burst("2026-01-01 08:00", 70) + burst("2026-01-01 15:00", 9) + burst("2026-01-02 09:00", 130, 3)
    msgs = parse_chat("\n".join(lines), "x").messages
    segs = chat.segment(msgs)
    assert [m.idx for s in segs for m in s] == [m.idx for m in msgs]
    assert all(sum(m.kind == "message" for m in s) <= 50 for s in segs)








def test_each_row_cites_only_its_own_messages(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda s, u, sc, **k: {"items": [
        {"row": int(n), "topics": ["x"], "names": [], "user": "u", "memory": "m", "followups": [], "sensitive": False}
        for n in re.findall(r"^ROW (\d+)$", u, re.M)]})
    rows.process(lab, "c", "Sam", CIRCLE)
    spans = sorted((r["first_idx"], r["last_idx"], r["n_msgs"]) for r in lab.rows())
    assert [n for _, _, n in spans] == [30, 12] and spans[0][1] < spans[1][0]


def test_compact_row_is_one_narrative_not_two_fields(lab, monkeypatch):
    props = chat.CHAT.schema["properties"]["items"]["items"]["properties"]
    assert "memory" in props and "user" not in props and "salience" not in props  # one narrative per row
    ctx = Context(owner="Sam", circle=CIRCLE, source="c")
    rendered = chat.render(skill_for("whatsapp").units(lab.load_messages("whatsapp", "c"), ctx)[0], ctx)
    assert "LIMIT" not in rendered.upper() and rendered.splitlines()[0].startswith("#")  # the model gets the chat lines, nothing precomputed
    monkeypatch.setattr(llm, "chat_json", lambda s, u, sc, **k: {"items": [
        {"row": int(n), "topics": ["orbit"], "names": [], "memory": "Sam asked; Lina answered.", "followups": [], "sensitive": False}
        for n in re.findall(r"^ROW (\d+)$", u, re.M)]})
    rows.process(lab, "c", "Sam", CIRCLE)
    r = lab.rows()[0]
    assert r["user_text"] == "" and r["memory"] == "Sam asked; Lina answered."
    assert rows.format_row(r).count(" | ") == len(rows.format_row(r).split(" | ")) - 1 and "Sam asked; Lina answered." in rows.format_row(r)
