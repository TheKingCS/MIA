"""Connections on the web and by voice (DEC-0146): "don't bring that up" settles a connection as declined and keeps
its thing quiet past the cooldown, until it's allowed again."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.web_connections as wcn
from core.actions import ACTION_TYPES, ActionError
from core.connections import ConnectionBook

NOW = datetime(2026, 11, 8, 9, 0)


def _found(ref="project:p1", name="Chicken coop"):
    """One three-week-old project tied in by a shared word, as core.connections.find returns it."""
    return [{"ref": ref, "kind": "project", "name": name, "status": "Planning", "since": (NOW - timedelta(days=21)).date(),
             "via": "words", "through": "", "through_kind": "", "shared": ["chicken"]}]


@pytest.fixture
def ctx(tmp_path):
    """A person with one connection waiting."""
    context = SimpleNamespace(connections=ConnectionBook(data_dir=tmp_path))
    context.connections.consider(_found(), "the chicken feed is in", NOW)
    return context


def test_the_page_shows_what_was_said_and_what_it_ties_into(ctx):
    page = wcn.screen(ctx)
    [c] = page["waiting"]
    assert c["said"] == "the chicken feed is in" and c["name"] == "Chicken coop" and c["how"] == "both about chicken"
    assert c["state_word"] == "Waiting" and page["quiet"] == []


def test_declining_keeps_it_quiet_past_the_cooldown_until_allowed(ctx):
    cid = ctx.connections.items[0]["id"]
    ACTION_TYPES["connection.decline"].describe(ctx, {"connection_id": cid})
    ACTION_TYPES["connection.decline"].execute(ctx, {"connection_id": cid})
    page = wcn.screen(ctx)
    assert page["waiting"] == [] and page["recent"][0]["state"] == "declined"
    assert page["quiet"] == [{"ref": "project:p1", "name": "Chicken coop"}]
    assert ctx.connections.consider(_found(), "chicken feed again", NOW + timedelta(days=90)) is None
    ACTION_TYPES["connection.allow"].execute(ctx, {"ref": "project:p1"})
    assert ctx.connections.consider(_found(), "chicken feed again", NOW + timedelta(days=90)) is not None
    with pytest.raises(ActionError):
        ACTION_TYPES["connection.allow"].describe(ctx, {"ref": "project:p1"})
    assert ConnectionBook(data_dir=ctx.connections.data_dir).quiet == []  # kept on disk


def test_dont_bring_that_up_by_voice_takes_the_one_just_raised(ctx):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_connection_actions import register_connection_actions

    reg = AssistantActionRegistry()
    register_connection_actions(reg)
    assert "Chicken coop" in reg._actions["list_connections"].handler(ctx, {})
    ctx.connections.settle("How's the chicken coop?", NOW + timedelta(hours=3))
    assert "won't tie things" in reg._actions["dont_bring_that_up"].handler(ctx, {})
    assert "asked me not to bring up: Chicken coop" in reg._actions["list_connections"].handler(ctx, {})


def test_what_she_found_first_shows_with_where_it_came_from(tmp_path):
    context = SimpleNamespace(connections=ConnectionBook(data_dir=tmp_path))
    found = [{"line": "you've got hardware cloth on the shelf", "source": "the workshop"}, {"source": "no line, dropped"}]
    context.connections.consider(_found(), "the chicken feed is in", NOW, research=lambda f: found)
    [c] = wcn.screen(context)["waiting"]
    assert c["found"] == [{"line": "you've got hardware cloth on the shelf", "source": "the workshop"}]
