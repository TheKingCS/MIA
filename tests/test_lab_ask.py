"""
tests.test_lab_ask
====================

Ask MIA on a course's page (core/lab_ask.py): the material is core's own (a lab's sketch and build, a drill question's
choices and why), the model is asked with it and the question, the exchange goes into his conversation, a missing
model is said plainly, and questions about something that isn't there are refused.
"""

from types import SimpleNamespace

import pytest

from core import lab_ask


class _Model:
    """A stand-in model that keeps what it was asked and answers with a fixed line."""

    def __init__(self, answer="Because the resistor limits the current."):
        """Its answer."""
        self.answer, self.asked = answer, []

    def chat_with_tools(self, messages, tools):
        """Keeps the messages; answers."""
        self.asked.append(messages)
        return SimpleNamespace(content=self.answer, tool_calls=[])


class _Talks:
    """A stand-in conversation store."""

    def __init__(self):
        """One empty conversation, active."""
        self.conversation = SimpleNamespace(conversation_id="c1", messages=[])

    def get_active_conversation_id(self):
        """The one conversation."""
        return "c1"

    def get_conversation(self, conversation_id):
        """It."""
        return self.conversation

    def start_new_active_conversation(self):
        """It again."""
        return self.conversation

    def add_message(self, conversation_id, role, content):
        """Keeps it."""
        self.conversation.messages.append((role, content))


def test_a_labs_material_is_its_sketch_and_its_build_and_a_drills_is_its_choices():
    """The blink lab's material has the sketch and the build's why; the canning drill's question 2 has its choices,
    verdicts and the 240 °F; an unknown lab or a drill from another course is refused."""
    about, text = lab_ask.material("esp32", "blink")
    assert about == "the Blink the LED lab" and "digitalWrite(LED, HIGH)" in text and "limits the current" in text
    about, text = lab_ask.material("gardening", "canning_safe", "canning_day", 2)
    assert about == "the Putting up green beans drill, question 2" and "wrong." in text and "240 °F" in text
    with pytest.raises(ValueError):
        lab_ask.material("esp32", "nope")
    with pytest.raises(ValueError):
        lab_ask.material("esp32", "blink", "canning_day", 1)


def test_asking_goes_to_the_model_with_the_material_and_into_his_conversation():
    """The model gets the instruction, the material and his question; the answer comes back and both go into his
    conversation, marked with what it was about."""
    model, talks = _Model(), _Talks()
    got = lab_ask.ask(SimpleNamespace(llm=model, conversations=talks), "esp32", "blink", "  Why the resistor? ")
    assert got == {"answer": "Because the resistor limits the current.", "about": "the Blink the LED lab"}
    system, user = model.asked[0]
    assert "never invent a figure" in system["content"] and "220 ohm" in system["content"]
    assert user == {"role": "user", "content": "Why the resistor?"}
    assert talks.conversation.messages == [("user", "(On the Blink the LED lab) Why the resistor?"),
                                           ("assistant", "Because the resistor limits the current.")]


def test_no_model_or_no_question():
    """No model: said plainly, nothing kept. An empty question: refused."""
    talks = _Talks()
    got = lab_ask.ask(SimpleNamespace(llm=None, conversations=talks), "esp32", "blink", "Why?")
    assert got["answer"].startswith("I can't reach my model") and talks.conversation.messages == []
    with pytest.raises(ValueError):
        lab_ask.ask(SimpleNamespace(llm=_Model()), "esp32", "blink", "   ")
