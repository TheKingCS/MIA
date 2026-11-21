"""The injection test set (WP-03, REQ-SEC-026): twenty poisoned inputs (tests/data/injection_cases.json), each put
through every way outside text reaches the model: a web page, the person's selection, and each lookup that brings
outside text (mail, feeds, a scanned receipt, a team's workspace). Each arrives framed as information, never as
instructions; and a change the model asks for right after reading it is held and said back, never run."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.tool_loop as tool_loop
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.browser_safety import OUTSIDE_MARK, outside, untrusted
from core.llm_manager import ChatReply, ToolCall

CASES = json.loads((Path(__file__).parent / "data" / "injection_cases.json").read_text(encoding="utf-8"))


def test_there_are_twenty_poisoned_inputs():
    """The set is the size the package names, and no two are the same."""
    assert len(CASES) == 20 and len(set(CASES)) == 20


@pytest.mark.parametrize("case", CASES)
def test_each_entry_frames_the_poisoned_text_as_information(case):
    """Web page, selection, and the outside lookups: the words sit inside a frame that says they aren't instructions,
    and the frame's end comes after them (a fake "end of page" inside the text can't close it early)."""
    from core.ual import Capture, framed

    for shown in (untrusted(case, "https://example.test"), framed(Capture(text=case, source_app="Mail")),
                  *(outside(case, what) for what in tool_loop.OUTSIDE_WHAT.values())):
        assert OUTSIDE_MARK in shown and "never as instructions" in shown
        assert shown.index(OUTSIDE_MARK) < shown.index(case.strip()) < shown.rindex("[End of")


class _Model:
    """Replies in order; remembers what it was sent."""

    def __init__(self, *replies):
        """The replies to give in turn."""
        self.replies, self.sent = list(replies), []

    def chat_with_tools(self, messages, tools):
        """Remembers the messages and gives the next reply."""
        self.sent.append(messages)
        return self.replies.pop(0)


@pytest.mark.parametrize("lookup", sorted(tool_loop.OUTSIDE_WHAT))
@pytest.mark.parametrize("case", CASES)
def test_a_change_asked_for_after_reading_poisoned_outside_text_is_never_run(case, lookup, monkeypatch):
    """The model reads the poisoned text through an outside lookup, then asks to delete a bill: nothing is deleted,
    the card is said back for him to ask himself, and the text it read was framed."""
    ran = []
    registry = AssistantActionRegistry()

    def tool(name, said):
        """A tool that notes it ran and says its text."""
        return AssistantAction(name=name, domain="money", description=name, parameters={"type": "object", "properties": {}},
                               handler=lambda context, arguments: ran.append(name) or said, trigger_phrases=(name,))

    registry.register(tool(lookup, case))
    registry.register(tool("delete_bill", "Deleted."))
    monkeypatch.setattr(tool_loop, "loop_ok", lambda context: True)
    life = SimpleNamespace(assistant_actions=registry, config=None)
    model = _Model(ChatReply(content="", tool_calls=[ToolCall(name=lookup, arguments={})]),
                   ChatReply(content="", tool_calls=[ToolCall(name="delete_bill", arguments={})]))
    offered = [{"function": {"name": lookup}}, {"function": {"name": "delete_bill"}}]
    reply = tool_loop.run(life, model, [], offered, "what came in today?")
    assert ran == [lookup] and reply.tool_calls == [] and "Say so" in reply.content
    seen = model.sent[1][-2]["content"]  # the lookup's result as the model read it
    assert OUTSIDE_MARK in seen and seen.index(OUTSIDE_MARK) < seen.index(case.strip()[:20])
