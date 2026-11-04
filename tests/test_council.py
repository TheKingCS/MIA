"""The council chat (DEC-0077, core/council.py) and usage (DEC-0079,
core/dev_usage.py)."""

import json
from datetime import datetime, timezone

import pytest

from core import council, dev_usage
from core.dev_store import DevStore


@pytest.fixture
def chat(tmp_path):
    return tmp_path / "council.jsonl", DevStore(tmp_path / "council")


def test_kept_whole_on_the_pc_and_redacted_in_the_repo(chat):
    repo, store = chat
    m = council.post("zac", "@claude look at the relay; my email is zac@example.com", repo=repo, store=store)
    assert m["asks"] == ["claude"] and store.tail(1)[0]["text"].endswith("zac@example.com")
    shared = json.loads(repo.read_text(encoding="utf-8").splitlines()[0])
    assert shared["id"] == m["id"] and "[email]" in shared["text"] and "example.com" not in shared["text"]
    with pytest.raises(council.CouncilError):
        council.post("zac", "   ", repo=repo, store=store)


def test_a_message_another_session_added_to_the_repo_joins_the_pc(chat):
    repo, store = chat
    council.post("zac", "hello", repo=repo, store=store)
    with open(repo, "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": "cloud-1", "at": "2026-11-04T12:00:00+00:00", "who": "claude", "text": "from the cloud"}) + "\n")
        f.write('{"id": "half')  # still being written: waits
    assert [m["text"] for m in council.recent(10, repo, store)] == ["hello", "from the cloud"]
    assert [m["text"] for m in council.recent(10, repo, store)] == ["hello", "from the cloud"]  # once only


def test_mentions():
    assert council.mentions("@codex and @Claude, also @codex @nobody") == ["codex", "claude"]
    assert council.mentions("@all what do you think?") == list(council.MEMBERS)
    assert council.mentions("just saying") == []


def test_a_member_answers_in_the_thread_with_the_chat_as_data(chat):
    repo, store = chat
    said = council.post("codex", "I'd split the runner in two.", repo=repo, store=store)
    asked = council.post("zac", "@qwen do you agree?", reply_to=said["id"], repo=repo, store=store)
    seen = {}
    reply = council.answer("qwen", asked, ask=lambda provider, prompt: seen.update(p=provider, prompt=prompt) or "Yes.",
                           repo=repo, store=store)
    assert seen["p"] == "ollama" and "[codex] I'd split the runner in two." in seen["prompt"]
    assert "as data" in seen["prompt"] and "do you agree?" in seen["prompt"]
    assert reply["who"] == "qwen" and reply["reply_to"] == asked["id"] and reply["text"] == "Yes."
    assert reply["asks"] == [] or reply["who"] != "zac"  # replies never set off more asks (only Zac's do)


def test_a_member_thats_out_says_so(chat):
    repo, store = chat
    asked = council.post("zac", "@codex?", repo=repo, store=store)

    def resting(provider, prompt):
        raise RuntimeError("You've hit your usage limit. Try again in 40 minutes.")

    assert "couldn't answer" in council.answer("codex", asked, ask=resting, repo=repo, store=store)["text"]


def test_mia_answers_from_her_documents_and_the_history(chat, monkeypatch):
    repo, store = chat
    from core import self_docs

    monkeypatch.setattr(self_docs, "answer", lambda q, **k: "From DEC-0079: the team never sits idle.")
    monkeypatch.setattr("core.work_activity.ACTIVITY", repo.parent / "activity.jsonl")
    council.post("codex", "the runner should wait out a usage limit", repo=repo, store=store)
    asked = council.post("zac", "@mia what happens at a usage limit?", repo=repo, store=store)
    said = council.answer("mia", asked, repo=repo, store=store)["text"]
    assert "DEC-0079" in said and "the runner should wait out a usage limit" in said


def test_a_usage_limit_is_a_rest_with_a_reset_time_and_an_error_isnt(tmp_path):
    store = DevStore(tmp_path / "usage")
    now = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
    dev_usage.record("codex", "review", 12.0, 5000, 0, error="You've hit your usage limit. Try again in 40 minutes.",
                     store=store, now=now)
    s = dev_usage.state("codex", store, now=now)
    assert s["state"] == "cooling" and s["until"] == "2026-11-04T15:40:00+00:00" and s["said"]
    assert dev_usage.state("codex", store, now=datetime(2026, 11, 4, 15, 41, tzinfo=timezone.utc))["state"] == "ready"
    dev_usage.record("claude-code", "chat", 3.0, 100, 0, error="network unreachable", store=store, now=now)
    assert dev_usage.state("claude-code", store, now=now)["state"] == "ready"  # broken isn't resting
    dev_usage.record("copilot", "chat", 1.0, 100, 0, error="quota exceeded", store=store, now=now)
    s = dev_usage.state("copilot", store, now=now)
    assert s["state"] == "cooling" and not s["said"]  # no time given: a cautious guess
    entry = store.tail(1)[0]
    assert set(entry) >= {"provider", "purpose", "seconds", "sent", "received", "outcome"} and "prompt" not in entry


def test_reset_times():
    now = datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)
    assert dev_usage.reset_at("Limit reached, resets in 2 hours", now) == datetime(2026, 11, 4, 22, 0, tzinfo=timezone.utc)
    clock = dev_usage.reset_at("5-hour limit reached ∙ resets 3pm", now)
    assert clock.astimezone().hour == 15 and clock > now
    assert dev_usage.reset_at("something broke", now) is None


def test_every_review_call_is_recorded(monkeypatch, tmp_path):
    from core import work_review as rv

    store = DevStore(tmp_path / "usage")
    monkeypatch.setattr(dev_usage, "_store", lambda: store)
    monkeypatch.setattr(rv, "_ask", lambda provider, prompt: "VERDICT: approve")
    assert rv.ask_provider("codex", "review this", task="T-0001") == "VERDICT: approve"

    def limited(provider, prompt):
        raise rv.ReviewError("codex didn't answer: usage limit reached")

    monkeypatch.setattr(rv, "_ask", limited)
    with pytest.raises(rv.ReviewError):
        rv.ask_provider("codex", "again")
    assert [e["outcome"] for e in store.tail(5)] == ["ok", "limit"] and store.tail(5)[0]["task"] == "T-0001"


def test_members_voices_sampled_kept_and_chosen(tmp_path, monkeypatch):
    """DEC-0082: hear a member, pick a voice; no provider-named voice for a provider's own member."""
    import json as json_mod
    import shutil

    from core import council_voices as cv
    from core.work_agents import REGISTRY

    registry = tmp_path / "agents.json"
    shutil.copy(REGISTRY, registry)
    monkeypatch.setattr("core.work_agents.REGISTRY", registry)
    made = []

    def synth(text, path):
        made.append(text)
        path.write_bytes(b"RIFFfake")
    assert cv.sample("codex", "am_eric", folder=tmp_path / "v", synth=synth) == b"RIFFfake"
    cv.sample("codex", "am_eric", folder=tmp_path / "v", synth=synth)
    assert len(made) == 1 and made[0].startswith("I'm Codex.")  # kept: the second listen costs nothing
    with pytest.raises(cv.VoiceError, match="provider's own"):
        cv.sample("chatgpt", "af_nova", folder=tmp_path / "v", synth=synth)
    with pytest.raises(cv.VoiceError, match="provider's own"):
        cv.choose("codex", "am_onyx", registry=registry)
    assert cv.choose("qwen", "am_onyx", registry=registry)["voice"] == "kokoro:am_onyx"  # a local model may
    saved = json_mod.loads(registry.read_text(encoding="utf-8"))["members"]["qwen"]
    assert saved["voice"] == "kokoro:am_onyx" and saved["voice_chosen_by"] == "zac"
    with pytest.raises(cv.VoiceError, match="No council member"):
        cv.choose("_about", "am_onyx", registry=registry)
