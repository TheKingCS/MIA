"""
The model test (core/model_bench.py) and the llama.cpp backend
(core/llm_manager.OpenAIBackend), 2026-10-07, DEC-0019: scoring follows
the live check's rules, the frozen cases match the golden set, and the
backend speaks llama-server's chat API, tested against a tiny fake
server on 127.0.0.1.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from core import model_bench
from core.config_manager import ConfigManager
from core.llm_manager import ChatReply, LLMUnavailableError, OllamaBackend, OpenAIBackend, ToolCall, make_backend


def test_scoring_follows_the_live_checks_rules():
    destructive = {"delete_alarm"}
    assert model_bench.score({"expected": "add_alarm"}, ["add_alarm"], {}, destructive)[0]
    assert not model_bench.score({"expected": "add_alarm"}, ["add_alarm", "add_alarm"], {}, destructive)[0]
    assert not model_bench.score({"expected": "add_alarm"}, [], None, destructive)[0]
    assert model_bench.score({"expected": None}, [], None, destructive)[0]
    assert not model_bench.score({"expected": None}, ["get_today"], {}, destructive)[0]
    assert model_bench.score({"expected": "safe"}, ["get_alarms"], {}, destructive)[0]
    assert not model_bench.score({"expected": "safe"}, ["delete_alarm"], {}, destructive)[0]
    with_args = {"expected": "log_fuel", "arguments": {"asset": "mower", "gallons": 3}}
    assert model_bench.score(with_args, ["log_fuel"], {"asset": "Riding Mower", "gallons": "3"}, destructive)[0]
    assert not model_bench.score(with_args, ["log_fuel"], {"asset": "Riding Mower", "gallons": "4"}, destructive)[0]


def test_pick_spreads_over_every_area():
    cases = list(range(100))
    assert model_bench.pick(cases, 10) == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    assert model_bench.pick(cases, None) == cases and model_bench.pick(cases, 500) == cases


def test_the_frozen_cases_match_the_golden_set():
    """Regenerate with `python -m tools.make_model_bench` when this fails."""
    import tests.live_model_check as live

    bench = model_bench.load_cases()
    frozen = [(c["description"], c["prompt"], c["expected"], c["arguments"]) for c in bench["cases"]]
    golden = [(d, p, e, (a[0] if a else None)) for d, p, e, *a in live.GOLDEN_CASES]
    assert frozen == golden
    assert all(c["messages"][-1]["role"] == "user" for c in bench["cases"])
    assert sum(1 for c in bench["cases"] if c["tools"]) > len(bench["cases"]) // 2
    for case in bench["cases"]:
        if case["expected"] not in (None, "safe"):
            offered = {t["function"]["name"] for t in case["tools"]}
            assert case["expected"] in offered, case["description"]


class _FakeLlamaServer(BaseHTTPRequestHandler):
    replies: list = []
    seen: list = []

    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append((self.path, body))
        reply = type(self).replies.pop(0)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode())


@pytest.fixture
def fake():
    server = HTTPServer(("127.0.0.1", 0), _FakeLlamaServer)
    _FakeLlamaServer.replies, _FakeLlamaServer.seen = [], []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", _FakeLlamaServer
    server.shutdown()


def _choice(content="", calls=()):
    return {"choices": [{"message": {"content": content, "tool_calls": [
        {"type": "function", "function": {"name": n, "arguments": json.dumps(a)}} for n, a in calls]}}],
        "timings": {"prompt_n": 2000, "prompt_ms": 40000.0, "predicted_n": 20, "predicted_ms": 2000.0}}


def test_openai_backend_speaks_llama_servers_chat_api(fake):
    url, server = fake
    backend = OpenAIBackend(url, "local")
    assert backend.is_available(2)
    server.replies.append(_choice(calls=[("add_alarm", {"time": "07:00"})]))
    tools = [{"type": "function", "function": {"name": "add_alarm", "description": "", "parameters": {}}}]
    reply = backend.chat([{"role": "user", "content": "Wake me at 7"}], tools, 5)
    assert reply == ChatReply(content="", tool_calls=[ToolCall("add_alarm", {"time": "07:00"})])
    path, sent = server.seen[0]
    assert path == "/v1/chat/completions" and sent["tools"] == tools and sent["temperature"] == 0.0
    assert backend.last_timings["prompt_n"] == 2000
    server.replies.append({"error": {"message": "context too long"}})
    with pytest.raises(LLMUnavailableError):
        backend.chat([{"role": "user", "content": "hi"}], [], 5)
    assert not OpenAIBackend("http://127.0.0.1:9", "x").is_available(1)


def test_the_backend_follows_config(tmp_path, monkeypatch):
    import core.config_manager as config_module

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    config = ConfigManager()
    assert isinstance(make_backend(config), OllamaBackend)
    config.set("llm.backend", "openai")
    assert isinstance(make_backend(config), OpenAIBackend)


def test_run_reports_accuracy_and_speed(fake):
    url, server = fake
    bench = {"destructive": ["delete_alarm"], "cases": [
        {"description": "a", "prompt": "Wake me at 7", "expected": "add_alarm", "arguments": None,
         "messages": [{"role": "user", "content": "Wake me at 7"}], "tools": []},
        {"description": "b", "prompt": "Hi", "expected": None, "arguments": None,
         "messages": [{"role": "user", "content": "Hi"}], "tools": []},
    ]}
    server.replies += [_choice(calls=[("add_alarm", {})]), _choice(calls=[("get_today", {})])]
    seen = []
    summary = model_bench.run(OpenAIBackend(url, "local"), bench, progress=lambda s: seen.append(s["done"]))
    assert (summary["total"], summary["done"], summary["passed"]) == (2, 2, 1) and seen == [1, 2]
    assert summary["read_per_second"] == 50.0 and summary["write_per_second"] == 10.0
    assert summary["results"][1]["detail"] == "expected no tool call, got ['get_today']"
