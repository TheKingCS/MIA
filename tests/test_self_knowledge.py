"""
tests.test_self_knowledge
===========================

What MIA can honestly say about herself (core/self_knowledge.py): grounded in real data, never guessed. `about_me`
reports her real scale from the system map; `my_focus` reflects her Night School directive; `what_i_know_about_you`
is honest about how much she knows; a missing source is a quiet gap, not a crash; and a question about her (not
about one of her apps) gets these facts, her scale read once and kept a while for answers.
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


def test_a_question_about_her_is_told_apart_from_a_how_to_about_an_app():
    for q in ("How do you learn?", "What are you working on?", "How does MIA remember things?",
              "Tell me about your night school", "Can you learn from me?"):
        assert self_knowledge.about_herself(q), q
    for q in ("How do I add a bill?", "How do you add a bill?", "What should I make for dinner?", ""):
        assert not self_knowledge.about_herself(q), q


def test_her_facts_for_a_question_about_herself_are_from_the_records(monkeypatch):
    from core import night_school

    monkeypatch.setattr(night_school, "settings", lambda *a, **k: {"directive": "Become a top-tier AI."})
    block = self_knowledge.grounding_block(SimpleNamespace())
    assert block.startswith("What's true about you, from your own records.")
    assert "I'm MIA" in block and "Become a top-tier AI." in block and "still getting to know you" in block


def test_her_scale_is_read_once_and_kept_a_while(monkeypatch):
    from core import system_map

    calls = []
    real = system_map.assemble
    monkeypatch.setattr(system_map, "assemble", lambda *a, **k: calls.append(1) or real(*a, **k))
    monkeypatch.setitem(self_knowledge._about_me_cache, "text", "")
    first = self_knowledge._about_me_kept()
    assert self_knowledge._about_me_kept() == first and len(calls) == 1
    self_knowledge.about_me()  # the About page's own read stays live
    assert len(calls) == 2
