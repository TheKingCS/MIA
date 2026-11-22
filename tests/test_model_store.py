"""
tests.test_model_store
========================

REQ-HW-014 (FW-12): MIA's models are removed and fetched again through the model server by name, never as files, so
his records never share a deletion path with them; the model she answers with can't be removed; only a model she
knows can be fetched; both need his yes on a card, by voice too.
"""
import json
from types import SimpleNamespace

import pytest

from core import model_store
from core.actions import ACTION_TYPES, ActionError


class _Config:
    """A config that keeps what it's given."""

    def __init__(self, **values):
        """These values."""
        self.values = dict(values)

    def get(self, key, default=None):
        """A value, or the default."""
        return self.values.get(key, default)

    def set(self, key, value):
        """Keeps a value."""
        self.values[key] = value

    def save(self):
        """Nothing to write."""


@pytest.fixture
def server(monkeypatch):
    """A pretend model server: its models, and every request it got."""
    state = {"models": [{"name": "qwen2.5:14b", "size": 9e9}, {"name": "qwen2.5:7b", "size": 4.7e9}], "asked": []}

    def call(context, path, payload, method="GET", timeout=10.0):
        """Answers like Ollama's API."""
        state["asked"].append((method, path, payload))
        if path == "/api/tags":
            return {"models": state["models"]}
        if path == "/api/delete":
            state["models"] = [m for m in state["models"] if m["name"] != payload["model"]]
        if path == "/api/pull":
            state["models"].append({"name": payload["model"], "size": 1e9})
        return {}

    monkeypatch.setattr(model_store, "_call", call)
    return state


def _context(**config):
    """A context whose chosen model is qwen2.5:14b."""
    return SimpleNamespace(config=_Config(**{"llm.model": "qwen2.5:14b", **config}), notifications=None)


def test_a_model_is_removed_through_the_server_by_name_and_can_be_fetched_again(server, tmp_path, monkeypatch):
    """Removal is one API call, never a file deleted; the name is kept, so Fetch Again offers it, and it comes back."""
    import shutil
    import os

    monkeypatch.setattr(os, "remove", lambda *a, **k: pytest.fail("a file was deleted"))
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: pytest.fail("a folder was deleted"))
    context = _context()
    assert "Removed qwen2.5:7b" in model_store.remove(context, "qwen2.5:7b")
    assert ("DELETE", "/api/delete", {"model": "qwen2.5:7b"}) in server["asked"]
    assert "qwen2.5:7b" in model_store.page(context)["fetchable"]
    model_store.fetch(context, "qwen2.5:7b", run_now=True)
    assert any(m["name"] == "qwen2.5:7b" for m in server["models"]) and model_store._fetching["qwen2.5:7b"] == "fetched"


def test_the_model_she_answers_with_cant_be_removed_and_only_a_known_model_is_fetched(server):
    """Refused: her own model, one not installed, a name that isn't a name; fetching a stranger's model."""
    context = _context()
    for name in ("qwen2.5:14b", "nothing:1b", "../../data"):
        with pytest.raises(ActionError):
            model_store.remove(context, name)
    with pytest.raises(ActionError):
        model_store.fetch(context, "someone-elses/huge-model:70b")
    assert not [a for a in server["asked"] if a[0] == "DELETE"]


def test_both_need_his_yes_and_reach_the_device_not_his_records():
    """act_with_approval on Settings, as are the two voice tools; declared as reaching the device and compensable."""
    from pathlib import Path

    from core.action_effects import effect_of

    manifest = json.loads((Path(__file__).resolve().parent.parent / "apps" / "settings" / "manifest.json")
                          .read_text(encoding="utf-8"))["capabilities"]["tiers"]
    for name in ("model.remove", "model.fetch", "remove_ai_model", "fetch_ai_model"):
        assert manifest[name] == "act_with_approval", name
    assert effect_of("model.remove") == ("device", "compensable") and "model.fetch" in ACTION_TYPES


def test_by_voice_it_puts_up_a_card_never_removes_on_its_own(server):
    """The tool proposes; nothing is removed until he approves."""
    from core.actions import ActionCenter
    from core.assistant_desktop_actions import _model_card

    context = _context()
    context.actions = ActionCenter()
    said = _model_card("model.remove")(context, {"name": "qwen2.5:7b"})
    assert "waiting for your yes" in said and not [a for a in server["asked"] if a[0] == "DELETE"]
