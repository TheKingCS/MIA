"""
tests.test_search_manager
============================

Unit tests for core.search_manager — no persisted file at all, so no
isolation fixture is needed here (unlike most core/ managers).
"""

from __future__ import annotations

import pytest

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.search_manager import SearchManager, SearchResult


def _make_manager() -> SearchManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return SearchManager(context)


def _result(title="Result", source="test") -> SearchResult:
    return SearchResult(title=title, description="", source=source, action_type="open_module", action_target="notes")


def test_search_with_no_providers_registered_returns_empty():
    manager = _make_manager()
    assert manager.search("anything") == []


def test_search_blank_query_returns_empty_without_calling_providers():
    manager = _make_manager()
    called = []
    manager.register_provider("test", lambda q: called.append(q) or [_result()])
    assert manager.search("") == []
    assert manager.search("   ") == []
    assert called == []


def test_search_strips_query_before_passing_to_providers():
    manager = _make_manager()
    received = []

    def provider(query):
        received.append(query)
        return []

    manager.register_provider("test", provider)
    manager.search("  hello  ")
    assert received == ["hello"]


def test_search_returns_a_single_providers_results():
    manager = _make_manager()
    result = _result(title="Notes match")
    manager.register_provider("notes", lambda q: [result])
    assert manager.search("query") == [result]


def test_search_combines_results_from_multiple_providers():
    manager = _make_manager()
    result_a = _result(title="A", source="modules")
    result_b = _result(title="B", source="profiles")
    manager.register_provider("modules", lambda q: [result_a])
    manager.register_provider("profiles", lambda q: [result_b])
    results = manager.search("query")
    assert result_a in results
    assert result_b in results
    assert len(results) == 2


def test_search_skips_a_provider_that_raises_but_keeps_others(caplog):
    manager = _make_manager()

    def broken_provider(query):
        raise RuntimeError("boom")

    good_result = _result(title="Still works")
    manager.register_provider("broken", broken_provider)
    manager.register_provider("good", lambda q: [good_result])

    results = manager.search("query")

    assert results == [good_result]


def test_register_provider_with_same_name_overwrites():
    manager = _make_manager()
    manager.register_provider("test", lambda q: [_result(title="First")])
    manager.register_provider("test", lambda q: [_result(title="Second")])
    results = manager.search("query")
    assert len(results) == 1
    assert results[0].title == "Second"
