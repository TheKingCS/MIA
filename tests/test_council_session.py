"""Council Mode through the glasses (T-0035, core/council_session.py): opened
and closed by voice, members addressed by name the way speech recognition
hears them, answers arriving as cards with who's speaking and in what voice."""

import pytest

from core import council, council_session as cs, glasses_feed
from core.dev_store import DevStore


@pytest.fixture
def meeting(tmp_path, monkeypatch):
    store = DevStore(tmp_path / "council")
    monkeypatch.setattr(council, "_store", lambda: store)
    monkeypatch.setattr(council, "REPO_LOG", tmp_path / "council.jsonl")
    monkeypatch.setattr(council, "here", lambda: ["mia", "claude", "codex"])
    monkeypatch.setattr("core.council_floor.ready_members", lambda: {"mia", "claude", "codex", "chatgpt"})
    monkeypatch.setattr("core.work_dashboard.allowed", lambda context, pid: pid == "zac")
    cs._sessions.clear()
    runs = []
    yield store, runs
    cs._sessions.clear()


def say(text, runs, who="zac"):
    return cs.hear(None, who, text, run=lambda pid, message: runs.append(message))


def test_opened_by_voice_and_only_for_the_owner(meeting):
    store, runs = meeting
    assert say("what's on today?", runs) is None  # not a council word: MIA's as usual
    assert say("MIA, bring the council together", runs, who="robin") is None  # not the owner
    opened = say("MIA, let's bring the council together", runs)
    assert opened["council"] and opened["say"] == "The council's here: Claude and Codex. Who goes first?"
    assert cs.active("zac") and not cs.active("robin")


def test_members_by_name_as_speech_hears_them(meeting):
    store, runs = meeting
    say("bring the council together", runs)
    assert say("Cloud, start us off on independence", runs)["say"] == "Claude is looking."
    assert runs[-1]["text"] == "@claude start us off on independence" and runs[-1]["plan"]["order"] == ["claude"]
    say("chat GPT and codex, debate it", runs)
    assert runs[-1]["plan"]["mode"] == "debate" and runs[-1]["plan"]["order"] == ["chatgpt", "codex"]
    say("everyone, what's missing?", runs)
    assert runs[-1]["text"].startswith("@all") and runs[-1]["plan"]["mode"] == "discuss"
    assert say("MIA, sum it up", runs)["say"] == "Let me look."  # MIA, no paid call
    assert say("that's a good point though", runs)["say"] == "Noted."  # asks no one
    thread = {m["thread"] for m in store.tail(20)}
    assert len(thread) == 1  # one session, one thread


def test_hold_on_and_closing(meeting):
    store, runs = meeting
    say("council mode", runs)
    assert say("hold on", runs)["say"] == "Stopped."
    assert store.tail(1)[0]["text"] == "stop"  # the floor stops on it
    closed = say("that's all for now", runs)
    assert closed["ended"] and not cs.active("zac")
    assert say("Claude, one more thing", runs) is None  # closed: back to MIA


def test_answers_reach_the_glasses_with_speaker_and_voice(meeting):
    card = glasses_feed.council_said("zac", "codex", "Two risks. The relay key never rotates, so a leak is "
                                     "forever. And the cache isn't locked. Fix the rotation first.\nASK claude: can it rotate?")
    assert card["headline"] == "Codex" and card["speaker"] == "codex" and card["voice"].startswith("kokoro:")
    assert card["generated"] and "ASK" not in card["say"] and card["say"].startswith("Two risks.")
    assert len(cs.spoken("word " * 200).split()) <= cs.SPOKEN_WORDS + 1


def test_the_floor_reports_each_answer_as_it_comes(meeting, monkeypatch):
    from core import council_floor

    store, _ = meeting
    root = council.post("zac", "@claude @codex discuss", store=store,
                        plan=council_floor.plan("@claude @codex discuss", ["claude", "codex", "mia"]))
    heard = []
    council_floor.run(root, ask=lambda p, prompt: "Fine.", summarize=lambda p: "They agree.",
                      ready={"claude", "codex", "mia"}, store=store, on_said=heard.append)
    assert [m["who"] for m in heard] == ["claude", "codex", "mia"] and heard[-1]["kind"] == "summary"


def test_one_member_away_doesnt_stop_the_rest(meeting, monkeypatch):
    store, runs = meeting
    monkeypatch.setattr("core.council_floor.ready_members", lambda: {"mia", "codex"})
    say("bring the council together", runs)
    answer = say("Claude and Codex, what do you think?", runs)
    assert answer["say"] == "Claude isn't available right now. Codex is looking." and runs[-1]["plan"]["order"] == ["claude", "codex"]
    monkeypatch.setattr("core.council_floor.ready_members", lambda: {"mia"})
    assert say("Claude?", runs)["say"] == "Claude isn't available right now."