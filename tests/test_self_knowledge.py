"""
tests.test_self_knowledge
===========================

What MIA can honestly say about herself (core/self_knowledge.py): grounded in real data, never guessed. `about_me`
reports her real scale from the system map; `my_focus` reflects her Night School directive; `what_i_know_about_you`
is honest about how much she knows; and a missing source is a quiet gap, not a crash.
"""

from types import SimpleNamespace

from core import self_knowledge


def test_about_me_reports_real_scale_not_a_guess():
    text = self_knowledge.about_me()
    assert text.startswith("I'm MIA") and "local-first" in text
    # it names real, non-zero counts from the system map (this repo has plenty of each)
    import re

    numbers = [int(n) for n in re.findall(r"\b(\d{2,})\b", text)]
    assert numbers and max(numbers) > 50  # files/tools/loops/decisions — real figures


def test_my_focus_reflects_the_night_school_directive(monkeypatch):
    from core import night_school

    monkeypatch.setattr(night_school, "settings", lambda *a, **k: {"directive": "Become a top-tier AI."})
    assert "Become a top-tier AI." in self_knowledge.my_focus()
    monkeypatch.setattr(night_school, "settings", lambda *a, **k: {"directive": ""})
    assert "build plan" in self_knowledge.my_focus()


def test_what_i_know_about_you_is_grounded_and_honest():
    # nothing known yet
    assert "still getting to know you" in self_knowledge.what_i_know_about_you(SimpleNamespace())
    # with directions, memories and learned style
    directions = SimpleNamespace(active=lambda: [SimpleNamespace(title="From consumer to producer"),
                                                 SimpleNamespace(title="Whimsy, art & tranquility")])
    memories = SimpleNamespace(all_memories=lambda: [1, 2, 3])
    style = SimpleNamespace(picks=[1])
    ctx = SimpleNamespace(direction=directions, user_memories=memories, response_style=style)
    text = self_knowledge.what_i_know_about_you(ctx)
    assert "From consumer to producer" in text and "3 things" in text and "how you like me to answer" in text


def test_a_missing_source_is_a_quiet_gap_not_a_crash():
    # a context with a broken store still produces an answer
    broken = SimpleNamespace(direction=SimpleNamespace(active=lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
    assert self_knowledge.what_i_know_about_you(broken)  # no raise, returns the honest default
    assert self_knowledge.self_summary(SimpleNamespace())  # the whole summary still assembles
