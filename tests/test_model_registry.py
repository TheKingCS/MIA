"""MIA about herself (core/model_registry.py): "What AI model are you
using?" answered from the runtime, saying where each fact came from,
never from the model's guess."""

from types import SimpleNamespace

import pytest

import core.model_registry as registry
from core.home_link import HOME_PC, PHONE, THIS_COMPUTER
from core.llm_manager import OllamaBackend, OpenAIBackend

SHOW = {"details": {"family": "qwen2", "parameter_size": "14.8B", "quantization_level": "Q4_K_M", "format": "gguf"},
        "model_info": {"qwen2.context_length": 32768}, "capabilities": ["completion", "tools"]}
PS = {"models": [{"name": "qwen2.5:14b", "size": 15_300_000_000, "size_vram": 15_300_000_000, "context_length": 32768},
                 {"name": "llama3.2:3b", "size": 3_000_000_000, "size_vram": 3_000_000_000}]}


@pytest.fixture
def fake_ollama(monkeypatch):
    def get(url, payload=None, timeout=3.0):
        if url.endswith("/api/show"):
            return SHOW
        if url.endswith("/api/ps"):
            return PS
        if url.endswith("/api/version"):
            return {"version": "0.40.6"}
        raise OSError("no")

    monkeypatch.setattr(registry, "_get", get)


def test_ollama_facts_come_from_the_runtime(fake_ollama):
    info = registry.ollama_info("http://127.0.0.1:11434", "qwen2.5:14b")
    assert (info["family"], info["parameters"], info["quantization"]) == ("qwen2", "14.8B", "Q4_K_M")
    assert (info["loaded"], info["context"], info["on_gpu"], info["version"]) == (True, 32768, 1.0, "0.40.6")
    assert info["others_loaded"] == ["llama3.2:3b"] and info["source"] == "the Ollama runtime"
    said = registry.describe({"where": THIS_COMPUTER, "now": info})
    assert said.startswith("Right now I'm answering with qwen2.5:14b (qwen2 family, 14.8B parameters, Q4_K_M "
                           "quantization), running in Ollama 0.40.6, on this computer.")
    assert "32,768-token context" in said and "all on the graphics card" in said and "tool calling" in said
    assert said.endswith("(Checked just now with the Ollama runtime.)")


def test_unreachable_runtimes_say_so(monkeypatch):
    def down(url, payload=None, timeout=3.0):
        raise OSError("refused")

    monkeypatch.setattr(registry, "_get", down)
    assert registry.ollama_info("http://x", "m") == {}
    phone = registry.llamacpp_info("http://127.0.0.1:8080/v1", "qwen2.5-1.5b")
    assert phone == {"runtime": "llama.cpp", "model": "qwen2.5-1.5b", "loaded": None, "source": "MIA's settings"}
    context = SimpleNamespace(llm=SimpleNamespace(backend=OllamaBackend("http://x", "qwen2.5:14b", "-1"), home=None),
                              config=SimpleNamespace(get=lambda k, d=None: d))
    info = registry.assistant_info(context)
    assert info["where"] == THIS_COMPUTER and info["now"]["problem"] == "Ollama isn't answering"
    assert "from my settings, not checked" in registry.describe(info)


def test_the_phone_names_the_home_computers_model_and_its_own_fallback(monkeypatch):
    import core.home_link as home_link

    monkeypatch.setattr(registry, "_get", lambda url, payload=None, timeout=3.0: {
        "model_path": "/data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf", "default_generation_settings": {"n_ctx": 8192}})
    pc = {"model": "qwen2.5:14b", "details": {"runtime": "Ollama", "model": "qwen2.5:14b", "parameters": "14.8B",
                                              "source": "the Ollama runtime"}}
    monkeypatch.setattr(home_link, "_request", lambda url, payload, timeout, token="": pc)
    home = SimpleNamespace(url="https://pc.example.ts.net", token="t")
    llm = SimpleNamespace(backend=OpenAIBackend("http://127.0.0.1:8080/v1", "qwen2.5-1.5b"), home=home,
                          home_reach=SimpleNamespace(up=lambda: True))
    context = SimpleNamespace(llm=llm, config=SimpleNamespace(get=lambda k, d=None: d))
    info = registry.assistant_info(context)
    assert info["where"] == HOME_PC and info["fallback"]["context"] == 8192
    said = registry.describe(info)
    assert "qwen2.5:14b" in said and "on your home computer" in said
    assert "this phone's own qwen2.5-1.5b takes over" in said

    llm.home_reach = SimpleNamespace(up=lambda: False)
    info = registry.assistant_info(context)
    assert info["where"] == PHONE and info["home_unreachable"]
    assert "isn't reachable right now" in registry.describe(info)


def test_the_question_reaches_the_tool_and_mower_models_dont():
    from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools

    r = build_desktop_registry()
    for q in ("What AI model are you using?", "Which model are you running on?", "What LLM does MIA use?"):
        assert r.named_action(q, offered_tools(r, q, demo_context())) == "get_model_info", q
    assert "get_model_info" not in offered_tools(r, "What model of mower do I have?", demo_context())
    assert r._actions["get_model_info"].parameters["required"] == []  # a plain, argument-free tool


def test_mia_answers_it_in_code_without_the_model():
    from tests.assistant_registry import build_desktop_registry

    r = build_desktop_registry()
    assert r.direct_lookup("What AI model are you using?").name == "get_model_info"
    assert r.direct_lookup("What model of mower do I have?") is None
