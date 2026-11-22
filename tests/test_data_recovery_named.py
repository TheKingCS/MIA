"""
tests.test_data_recovery_named
================================

REQ-FUN-221: an answer built from several stores names the parts it couldn't read, rather than leaving them out
silently: a store reset to empty at start is remembered for the run and named in her context, with the rule to say so.
"""
from types import SimpleNamespace

from core import data_recovery
from core.assistant_chat import build_user_context_block


def test_a_store_that_couldnt_be_read_is_named_in_her_context_with_the_rule_to_say_so(monkeypatch):
    """Nothing unread: no note; one reset at start: its name in words, and never answering as if empty."""
    monkeypatch.setattr(data_recovery, "_unreadable", {})
    context = SimpleNamespace(profiles=None, user_memories=None, direction=None, notifications=None)
    assert "couldn't be read" not in build_user_context_block(context)
    data_recovery.notify_data_corruption(context, "inventory_items.json")
    note = build_user_context_block(context)
    assert data_recovery.unreadable() == ["inventory_items.json"]
    assert "couldn't be read when MIA started" in note and "never answer as if they were empty" in note
