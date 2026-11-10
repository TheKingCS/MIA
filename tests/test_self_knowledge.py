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


def test_every_topic_points_at_files_decisions_apps_and_readers_that_are_really_there():
    from core import capabilities, self_docs

    apps = {a["id"] for a in capabilities.capability_map()}
    for topic in self_knowledge.TOPICS:
        for rel in topic.files:
            assert (self_knowledge.ROOT / rel).is_file(), (topic.name, rel)
        for dec in topic.decisions:
            assert self_docs.decision(dec) is not None, (topic.name, dec)
        for app in topic.apps:
            assert app in apps, (topic.name, app)
        for name in topic.live:
            assert callable(getattr(self_knowledge, name, None)), (topic.name, name)


def test_a_question_only_her_records_can_answer_is_told_from_one_about_the_person():
    for q in ("Tell me about how you were created.", "When did your development begin?",
              "What are your current limitations?", "What are we currently working toward?", "How do you learn?"):
        assert self_knowledge.asks_about_her(q), q
    for q in ("What's due this week?", "Can you show the grocery list on my glasses?",
              "Do you remember my dentist's name?", "Do you think I should learn Spanish?",
              "How do you improve greenhouse yields?"):
        assert not self_knowledge.asks_about_her(q), q


def test_describing_something_she_has_is_told_from_looking_up_or_changing_a_record():
    for q in ("Do you have a greenhouse app?", "What is the Chronicle?", "What apps do you have?"):
        assert self_knowledge.wants_described(None, q), q
    for q in ("What is the greenhouse temperature?", "Add milk to the grocery list"):
        assert not self_knowledge.wants_described(None, q), q


def test_the_block_for_a_question_about_her_says_where_each_line_comes_from():
    block = self_knowledge.block_for(SimpleNamespace(), "How do you learn?")
    assert block.startswith("About you, MIA:") and len(block) <= self_knowledge.BLOCK_CHARS
    assert "[decision DEC-0049, " in block and "[my code and documents, core/failure_log.py]" in block
    assert all(line.startswith("- [") for line in block.split(chr(10))[1:])
    for q in ("Can you show the grocery list on my glasses?", "What's due this week?", ""):
        assert self_knowledge.block_for(SimpleNamespace(), q) == "", q


def test_the_two_things_called_chronicle_are_both_named_from_their_own_files():
    said = self_knowledge._two_chronicles(None)
    assert len(said) == 1 and "core/saga.py" in said[0] and "core/chronicle.py" in said[0]


def test_what_she_can_find_on_her_own_never_claims_a_search_of_the_network():
    said = " ".join(self_knowledge._device_facts(None))
    assert "plugged into this computer" in said and "Nothing of mine searches the network for devices" in said


def test_her_limits_name_what_is_not_set_up_and_leave_the_glasses_to_their_own_topic(monkeypatch):
    from core import service_map

    monkeypatch.setattr(service_map, "status", lambda context, service: service_map.MISSING)
    lines = self_knowledge._limit_facts(SimpleNamespace())
    missing = [x for x in lines if x.startswith("[what I run on, checked now]")]
    assert missing and service_map.SERVICES[0].name in missing[0]
    assert not any("on the glasses" in x for x in lines)


def test_a_sentence_saying_a_thing_is_retired_is_said_first():
    said = self_knowledge._status_first("It keeps the log. It grew over a year. It is no longer used.")
    assert said.startswith("It is no longer used.") and said.endswith("It grew over a year.")
    assert self_knowledge._status_first("It keeps the log.") == "It keeps the log."


def test_a_documents_opening_skips_its_heading_and_the_note_about_itself(tmp_path, monkeypatch):
    (tmp_path / "X.md").write_text("# Title\n\n*Rewritten each session.*\n\n> See also Y.\n\nShe keeps the garden log.\n",
                                   encoding="utf-8")
    monkeypatch.setattr(self_knowledge, "ROOT", tmp_path)
    assert self_knowledge._opening("X.md") == "She keeps the garden log."
    assert self_knowledge._opening("missing.md") == ""


def test_one_decision_is_read_with_its_status_in_its_first_words(tmp_path):
    from core import self_docs

    (tmp_path / "DECISIONS.md").write_text(
        "# Decisions\n\n### DEC-0001: Eggs are counted daily\n- Status: APPROVED (2026-01-02, after a long talk)\n"
        "- Decision: Count the eggs each morning.\n- Honest limits: None known.\n\n"
        "### DEC-0002: A thing still being weighed\n- Status: PROPOSED\n- What: Try the other way first.\n- Next: Ask.\n",
        encoding="utf-8")
    one = self_docs.decision("dec-0001", root=tmp_path)
    assert (one["id"], one["title"], one["status"]) == ("DEC-0001", "Eggs are counted daily", "APPROVED")
    assert one["gist"].startswith("Count the eggs each morning.")
    two = self_docs.decision("DEC-0002", root=tmp_path)
    assert two["status"] == "PROPOSED" and "Try the other way first." in two["gist"]
    assert self_docs.decision("DEC-0999", root=tmp_path) is None


def test_her_history_can_be_read_whole_or_by_kind():
    from core import dev_history

    store = SimpleNamespace(records=lambda: [{"kind": "commit", "ref": "a"}, {"kind": "decision", "ref": "b"}])
    assert len(dev_history.records(store=store)) == 2
    assert [r["ref"] for r in dev_history.records(("decision",), store)] == ["b"]


def test_where_the_storage_check_cannot_run_she_says_she_only_finds_serial_boards(monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert any("only find serial boards" in x for x in self_knowledge._device_facts(None))
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/" + name)
    assert not any("only find serial boards" in x for x in self_knowledge._device_facts(None))
