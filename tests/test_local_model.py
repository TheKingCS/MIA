"""
The phone's own model (core/local_model.py, 2026-10-07, DEC-0019):
downloading (and carrying on after a break), starting llama.cpp's server
and pointing Talk at it, running the test, and starting the same model
again after MIA restarts. A small Python script stands in for
llama-server, and a local HTTP server for Hugging Face.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.local_model as local_model
from core.config_manager import ConfigManager
from core.llm_manager import LLMManager, OpenAIBackend

BLOB = bytes(range(256)) * 12_000  # about 3 MB


class _Hub(BaseHTTPRequestHandler):
    ranges: list = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        start = 0
        if self.headers.get("Range"):
            type(self).ranges.append(self.headers["Range"])
            start = int(self.headers["Range"].split("=")[1].rstrip("-"))
            self.send_response(206)
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(BLOB) - start))
        self.end_headers()
        self.wfile.write(BLOB[start:])


FAKE_SERVER = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
port = int(sys.argv[sys.argv.index("--port") + 1])
assert "--jinja" in sys.argv and sys.argv[sys.argv.index("-np") + 1] == "1"
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        tools = body.get("tools") or []
        calls = [{"type": "function", "function": {"name": tools[0]["function"]["name"], "arguments": "{}"}}] if tools else []
        reply = {"choices": [{"message": {"content": "" if calls else "Hello there.", "tool_calls": calls}}],
                 "timings": {"prompt_n": 100, "prompt_ms": 1000.0, "predicted_n": 5, "predicted_ms": 500.0}}
        data = json.dumps(reply).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
HTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(check, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def hub():
    server = HTTPServer(("127.0.0.1", 0), _Hub)
    _Hub.ranges = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/model.gguf"
    server.shutdown()


@pytest.fixture
def phone(tmp_path, monkeypatch, hub):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    model = local_model.LocalModel("tiny", "Tiny", "A stand-in.", "tiny.gguf", hub, 3)
    monkeypatch.setattr(local_model, "MODELS", (model,))
    monkeypatch.setattr(local_model, "MODELS_BY_ID", {"tiny": model})
    script = tmp_path / "llama-server"
    script.write_text(f"#!{sys.executable}\n" + FAKE_SERVER)
    script.chmod(0o755)
    context = SimpleNamespace(config=ConfigManager())
    context.llm = LLMManager(context)
    models = local_model.LocalModels(context, str(script), data_dir=tmp_path / "data")
    models.port = _free_port()
    yield models
    models.stop(forget=False)


def test_the_server_starts_local_only_with_tools_on():
    args = local_model.server_args("/bin/llama", "/m.gguf", port=8790, threads=4)
    assert args[:3] == ["/bin/llama", "-m", "/m.gguf"]
    assert args[args.index("--host") + 1] == "127.0.0.1" and "--jinja" in args
    assert args[args.index("-np") + 1] == "1" and args[args.index("-c") + 1] == "8192"


def test_without_the_server_program_nothing_can_start(tmp_path):
    models = local_model.LocalModels(SimpleNamespace(config=None), None, data_dir=tmp_path)
    status = models.status()
    assert status["available"] is False and len(status["models"]) == len(local_model.MODELS)
    with pytest.raises(ValueError):
        models.start(local_model.MODELS[0].model_id)


def test_download_carries_on_after_a_break(phone):
    phone.folder.mkdir(parents=True)
    (phone.folder / "tiny.part").write_bytes(BLOB[:1_000_000])
    assert phone.status()["models"][0]["partial_mb"] == 1
    phone.download("tiny")
    assert _wait(lambda: phone.status()["download"].get("finished"))
    assert phone.status()["download"]["error"] == ""
    assert (phone.folder / "tiny.gguf").read_bytes() == BLOB and _Hub.ranges == ["bytes=1000000-"]
    assert phone.status()["models"][0]["downloaded"] is True
    with pytest.raises(ValueError):
        phone.download("nope")


def test_start_points_talk_at_the_phones_model_and_the_test_runs(phone):
    with pytest.raises(ValueError, match="Download"):
        phone.start("tiny")
    phone.download("tiny")
    assert _wait(lambda: phone.status()["download"].get("finished"))
    phone.start("tiny")
    assert _wait(lambda: phone.status()["server"]["state"] in ("ready", "error"))
    assert phone.status()["server"]["state"] == "ready", phone.status()["server"]
    assert isinstance(phone.context.llm.backend, OpenAIBackend)
    assert phone.context.llm.chat_with_tools([{"role": "user", "content": "hi"}], []).content == "Hello there."
    assert phone.context.config.get("phone.model_id") == "tiny"

    phone.run_test(3)
    assert _wait(lambda: phone.status()["run"].get("finished"))
    results = phone.status()["models"][0]["results"]
    assert results["done"] == 3 and results["model_id"] == "tiny" and results["read_per_second"] == 100.0
    assert json.loads((phone.folder / "test_tiny.json").read_text())["total"] == 3


def test_mia_starts_the_same_model_again_and_stop_forgets_it(phone):
    phone.download("tiny")
    assert _wait(lambda: phone.status()["download"].get("finished"))
    phone.start("tiny")
    assert _wait(lambda: phone.status()["server"]["state"] == "ready")
    phone.stop(forget=False)  # MIA closing
    again = local_model.LocalModels(phone.context, phone.binary, data_dir=phone.folder.parent)
    again.port = phone.port
    again.resume()
    assert _wait(lambda: again.status()["server"]["state"] == "ready")
    again.stop()
    assert again.status()["server"]["state"] == "stopped" and phone.context.config.get("phone.model_id") is None
    phone.delete("tiny")
    assert not (phone.folder / "tiny.gguf").exists()


def test_threads_use_a_phones_fast_cores():
    assert local_model.threads_for(8) == 4 and local_model.threads_for(12) == 4
    assert local_model.threads_for(4) == 4 and local_model.threads_for(2) == 2 and local_model.threads_for(1) == 1
