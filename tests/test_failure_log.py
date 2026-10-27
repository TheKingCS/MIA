"""The Fix-It Log (DEC-0049): where MIA stumbles is recorded (privately,
redacted), grouped into issues, turned into a fix report with a test to
write first, and what the person confirms she learns herself."""

from datetime import datetime, timedelta, timezone

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def mia(shop):  # noqa: F811
    from core.conversation_manager import Conversation
    from core.failure_log import FailureLog

    shop.failures = FailureLog(shop, data_dir=shop.my_dir)
    shop.chat = Conversation(conversation_id="c1")
    return shop


def _say(conversation, role, text, seconds_ago=5):
    from core.conversation_manager import ConversationMessage

    at = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    conversation.messages.append(ConversationMessage(role=role, content=text, timestamp=at))


def test_what_a_log_may_keep():
    from core.failure_log import issue_key, redact, similar

    assert redact("my password is hunter2 and email me at a@b.co") == "my password is [hidden] and email me at [email]"
    assert redact("card 4111 1111 1111 1111 please") == "card [number] please"
    assert similar("log my shift 8 hours", "log my 8 hour shift") >= 0.5 and similar("add milk", "what's the weather") == 0
    assert issue_key("tool_error", tool="log_shift") == "tool:log_shift" and issue_key("said_wrong") == "turn:chat"


def test_the_person_says_it_went_wrong(mia):
    from core.failure_log import observe_prompt

    w, c = mia, mia.chat
    _say(c, "user", "log my shift")
    _say(c, "assistant", "Here's the weather.")
    assert observe_prompt(w, c, "no, I meant log my work shift") is None
    e = w.failures.events()[-1]
    assert e["kind"] == "said_wrong" and e["before"] == "log my shift" and e["reply"] == "Here's the weather."
    said = observe_prompt(w, c, "MIA, report a problem: the loot was wrong on Tuesday")
    assert said.startswith("Got it. I've logged that") and w.failures.events()[-1]["note"] == "the loot was wrong on Tuesday"
    # Asking again in other words within two minutes, and undoing right after.
    _say(c, "user", "add eggs to the grocery list")
    _say(c, "assistant", "I couldn't find that.")
    observe_prompt(w, c, "put eggs on my grocery list")
    assert w.failures.events()[-1]["kind"] == "rephrased"
    observe_prompt(w, c, "undo that")
    assert w.failures.events()[-1]["kind"] == "undo_soon"


def test_private_turns_are_never_logged(mia):
    from core.failure_log import observe_prompt

    w, c = mia, mia.chat
    c.off_record = True
    _say(c, "user", "log my shift")
    _say(c, "assistant", "No.")
    observe_prompt(w, c, "that's wrong")
    assert w.failures.events() == []


def test_what_mia_sees_herself(mia):
    from core.failure_log import observe_tool_error, observe_turn

    w, c = mia, mia.chat
    observe_turn(w, c, "log 9 hours at work", tools_offered=["log_shift"], tool_called="", reply="Sounds like a long day!")
    observe_turn(w, c, "add a widget to the thingamajig", tools_offered=[], reply="Hmm.")
    observe_turn(w, c, "hello", tools_offered=[], llm_available=False)
    observe_turn(w, c, "how are you", tools_offered=[], reply="Good!", seconds=40)
    observe_tool_error(w, "log_shift", "KeyError: 'hours'", {"hours": None})
    kinds = [e["kind"] for e in w.failures.events()]
    assert kinds == ["talked_instead", "no_tool", "model_down", "slow", "tool_error"]
    issues = {i["key"]: i for i in w.failures.issues()}
    assert issues["tool:log_shift"]["title"] == "The log shift tool broke" and issues["routing:log_shift"]["count"] == 1
    # Worst first: a broken tool outranks a slow answer.
    keys = [i["key"] for i in w.failures.issues()]
    assert keys.index("tool:log_shift") < keys.index("slow")


def test_a_retry_that_worked_is_offered_and_remembered_only_on_yes(mia):
    from core.failure_log import observe_prompt, observe_turn

    w, c = mia, mia.chat
    _say(c, "user", "got off work")
    _say(c, "assistant", "Nice, rest up!")
    observe_prompt(w, c, "no, I meant log my shift")
    offer = observe_turn(w, c, "no, I meant log my shift", tools_offered=["log_shift"], tool_called="log_shift", reply="Run cleared")
    assert offer == "(Want me to remember that “got off work” means this? Say “remember that”.)"
    assert observe_prompt(w, c, "remember that").startswith("Remembered: when you say “got off work”")
    assert [p["said"] for p in w.failures.phrases] == ["got off work"]
    assert w.failures.phrases_in("I just got off work!") and not w.failures.phrases_in("work is fine")
    # Anything else lets the offer go.
    c.pending_phrase = {"said": "x y z", "tool": "log_shift"}
    observe_prompt(w, c, "what's for dinner")
    assert c.pending_phrase is None and len(w.failures.phrases) == 1


def test_teaching_a_phrase_links_the_right_tool(mia):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_dungeon_actions import register_dungeon_actions
    from core.failure_log import observe_prompt

    w, c = mia, mia.chat
    w.assistant_actions = AssistantActionRegistry()
    register_dungeon_actions(w.assistant_actions)
    said = observe_prompt(w, c, "When I say clocked off, I mean log my shift")
    assert said == "Remembered: when you say “clocked off”, you mean log my shift."
    assert w.failures.phrases[0]["tool"] == "log_shift"
    # Routing now brings that tool when the phrase is said.
    assert "log_shift" in [a.name for a in w.assistant_actions.matching_actions("just clocked off", w)]


def test_issues_fixed_come_back_if_it_happens_again_and_the_report(mia):
    from core.failure_actions import failures_page
    from core.failure_log import observe_tool_error, write_report

    w = mia
    observe_tool_error(w, "log_shift", "KeyError")
    do(w, "failures.status", key="tool:log_shift", status="fixed")
    assert failures_page(w)["summary"]["open"] == 0
    observe_tool_error(w, "log_shift", "KeyError again")
    issue = next(i for i in w.failures.issues() if i["key"] == "tool:log_shift")
    assert issue["status"] == "open" and issue["reopened"]
    do(w, "failures.thumbs", prompt="what's my loot", reply="You have 3 chickens.", note="wrong app")
    page = failures_page(w)
    assert page["summary"]["open"] == 2 and "Test to write first" in page["report"]
    path = write_report(w)
    assert path.name == "fix_report.md" and "The log shift tool broke" in path.read_text(encoding="utf-8")
    assert "came back after a fix" in path.read_text(encoding="utf-8")


def test_the_log_by_voice(mia):
    from core.failure_actions import _get_issues
    from core.failure_log import observe_tool_error

    w = mia
    assert _get_issues(w, {}).startswith("Nothing's gone wrong")
    observe_tool_error(w, "log_shift", "KeyError")
    assert _get_issues(w, {}).startswith("1 open issue in the last two weeks. The log shift tool broke (1×).")
