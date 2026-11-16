from pathlib import Path

from app.lab.parse import parse_chat

FIX = Path(__file__).parent / "fixtures" / "lab"


def load(name):
    return parse_chat((FIX / name).read_text(encoding="utf-8"), Path(name).stem)


def test_ios_counts_dates_multiline_media_system():
    p = load("chat_ios_sample.txt")
    s = p.stats()
    assert s["messages"] == 25 and s["media"] == 1 and s["system_lines"] == 1
    assert s["first"] == "2026-10-03T09:12:04" and s["last"] == "2026-11-07T12:01:00"
    assert s["date_order"] == "dmy" and s["unparsed_lines"] == 0
    draft = next(m for m in p.messages if m.text.startswith("Lina here is the draft"))
    assert draft.text.splitlines()[-1] == "and the audio is mixed"  # continuation lines joined
    assert [m.idx for m in p.messages] == list(range(len(p.messages)))  # stable ids


def test_android_and_copy_paste_formats():
    a = load("chat_android_sample.txt")
    assert a.stats()["messages"] == 3 and a.system_lines == 1 and a.stats()["media"] == 1
    assert a.messages[1].text == "yes after 5 pm\nand not before"
    p = load("chat_paste_sample.txt")
    assert p.date_order == "mdy"  # 11/20/2026 proves month-first
    assert [m.ts for m in p.messages] == ["2026-11-09T11:27:00", "2026-11-09T11:28:00", "2026-11-20T13:05:00"]


def test_garbage_is_counted_not_crashing():
    p = parse_chat("hello there\nnot a chat\n", "junk")
    assert p.messages == [] and p.unparsed_lines == 2


def test_narrow_nbsp_before_pm_still_parses():
    raw = "[15/04/2024, 4:00:30 PM] A: hi\n[15/04/2024, 4:01:00 PM] B: yo\n"
    p = parse_chat(raw, "x")
    assert [m.ts for m in p.messages] == ["2024-04-15T16:00:30", "2024-04-15T16:01:00"]
