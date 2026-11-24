"""
tests.test_everyday_phrasing_routing
======================================

The everyday ways he'd ask for the tools built 2026-11-23 and 24 reach them by their trigger phrases, without the
embedding model (the phone): who owes him, his emergency kit, the jars he puts up and his canning shelf, his
generator and preparedness settings, and how long the generator runs.
"""

import pytest

from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools

SAID = [
    ("who_owes_me", "Who owes me money?"), ("who_owes_me", "Has anyone not paid me yet?"),
    ("who_owes_me", "what's outstanding on my orders"), ("who_owes_me", "which customers still owe me"),
    ("emergency_kit", "check my emergency kit"), ("emergency_kit", "what am I missing for a go bag"),
    ("emergency_kit", "is my 72 hour kit complete?"), ("emergency_kit", "what should be in my bug out bag"),
    ("put_up_jars", "I put up 7 quarts of tomatoes today"), ("put_up_jars", "we canned 12 pints of salsa"),
    ("canning_shelf", "what's on my canning shelf?"), ("canning_shelf", "which canned stuff should I use first"),
    ("set_preparedness", "my generator burns half a gallon an hour"), ("set_preparedness", "plan for 3 people"),
    ("set_preparedness", "my generator uses 2 pounds of propane an hour"),
    ("how_prepared", "how many days could my generator run?"), ("how_prepared", "how prepared am I?"),
]


@pytest.fixture(scope="module")
def registry():
    """The desktop's tool registry, built once."""
    return build_desktop_registry()


@pytest.mark.parametrize("tool,said", SAID)
def test_each_everyday_phrasing_is_offered_its_tool(registry, tool, said):
    assert tool in offered_tools(registry, said, demo_context()), said
