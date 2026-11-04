"""The council's floor (DEC-0080/0081, core/council_floor.py): members can
talk to each other, but only through MIA, within each turn's budget, and as
cheaply as it can be done."""

import pytest

from core import council, council_floor as floor
from core.dev_store import DevStore

READY = {"mia", "claude", "codex", "qwen", "chatgpt"}


@pytest.fixture
def chat(tmp_path, monkeypatch):
    store, repo = DevStore(tmp_path / "council"), tmp_path / "council.jsonl"
    monkeypatch.setattr(council, "_store", lambda: store)
    monkeypatch.setattr(council, "REPO_LOG", repo)
    monkeypatch.setattr("core.self_docs.answer", lambda q, **k: "From DEC-0062: the relay is sealed.")
    monkeypatch.setattr("core.work_activity.ACTIVITY", tmp_path / "activity.jsonl")
    floor._SUMMARIES.clear()
    return store


def scripted(answers: dict):
    """A stand-in for the members: provider -> the answers it gives, in order; records each call."""
    calls = []

    def ask(provider, prompt):
        calls.append((provider, prompt))
        said = answers.get(provider, ["fine"])
        return said.pop(0) if len(said) > 1 else said[0]
    ask.calls = calls
    return ask


def run(store, text, ask, ready=READY, summarize=lambda p: "They agree on the cache; codex wants a test."):
    root = council.post("zac", text, store=store, plan=floor.plan(text, sorted(ready)))
    return floor.run(root, ask=ask, summarize=summarize, ready=ready, store=store), root


def test_what_a_message_asks_for():
    here = sorted(READY)
    assert floor.plan("@claude what next?", here) == {"mode": "ask", "order": ["claude"], "rounds": 1, "budget": 2}
    assert floor.plan("@claude @codex debate the cache", here)["mode"] == "debate"
    assert floor.plan("@claude @codex debate the cache", here)["budget"] == 4
    assert floor.plan("Council, work it out", here)["order"] == ["claude", "chatgpt", "codex", "qwen"]
    assert floor.plan("@all thoughts? budget 3", here)["budget"] == 3
    assert floor.plan("@claude budget 99", here)["budget"] == floor.MAX_BUDGET
    assert floor.plan("just a note to self", here)["order"] == []


def test_a_member_asks_another_through_mia_and_she_sums_up(chat):
    ask = scripted({"claude-code": ["Cache it per thread.\nASK codex: is a per-thread cache safe with two writers?"],
                    "codex": ["Yes, if writes go through one lock."]})
    posted, root = run(chat, "@claude how should we cache summaries?", ask)
    kinds = [(m["who"], m["kind"]) for m in posted]
    assert kinds == [("claude", "answer"), ("mia", "note"), ("codex", "answer"), ("mia", "summary")]
    assert posted[1]["text"] == "Claude asks Codex: is a per-thread cache safe with two writers?"
    assert [p for p, _ in ask.calls] == ["claude-code", "codex"]
    assert floor.spent(root["id"], council.thread(root["id"], chat)) == 2
    assert all(m["thread"] == root["id"] and m["turn"] == root["id"] for m in posted)


def test_a_question_past_the_budget_is_held_and_says_why(chat):
    ask = scripted({"claude-code": ["Maybe.\nASK codex: is it safe?"]})
    posted, _ = run(chat, "@claude is it safe? budget 1", ask)
    assert [p for p, _ in ask.calls] == ["claude-code"]
    assert posted[-1]["kind"] == "note" and "budget is spent" in posted[-1]["text"]


def test_a_question_about_whats_decided_goes_to_mia_for_free(chat):
    ask = scripted({"claude-code": ["Depends.\nASK codex: what did we decide about the relay?"]})
    posted, _ = run(chat, "@claude is the relay safe?", ask)
    assert [p for p, _ in ask.calls] == ["claude-code"]  # codex never called
    assert posted[1]["text"].startswith("Claude asks MIA:") and posted[2]["who"] == "mia"
    assert "DEC-0062" in posted[2]["text"]


def test_a_repeat_question_and_an_absent_member_are_held(chat):
    ask = scripted({"claude-code": ["One.\nASK codex: is the cache safe with two writers?"],
                    "codex": ["Yes.\nASK claude: is the cache safe with two writers?"]})
    posted, _ = run(chat, "@claude cache? budget 6", ask)
    assert "already asked" in posted[-2]["text"] or "already asked" in posted[-1]["text"]
    ask2 = scripted({"claude-code": ["Hmm.\nASK copilot: can you check the tests?"]})
    posted, _ = run(chat, "@claude tests?", ask2)
    assert "isn't available" in posted[-1]["text"] and [p for p, _ in ask2.calls] == ["claude-code"]


def test_a_debate_runs_two_rounds_and_stops_when_they_agree(chat):
    ask = scripted({"claude-code": ["Use a lock.", "Fair point on reads.\nAGREE"],
                    "codex": ["A queue is safer.", "A lock with a read path works.\nAGREE"]})
    posted, root = run(chat, "@claude @codex debate how to guard the cache", ask)
    assert [p for p, _ in ask.calls] == ["claude-code", "codex", "claude-code", "codex"]
    assert "Second round" in ask.calls[2][1]
    assert any(m["text"] == "They agree." for m in posted) and posted[-1]["kind"] == "summary"
    assert floor.spent(root["id"], council.thread(root["id"], chat)) == 4


def test_a_member_that_only_repeats_itself_drops_out(chat):
    ask = scripted({"claude-code": ["Use a lock around every write to the cache."],
                    "codex": ["A queue is better.", "Still a queue.\nASK claude: why a lock over a queue here?"]})
    posted, _ = run(chat, "@claude @codex debate the cache, budget 6", ask)
    assert [p for p, _ in ask.calls] == ["claude-code", "codex", "claude-code", "codex"]
    assert any("only been repeating" in m["text"] for m in posted)  # claude said the same twice: not asked again


def test_members_read_a_summary_of_a_long_thread_not_the_chat(chat):
    said = [{"who": w, "text": t, "thread": "x", "kind": "answer"} for w, t in
            [("zac", "q"), ("claude", "a" * 900), ("codex", "b"), ("qwen", "c"), ("claude", "d")]]
    summaries = []
    text = floor.context_for(said, lambda p: summaries.append(p) or "Claude and Codex disagree on the lock.")
    assert text.startswith("Summary of the thread so far (by MIA):\nClaude and Codex disagree")
    assert "[qwen] c" in text and "[claude] d" in text and "a" * 700 not in text
    floor.context_for(said, lambda p: summaries.append(p) or "again")
    assert len(summaries) == 1  # cached
    short = floor.context_for(said[:2], None)
    assert short.startswith("[zac] q")


def test_zac_saying_stop_stops_it(chat):
    def ask(provider, prompt):
        root = next(m for m in chat.tail(5) if m["who"] == "zac")
        council.post("zac", "stop", reply_to=root["id"], store=chat)
        return "first answer"
    posted, _ = run(chat, "@claude @codex @qwen discuss the plan", ask)
    assert posted[-1]["text"] == "Stopped, as you asked."
    assert sum(1 for m in posted if m["kind"] == "answer") == 1


def test_a_member_that_cant_answer_is_out_for_the_rest(chat):
    calls = []

    def ask(provider, prompt):
        calls.append(provider)
        if provider == "codex":
            raise RuntimeError("You've hit your usage limit")
        return "ok.\nASK codex: and you?" if provider == "claude-code" else "ok"
    posted, _ = run(chat, "@codex @claude discuss", ask)
    assert calls == ["codex", "claude-code"] and "isn't available" in posted[-1]["text"]


def test_answers_never_ask_anyone_themselves(chat):
    ask = scripted({"claude-code": ["@codex @all you should all weigh in"]})
    posted, _ = run(chat, "@claude hi", ask)
    assert posted[0]["kind"] == "answer" and posted[0]["asks"] == []


def test_a_passed_question_takes_the_members_turn(chat):
    ask = scripted({"qwen-x": ["-"], "ollama": ["Every answer.\nASK coder: is that feasible?"],
                    "ollama-coder": ["Yes, it's feasible."]})
    posted, root = run(chat, "@qwen @coder discuss when to summarize", ask, ready=READY | {"coder"})
    assert [p for p, _ in ask.calls] == ["ollama", "ollama-coder"]  # coder answers once, not twice
    assert floor.spent(root["id"], council.thread(root["id"], chat)) == 2


def test_echoes_are_tidied_away():
    said = "[zac] the question\n[qwen] what qwen said\nQwen prefers breaks; Coder prefers every answer."
    assert floor.tidy(said, ["zac", "qwen", "coder"]) == "Qwen prefers breaks; Coder prefers every answer."
    assert floor.tidy("Coder: it works.", ["coder"]) == "it works."
