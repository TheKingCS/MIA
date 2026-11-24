"""Trigger phrases that fired inside sentences meant for another app (found by laying every tool's phrases over the
routing corpus, 2026-11-24): a bought drill isn't clothing, "my own time" isn't whose a tool is, "what depends on
selling the lot" isn't an app's record, "add to my notes" and "what's in my inbox" aren't a tracker MIA made, and
"how far along is the coop project" is the project's, not the freedom plan's. A tracker is reached by its title."""

from types import SimpleNamespace

import pytest

from tests.assistant_registry import build_desktop_registry
from tests.test_assistant_routing import demo_context


@pytest.fixture(scope="module")
def registry():
    """The desktop's full tool registry."""
    return build_desktop_registry()


@pytest.mark.parametrize("said, never", [
    ("I bought a DeWalt drill for $199 for the greenhouse", "add_clothing"),
    ("Paying off debt is so I can control my own time", "set_item_owner"),
    ("What depends on selling the lot?", "describe_app"),
    ("Add to my notes for GFCI outlets: test them monthly", "add_to_creation"),
    ("What's in my inbox?", "read_creation"),
    ("how far along is the chicken coop project", "get_freedom_progress"),
])
def test_a_phrase_inside_another_apps_sentence_no_longer_brings_its_tool(registry, said, never):
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    assert never not in [a.name for a in registry.matching_actions(said, context)], said


@pytest.mark.parametrize("said, tool", [
    ("I bought a jacket at the outlet", "add_clothing"), ("the chainsaw is my own", "set_item_owner"),
    ("add to my seed bank: variety Brandywine", "add_to_creation"), ("what's in my seed bank?", "read_creation"),
])
def test_the_narrowed_phrases_still_reach_their_tool(registry, said, tool):
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry,
                              creations=SimpleNamespace(items=[{"id": "c1", "title": "Seed Bank", "status": "published"}]))
    assert tool in [a.name for a in registry.matching_actions(said, context)], said
