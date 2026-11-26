"""
tests.test_guitar_thread
==========================

The guitar conversation check's fixes (2026-11-26): "I practiced for 30 minutes today" is a session on his course
(it had only been noted), "what should I work on next?" after her course reply is its next step (never a project).
"""

from types import SimpleNamespace

from core import assistant_turn, her_asks, paths


def test_practice_goes_to_his_course(monkeypatch):
    guitar = SimpleNamespace(id="guitar", name="Guitar")
    book = SimpleNamespace(started=lambda: ["guitar"], path=lambda pid: object())
    monkeypatch.setattr(paths, "program_of", lambda c, p: guitar if p == "guitar" else None)
    monkeypatch.setattr(paths, "find_program", lambda c, w: guitar if "guitar" in (w or "").lower() else None)
    ran = []
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: ran.append((n, a)) or "Logged.")
    context = SimpleNamespace(paths=book)
    for words in ("I practiced for 30 minutes today", "practiced guitar for an hour", "I played guitar for 45 minutes"):
        assert assistant_turn._own_tool_reply(context, words) == "Logged.", words
    assert [a["minutes"] for _n, a in ran] == [30.0, 60, 45.0]
    assert assistant_turn._own_tool_reply(context, "I played golf for 2 hours") != "Logged."
    monkeypatch.setattr(paths, "next_step", lambda b, p: f"next[{p.name}]")
    assert her_asks.reply(context, "Logged. Guitar this week: 1 of 1 days, 30 minutes.", "what should I work on next?") \
        == "next[Guitar]"
    assert her_asks.reply(context, "Done.", "what should I work on next?") is None
