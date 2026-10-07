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


# Starting the stand-in server runs a script as a program, which only works
# where the real one runs: Linux and Android. (Windows has no llama-server.)
needs_posix = pytest.mark.skipif(sys.platform == "win32", reason="llama-server runs on the phone (Linux/Android)")


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


@needs_posix
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


@needs_posix
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


def test_pinned_to_the_fast_cores_with_a_smaller_cache():
    args = local_model.server_args("/bin/llama", "/m.gguf", threads=4, cores=[4, 5, 6, 7])
    assert args[args.index("-C") + 1] == "0xf0" and args[args.index("-Cb") + 1] == "0xf0"
    assert args[args.index("--cpu-strict") + 1] == "1" and args[args.index("-tb") + 1] == "4"
    assert args[args.index("-ctk") + 1] == "q8_0" and args[args.index("-fa") + 1] == "on"
    assert "-C" not in local_model.server_args("/bin/llama", "/m.gguf", cores=[])


def _cpus(tmp_path, speeds):
    for n, speed in enumerate(speeds):
        folder = tmp_path / f"cpu{n}" / "cpufreq"
        folder.mkdir(parents=True)
        (folder / "cpuinfo_max_freq").write_text(f"{speed}\n")
    (tmp_path / "cpufreq").mkdir()  # not a core
    return tmp_path


def test_fast_cores_are_the_ones_above_the_slowest_group(tmp_path):
    a54 = _cpus(tmp_path / "a54", [2002000] * 4 + [2400000] * 4)  # 4 small, 4 big (Exynos 1380)
    assert local_model.fast_cores(a54) == [4, 5, 6, 7]
    flagship = _cpus(tmp_path / "s", [2000000] * 3 + [2800000] * 4 + [3300000])  # small, big, prime
    assert local_model.fast_cores(flagship) == [3, 4, 5, 6, 7]
    assert local_model.fast_cores(_cpus(tmp_path / "even", [2400000] * 4)) == []
    assert local_model.fast_cores(tmp_path / "nothing") == []


def test_free_memory_and_what_a_model_needs(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:  5743000 kB\nMemFree:  300000 kB\nMemAvailable:  2097152 kB\n")
    assert local_model.free_memory_mb(meminfo) == 2048
    assert local_model.free_memory_mb(tmp_path / "missing") is None
    assert 1500 < local_model.needed_memory_mb(1120) < 1800 and 2600 < local_model.needed_memory_mb(2100) < 3000


def test_why_android_closed_mia_in_words():
    assert local_model.describe_exit({"reason": 3, "importance": 100, "pss_kb": 3_145_728}) == \
        "Android closed MIA to free memory while you were using it (it was using 3072 MB)."
    assert local_model.describe_exit({"reason": 5, "importance": 400}) == "MIA crashed (in native code) in the background."
    assert local_model.describe_exit({"reason": 10}) == "" and local_model.describe_exit({}) == ""


def test_a_model_that_closed_mia_while_loading_is_not_loaded_again(phone):
    phone.download("tiny")
    assert _wait(lambda: phone.status()["download"].get("finished"))
    phone.context.config.set("phone.model_id", "tiny")
    phone._loading_marker().write_text("tiny")  # MIA died while this was loading
    phone.resume()
    status = phone.status()
    assert status["server"]["state"] == "stopped" and "closed while loading Tiny" in status["note"]
    assert phone.context.config.get("phone.model_id") is None and not phone._loading_marker().exists()
    phone.resume()  # and the time after that, nothing is remembered: still nothing loads
    assert phone.status()["server"]["state"] == "stopped"
