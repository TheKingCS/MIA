"""
tests.test_service_map
========================

What MIA runs on (core/service_map.py, T-0007): each service's dependencies as derived DEPENDS_ON links, what stops
when one does (through a chain: the vision model with Ollama), what each needs, the words that name each, checks
that only look, and her answers in a turn.
"""

from types import SimpleNamespace

from core import service_map as sm


def test_every_service_s_needs_are_services_and_the_links_are_in_the_graph_s_shape():
    """No dependency points at a service that isn't listed; each is a derived DEPENDS_ON link."""
    for s in sm.SERVICES:
        assert all(n in sm.BY_ID for n in s.needs), s.id
    found = sm.links()
    assert all(l.relation == "DEPENDS_ON" and l.derived and l.source.startswith("service:") for l in found)
    assert any(l.source == "service:plaid" and l.target == "service:internet" for l in found)


def test_what_breaks_follows_the_chain_and_says_what_still_works():
    """Ollama takes the embedding and vision models with it; the internet takes bank sync, search and email; Vosk
    takes nothing else; each answer says what still works."""
    assert set(sm.depends_on("ollama")) == {"embeddings", "vision"}
    assert {"plaid", "searxng", "tailscale", "email_account"} <= set(sm.depends_on("internet"))
    assert sm.depends_on("vosk") == []
    said = sm.what_breaks("ollama")
    assert said.startswith("If Ollama (her local model) stops:") and "Still working: every record and action" in said
    assert sm.needs_of("glasses") == ["phone"] and sm.needs_of("plaid") == ["internet"]


def test_the_words_find_the_service_and_the_checks_only_look(monkeypatch):
    """"the model", "bank sync", "the glasses" name their services; a missing executable or package reads missing, a
    taken-over greenhouse reads here, a check that can't be told reads unknown."""
    assert sm.find("if the model goes down").id == "ollama" and sm.find("bank sync").id == "plaid"
    assert sm.find("the glasses").id == "glasses" and sm.find("the weather") is None
    monkeypatch.setattr(sm.shutil, "which", lambda name: None)
    monkeypatch.setattr(sm.importlib.util, "find_spec", lambda name: None)
    assert sm.status(SimpleNamespace(), sm.BY_ID["ollama"]) == sm.MISSING
    assert sm.status(SimpleNamespace(), sm.BY_ID["vosk"]) == sm.MISSING
    context = SimpleNamespace(greenhouse_link=SimpleNamespace(taken_over=True))
    assert sm.status(context, sm.BY_ID["greenhouse_node"]) == sm.HERE
    assert sm.status(SimpleNamespace(), sm.BY_ID["phone"]) == sm.UNKNOWN
    assert sm.status(SimpleNamespace(connectivity=SimpleNamespace(status="offline")), sm.BY_ID["internet"]) == sm.MISSING


def test_her_answers_in_a_turn():
    """"What breaks if Ollama stops?", "what does bank sync need?" and "what do you run on?" are answered in code;
    other words are left alone."""
    from core.assistant_turn import _service_reply

    context = SimpleNamespace(config=None)
    assert _service_reply(context, "What breaks if Ollama stops?").startswith("If Ollama")
    assert _service_reply(context, "what does bank sync need?") == "Bank sync (Plaid) needs the internet."
    assert _service_reply(context, "what does vosk need?") == "Vosk (listening) runs on its own, on this computer."
    assert _service_reply(context, "what do you run on?").startswith(("Here and ready", "Not set up"))
    assert _service_reply(context, "what breaks if I skip leg day?") is None
    assert _service_reply(context, "how's the weather") is None
