"""
tests.test_assistant_routing
==============================

Enforces tests/assistant_routing_corpus.py against the real desktop
action registry: every realistic request reaches its tool, how-to
questions reach the help docs, and small talk stays tool-free. Plus unit
tests for the pieces that make that work (record-name lookup, quantity
parsing, keyword/record-name matching).
"""

from __future__ import annotations

import pytest

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_chat import looks_like_how_to_question
from core.assistant_domain_actions import parse_quantity_phrase
from core.assistant_lookup import head_word, resolve_by_name
from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools
from tests.assistant_routing_corpus import CORPUS, INFO, NO_TOOLS


@pytest.fixture(scope="module")
def registry():
    return build_desktop_registry()


@pytest.mark.parametrize("prompt, expected", CORPUS)
def test_corpus_prompt_reaches_expected_tool(registry, prompt, expected):
    tools = offered_tools(registry, prompt, demo_context())
    if expected == INFO:
        assert tools == [], f"{prompt!r} should be answered from help docs, got tools {tools}"
    else:
        assert expected in tools, f"{prompt!r} did not offer {expected}"


@pytest.mark.parametrize("prompt", NO_TOOLS)
def test_small_talk_stays_tool_free(registry, prompt):
    assert offered_tools(registry, prompt, demo_context()) == []


def test_every_corpus_tool_exists(registry):
    names = set(registry._actions)
    missing = {expected for _, expected in CORPUS if expected != INFO and expected not in names}
    assert not missing


# ------------------------------------------------------------------ how-to detection


@pytest.mark.parametrize("prompt", [
    "How do I add a bill?", "How can I add a recipe?", "Where do I see my debts?",
    "How does the Debts tab work?", "What does the Greenhouse module do?", "Is there a way to export my budget?",
])
def test_how_to_questions_detected(prompt):
    assert looks_like_how_to_question(prompt)


@pytest.mark.parametrize("prompt", [
    "How does my budget look?", "What does the mower need?", "What is the balance on my Chase card?",
    "How much have I spent?", "How far is camp?", "Where is the truck?",
])
def test_data_questions_are_not_how_to(prompt):
    assert not looks_like_how_to_question(prompt)


# ------------------------------------------------------------------ record lookup


TASKS = ["Oil change", "Rotate tires", "Sharpen blades", "Water tomatoes"]


@pytest.mark.parametrize("said, expected", [
    ("oil change", "Oil change"), ("OIL CHANGE", "Oil change"), ("the oil", "Oil change"),
    ("blades", "Sharpen blades"), ("watered the tomatoes", "Water tomatoes"), ("tires", "Rotate tires"),
])
def test_resolve_by_name_tolerant_match(said, expected):
    item, error = resolve_by_name(TASKS, said, str, "task")
    assert (item, error) == (expected, None)


def test_resolve_by_name_tie_asks_which():
    item, error = resolve_by_name(["Change oil", "Oil change"], "oil", str, "task")
    assert item is None and "Which one" in error and "Change oil" in error


def test_resolve_by_name_miss_lists_what_exists():
    item, error = resolve_by_name(TASKS, "brakes", str, "task")
    assert item is None and "Rotate tires" in error


def test_resolve_by_name_exact_only_for_destructive_use():
    item, error = resolve_by_name(["Riding Mower"], "mower", str, "asset", allow_fuzzy=False)
    assert item is None and "an asset" in error
    assert resolve_by_name(["Riding Mower"], "riding mower", str, "asset", allow_fuzzy=False) == ("Riding Mower", None)


@pytest.mark.parametrize("name, head", [
    ("Riding Mower", "mower"), ("Pepper Plants", "pepper"), ("Garden Omelette", "omelette"),
    ("Tomato Bed", "tomato"), ("Blueberry Bushes", "blueberry"), ("Chainsaw", "chainsaw"), ("", ""),
])
def test_head_word(name, head):
    assert head_word(name) == head


# ------------------------------------------------------------------ quantity parsing


@pytest.mark.parametrize("text, expected", [
    ("2 lb ground venison", (2.0, "lb", "ground venison")),
    ("a dozen eggs", (1.0, "dozen", "eggs")),
    ("1 1/2 cups flour", (1.5, "cups", "flour")),
    ("1/2 cup of sugar", (0.5, "cup", "sugar")),
    ("milk", (0.0, "", "milk")),
    ("two cans black beans", (2.0, "cans", "black beans")),
    ("10 pounds of flour", (10.0, "pounds", "flour")),
])
def test_parse_quantity_phrase(text, expected):
    assert parse_quantity_phrase(text) == expected


# ------------------------------------------------------------------ registry matching


def _registry_with(domain="garage"):
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="noop", domain=domain, description="", parameters={}, handler=lambda c, a: "", trigger_phrases=("zzz",),
    ))
    return registry


def test_domain_keywords_match_whole_words_only():
    registry = _registry_with()
    registry.register_domain_keywords("garage", ["led"])
    assert [a.name for a in registry.matching_actions("add a red led")] == ["noop"]
    assert registry.matching_actions("she called me") == []


def test_entity_names_match_on_head_word():
    registry = _registry_with()
    registry.register_entity_names("garage", lambda ctx: ["Riding Mower"])
    assert [a.name for a in registry.matching_actions("sharpened the mower blades", context=object())] == ["noop"]
    assert registry.matching_actions("riding the bus", context=object()) == []
    assert registry.matching_actions("sharpened the mower blades") == []  # no context, no record names


def test_entity_names_match_all_words_mode():
    registry = _registry_with("debts")
    registry.register_entity_names("debts", lambda ctx: ["Truck Loan"], match_all_words=True)
    assert registry.matching_actions("drove the truck", context=object()) == []
    assert registry.matching_actions("paid the truck loan", context=object())


def test_failing_entity_provider_is_skipped():
    registry = _registry_with()

    def broken(ctx):
        raise RuntimeError("boom")

    registry.register_entity_names("garage", broken)
    assert registry.matching_actions("anything", context=object()) == []
