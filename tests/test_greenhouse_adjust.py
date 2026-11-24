"""
tests.test_greenhouse_adjust
==============================

MIA setting the greenhouse node's targets (core/greenhouse_adjust.py, DEC-0185 step 4): his words read in code, the
exact change said and sent only on "yes, set it", signed so the node's own check accepts it (homestead's
core/command_auth.verify, loaded on its own: MIA never imports the node's packages), the outcome read back from the
node's export, and nothing sent without the node's key or outside his network.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from core import greenhouse_adjust as ga
from core import greenhouse_link as gl
from core import greenhouse_provision as gp
from core.actions import ACTION_TYPES, ActionError

NODE_AUTH = Path(__file__).resolve().parent.parent / "homestead" / "core" / "command_auth.py"


def _node_auth():
    """The node's own signature check, loaded from its file alone (stdlib only)."""
    spec = importlib.util.spec_from_file_location("node_command_auth", NODE_AUTH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state(ph_min=6.6, recent=()):
    """A node export with one cell and MIA's directions section."""
    return {"cells": [{"id": 1, "name": "Pilot", "readings": []}],
            "mia_directions": {"targets": {"1": {"ph_target_min": ph_min, "ph_target_max": 7.2,
                                                 "ec_target_min": 800, "ec_target_max": 1400}},
                               "recent": list(recent)}}


@pytest.fixture
def linked(tmp_path, monkeypatch):
    """A context with a greenhouse link on the home network, and this node's key on file."""
    from types import SimpleNamespace

    link = gl.GreenhouseLink(None, data_dir=tmp_path / "gh")
    link.url, link.taken_over = "http://192.168.1.50:8770", True
    monkeypatch.setattr(gp, "COMMAND_KEY", tmp_path / ".keys" / "greenhouse_command_key")
    monkeypatch.setattr(gl, "own_node", lambda url: url.startswith("http://192.168."))
    context = SimpleNamespace(greenhouse_link=link, config=None, profiles=None)
    return context, link


def test_his_words_become_one_parameter_and_value():
    """pH or EC, minimum or maximum in his words, a value; anything else isn't one."""
    assert ga.parse("set the greenhouse pH minimum to 6.4") == ("ph_target_min", 6.4)
    assert ga.parse("lower the greenhouse's EC ceiling to 1600") == ("ec_target_max", 1600.0)
    assert ga.parse("raise the pH floor in the greenhouse to 6.8") == ("ph_target_min", 6.8)
    assert ga.parse("what's the greenhouse pH?") is None
    assert ga.parse("set the greenhouse pump to 1") is None


def test_the_change_is_said_then_sent_on_yes_signed_so_the_node_accepts_it(linked):
    """"set ... to 6.4" says the exact change and sends nothing; "yes, set it" sends one direction the node's own
    check verifies, believing the node's current value, and says what it became (waiting for his Approve)."""
    context, link = linked
    key = gp.command_key("192.168.1.50")
    node = _node_auth()
    sent, db = [], sqlite3.connect(":memory:")
    gets = iter([_state(), _state(), _state(recent=[{"id": 7, "outcome": "waiting for approval"}])])

    def get(url):
        """The node's export, read fresh each time."""
        return json.dumps(next(gets)).encode()

    def post(url, body, headers):
        """The node's door: its own signature check, then a staged answer."""
        ok, why = node.verify(db, key, headers, body)
        sent.append((url, json.loads(body), ok, why))
        return (200, {"state": "staged", "command_id": 7}) if ok else (401, {"state": "refused"})

    said = ga.reply(context, "set the greenhouse pH minimum to 6.4", get=get)
    assert "from 6.6 to 6.4" in said and "yes, set it" in said and sent == []
    answer = ga.reply(context, "yes, set it", post=post, get=get)
    [(url, body, ok, why)] = sent
    assert url == "http://192.168.1.50:8770/mia/command" and ok, why
    assert body["param_name"] == "ph_target_min" and body["value"] == 6.4 and body["believed_current"] == 6.6
    assert "holding it for your Approve" in answer


def test_outside_its_limits_no_key_or_off_his_network_nothing_is_sent(linked, monkeypatch):
    """A pH of 4 is refused before anything is read; with no key for this node, nothing is sent; an address off his
    network is never posted to."""
    context, link = linked
    get = lambda url: json.dumps(_state()).encode()  # noqa: E731
    with pytest.raises(ActionError, match="limits"):
        ga.plan(context, "ph_target_min", 4.0, get=get)
    p = ga.plan(context, "ph_target_min", 6.4, get=get)
    posted = []
    with pytest.raises(ActionError, match="key"):
        ga.send(context, p, post=lambda *a: posted.append(a) or (200, {}), get=get)
    gp.command_key("192.168.1.50")
    monkeypatch.setattr(gl, "own_node", lambda url: False)
    with pytest.raises(ActionError, match="own network"):
        ga.send(context, p, post=lambda *a: posted.append(a) or (200, {}), get=get)
    assert posted == []


def test_the_action_card_reads_the_node_fresh_and_a_refusal_is_said(linked):
    """greenhouse.adjust's card says the exact change from the node's current value; a node refusal is said with
    its reason, not as done."""
    context, link = linked
    gp.command_key("192.168.1.50")
    from unittest.mock import patch

    get = lambda url: json.dumps(_state()).encode()  # noqa: E731
    with patch.object(gl, "_get", get):
        card = ACTION_TYPES["greenhouse.adjust"].describe(context, {"param": "ec_target_max", "value": 1600})
        assert "EC maximum on Pilot from 1400 to 1600" in card
        p = ga.plan(context, "ec_target_max", 1600)
        said = ga.send(context, p, post=lambda *a: (200, {"state": "refused", "reason": "ec_target_max changed less "
                                                                                       "than 60 minutes ago"}))
    assert said.startswith("The node refused") and "60 minutes" in said


def test_the_page_card_shows_the_targets_and_outcomes_from_the_last_read(linked):
    """node_card reads only the last state (no network): the cell's targets in words, the latest outcomes."""
    context, link = linked
    link.state = _state(recent=[{"param_name": "ph_target_min", "value": 6.4, "outcome": "refused",
                                 "reason": "stale", "received_at": "2026-11-24T12:00:00"}])
    card = ga.node_card(context)
    assert card["linked"] and card["cells"][0]["name"] == "Pilot"
    assert card["recent"][0] == {"param": "pH minimum", "value": 6.4, "outcome": "refused", "reason": "stale",
                                 "when": "2026-11-24T12:00"}
