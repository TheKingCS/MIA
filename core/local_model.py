"""
core.local_model
==================

MIA's model on the phone (2026-10-07, DEC-0019, docs/PHONE_MODEL_TEST.md):
download a small open model once, run it with llama.cpp's server
(`llama-server`, built into the phone app) on 127.0.0.1, point MIA's
Talk at it, and measure whether it does MIA's job (core/model_bench.py).

Device-level, not anyone's personal data: models live in
`data/models/`, beside the engine. Only the phone app makes one
(`context.local_models`, android-phone/mia_phone.py), handing it the
path of the server it ships. Downloading, the server starting and a test
run take minutes, so each runs on its own background thread, scoped to
this module (CLAUDE.md: threads only where a long task needs one); the
screen reads `status()` while they run.

A model download is MIA's only trip outside the phone here, once, from
Hugging Face, the place these models are published. Nothing about the
person goes with it.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PORT = 8790


@dataclass(frozen=True)
class LocalModel:
    model_id: str
    name: str
    about: str
    file: str
    url: str
    size_mb: int  # about; the download reports the exact size


# Small open models that call tools, as Q4_K_M (4-bit) files. Llama 3.2
# 3B is the one MIA uses on a computer today, so it's the comparison.
MODELS: tuple[LocalModel, ...] = (
    LocalModel("qwen2.5-1.5b", "Qwen 2.5 · 1.5B", "Smallest and fastest; the one most likely to feel quick.",
               "qwen2.5-1.5b-instruct-q4_k_m.gguf",
               "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
               1120),
    LocalModel("qwen2.5-3b", "Qwen 2.5 · 3B", "Twice the size: better at picking tools, slower.",
               "qwen2.5-3b-instruct-q4_k_m.gguf",
               "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
               2100),
    LocalModel("llama3.2-3b", "Llama 3.2 · 3B", "The model MIA uses on a computer today.",
               "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
               "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
               2020),
)
MODELS_BY_ID = {m.model_id: m for m in MODELS}

QUICK, FULL = 10, 40  # cases in a quick and a full test run on the phone


def server_args(binary: str, model_path: str, port: int = PORT, threads: int = 4, context: int = 8192,
                cores: Optional[list] = None) -> list[str]:
    """Pure logic. How the phone starts llama.cpp's server: on 127.0.0.1
    only, chat templates on (`--jinja`, needed for tools), one slot with
    the whole context (MIA's longest request is about 7,000 tokens).
    `cores`: the phone's fast cores, which every thread is pinned to; a
    thread on a slow core makes every word wait for it (Zac's A54 wrote 3
    tokens a second unpinned, 2026-10-07). The memory for the conversation
    so far is kept at 8 bits instead of 16 (flash attention on), half the
    size, so a 3B model fits beside everything else on a 6 GB phone."""
    args = [binary, "-m", model_path, "--host", "127.0.0.1", "--port", str(port), "--jinja",
            "-c", str(context), "-np", "1", "-t", str(threads), "-tb", str(threads), "--no-webui",
            "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0"]
    if cores:
        mask = hex(sum(1 << c for c in cores))
        args += ["-C", mask, "-Cb", mask, "--cpu-strict", "1"]
    return args


def threads_for(cores: int) -> int:
    """Pure logic. Phones with 8 cores have 4 fast ones: use those (the
    slow ones hold the fast ones back). Smaller devices use every core."""
    return 4 if cores >= 8 else max(1, cores)


def fast_cores(cpu_dir: Path = Path("/sys/devices/system/cpu")) -> list[int]:
    """The cores faster than the phone's slowest group (Linux reports each
    core's top speed). Empty when they're all the same, or it can't tell."""
    speeds = {}
    for core in cpu_dir.glob("cpu[0-9]*"):
        try:
            speeds[int(core.name[3:])] = int((core / "cpufreq" / "cpuinfo_max_freq").read_text().strip())
        except (OSError, ValueError):
            continue
    if len(set(speeds.values())) < 2:
        return []
    slowest = min(speeds.values())
    return sorted(c for c, speed in speeds.items() if speed > slowest)


def free_memory_mb(meminfo: Path = Path("/proc/meminfo")) -> Optional[int]:
    """What the system says it could hand out now (MemAvailable)."""
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def needed_memory_mb(file_mb: int) -> int:
    """Pure logic. About what a running model takes: its file, plus the
    conversation memory and working space (measured: a 1.5B needs about
    1.6 GB, a 3B about 2.9 GB)."""
    return round(file_mb * 1.15 + 350)


EXIT_REASONS = {  # Android's ApplicationExitInfo reasons, in words
    1: "MIA closed itself", 2: "Android stopped MIA", 3: "Android closed MIA to free memory",
    4: "MIA crashed", 5: "MIA crashed (in native code)", 6: "MIA stopped responding", 9: "MIA used too much",
    10: "you closed MIA", 11: "you force-stopped MIA", 13: "MIA closed", 16: "MIA was updated",
}


def describe_exit(info: dict) -> str:
    """Pure logic. Why Android last closed MIA, in a sentence; "" when it
    was ordinary (closed by you, or an update)."""
    reason = info.get("reason")
    if not reason or reason in (10, 11, 16):
        return ""
    words = EXIT_REASONS.get(reason, "MIA closed")
    where = " while you were using it" if info.get("importance", 1000) <= 200 else " in the background"
    memory = f" (it was using {round(info['pss_kb'] / 1024)} MB)" if info.get("pss_kb") else ""
    return words + where + memory + "."


class LocalModels:
    """`context.local_models` on the phone."""

    def __init__(self, context, binary: Optional[str], data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.binary = binary
        self.port = PORT
        self.folder = Path(data_dir or _DATA_DIR) / "models"
        self._lock = threading.Lock()
        self._download: dict = {}  # model_id, done_mb, total_mb, error
        self._server: dict = {"state": "stopped"}  # state, model_id, error, load_seconds
        self._process: Optional[subprocess.Popen] = None
        self._run: dict = {}  # the test run in progress
        self._stop_run = False
        self.last_exit: dict = {}  # why Android last closed MIA (the phone app tells us)
        self.note = ""  # something to tell the person at the top of the screen

    # ------------------------------------------------------------------ what's here

    def path(self, model: LocalModel) -> Path:
        return self.folder / model.file

    def available(self) -> bool:
        return bool(self.binary) and Path(self.binary).exists()

    def results(self, model_id: str) -> Optional[dict]:
        try:
            return json.loads((self.folder / f"test_{model_id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def status(self) -> dict:
        with self._lock:
            download, server, run = dict(self._download), dict(self._server), dict(self._run)
        models = []
        for m in MODELS:
            part = self.path(m).with_suffix(".part")
            models.append({
                "id": m.model_id, "name": m.name, "about": m.about, "size_mb": m.size_mb,
                "downloaded": self.path(m).exists(),
                "partial_mb": round(part.stat().st_size / 1e6) if part.exists() else 0,
                "results": self.results(m.model_id),
            })
        if run:
            run.pop("results", None)
        for item, m in zip(models, MODELS):
            item["needs_mb"] = needed_memory_mb(m.size_mb)
        return {"available": self.available(), "models": models, "download": download, "server": server,
                "run": run, "quick": QUICK, "full": FULL, "free_mb": free_memory_mb(), "fast_cores": fast_cores(),
                "last_exit": describe_exit(self.last_exit), "note": self.note}

    # ------------------------------------------------------------------ download

    def download(self, model_id: str) -> None:
        model = MODELS_BY_ID.get(model_id)
        if model is None:
            raise ValueError("MIA doesn't know that model.")
        with self._lock:
            if self._download.get("model_id") and not self._download.get("finished"):
                raise ValueError("A download is already going.")
            self._download = {"model_id": model_id, "done_mb": 0, "total_mb": model.size_mb, "error": "",
                              "finished": False}
        threading.Thread(target=self._fetch, args=(model,), name="mia-model-download", daemon=True).start()

    def _fetch(self, model: LocalModel) -> None:
        import ssl

        try:
            import certifi  # the phone's Python has no system certificates of its own

            tls = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            tls = ssl.create_default_context()
        self.folder.mkdir(parents=True, exist_ok=True)
        part = self.path(model).with_suffix(".part")
        have = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(model.url, headers={"User-Agent": "MIA", **({"Range": f"bytes={have}-"} if have else {})})
        try:
            with urllib.request.urlopen(request, timeout=60, context=tls) as response:
                if have and response.status != 206:
                    have = 0  # the server started over
                total = have + int(response.headers.get("Content-Length") or 0)
                with self._lock:
                    self._download.update(total_mb=round(total / 1e6) or model.size_mb, done_mb=round(have / 1e6))
                with open(part, "ab" if have else "wb") as out:
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                        have += len(chunk)
                        with self._lock:
                            self._download["done_mb"] = round(have / 1e6)
            if total and have < total:
                raise OSError(f"the download stopped at {have // 1_000_000} of {total // 1_000_000} MB")
            part.replace(self.path(model))
            log.info("Downloaded %s (%d MB).", model.file, have // 1_000_000)
        except (urllib.error.URLError, OSError) as problem:
            log.warning("Model download failed: %s", problem)
            with self._lock:
                self._download["error"] = f"The download stopped ({problem}). Tap Download again to carry on."
        finally:
            with self._lock:
                self._download["finished"] = True

    def delete(self, model_id: str) -> None:
        model = MODELS_BY_ID.get(model_id)
        if model is None:
            raise ValueError("MIA doesn't know that model.")
        if self._server.get("model_id") == model_id:
            self.stop()
        for f in (self.path(model), self.path(model).with_suffix(".part"), self.folder / f"test_{model_id}.json"):
            f.unlink(missing_ok=True)

    # ------------------------------------------------------------------ the server

    def start(self, model_id: str) -> None:
        model = MODELS_BY_ID.get(model_id)
        if model is None or not self.path(model).exists():
            raise ValueError("Download that model first.")
        if not self.available():
            raise ValueError("This MIA has no model server.")
        self.stop(forget=False)
        self._remember(model_id)
        with self._lock:
            self._server = {"state": "starting", "model_id": model_id, "error": ""}
        threading.Thread(target=self._launch, args=(model,), name="mia-model-server", daemon=True).start()

    def _launch(self, model: LocalModel) -> None:
        from core.llm_manager import OpenAIBackend

        started = time.monotonic()
        self.folder.mkdir(parents=True, exist_ok=True)
        log_file = open(self.folder / "server.log", "wb")
        cores = fast_cores()
        threads = min(4, len(cores)) if cores else threads_for(os.cpu_count() or 4)
        self._loading_marker().write_text(model.model_id)  # cleared once it's up, or it failed
        try:
            self._process = subprocess.Popen(
                server_args(self.binary, str(self.path(model)), port=self.port, threads=threads, cores=cores[:threads]),
                stdout=log_file, stderr=subprocess.STDOUT)
        except OSError as problem:
            self._loading_marker().unlink(missing_ok=True)
            with self._lock:
                self._server = {"state": "error", "model_id": model.model_id, "error": f"It didn't start: {problem}"}
            return
        backend = OpenAIBackend(f"http://127.0.0.1:{self.port}", model.model_id)
        while time.monotonic() - started < 300:
            if self._process.poll() is not None:
                self._loading_marker().unlink(missing_ok=True)
                tail = (self.folder / "server.log").read_text(errors="replace")[-400:]
                with self._lock:
                    self._server = {"state": "error", "model_id": model.model_id, "error": f"It stopped: {tail}"}
                return
            if backend.is_available(2):
                break
            time.sleep(0.5)
        else:
            self._loading_marker().unlink(missing_ok=True)
            self.stop()
            with self._lock:
                self._server = {"state": "error", "model_id": model.model_id, "error": "It took too long to load."}
            return
        self._loading_marker().unlink(missing_ok=True)
        llm = getattr(self.context, "llm", None)
        if llm is not None:
            llm.use_backend(backend, timeout=300)  # Talk uses the phone's model now
        with self._lock:
            self._server = {"state": "ready", "model_id": model.model_id, "error": "",
                            "load_seconds": round(time.monotonic() - started, 1), "threads": threads,
                            "cores": cores[:threads]}
        log.info("The phone's model is up: %s.", model.model_id)

    def _remember(self, model_id: Optional[str]) -> None:
        """The model Talk uses, started again when MIA starts."""
        config = getattr(self.context, "config", None)
        if config is not None and config.get("phone.model_id") != model_id:
            config.set("phone.model_id", model_id)
            config.save()

    def _loading_marker(self) -> Path:
        return self.folder / "loading"

    def resume(self) -> None:
        """At start-up: bring back the model that was running, unless
        loading a model is what closed MIA last time (never a loop of
        crashes: the person decides whether to try again)."""
        marker = self._loading_marker()
        if marker.exists():
            model = MODELS_BY_ID.get(marker.read_text().strip())
            marker.unlink(missing_ok=True)
            self._remember(None)
            name = model.name if model else "a model"
            self.note = (f"MIA closed while loading {name} last time, so it didn't load again by itself. "
                         "It probably needs more free memory than the phone had; try the smaller model, "
                         "or close other apps first.")
            return
        model = MODELS_BY_ID.get(self.context.config.get("phone.model_id") or "")
        if model is not None and self.path(model).exists() and self.available():
            self.start(model.model_id)

    def stop(self, forget: bool = True) -> None:
        if forget:
            self._remember(None)
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        with self._lock:
            self._server = {"state": "stopped"}

    # ------------------------------------------------------------------ the test

    def run_test(self, count: int) -> None:
        from core import model_bench
        from core.llm_manager import OpenAIBackend

        with self._lock:
            if self._server.get("state") != "ready":
                raise ValueError("Start a model first.")
            if self._run and not self._run.get("finished"):
                raise ValueError("A test is already running.")
            model_id = self._server["model_id"]
            self._run = {"model_id": model_id, "total": count, "done": 0, "passed": 0, "finished": False}
        self._stop_run = False

        def go() -> None:
            def progress(summary: dict) -> None:
                with self._lock:
                    self._run.update({k: v for k, v in summary.items() if k != "results"})

            try:
                summary = model_bench.run(OpenAIBackend(f"http://127.0.0.1:{self.port}", model_id), model_bench.load_cases(),
                                          count=count, progress=progress, should_stop=lambda: self._stop_run)
                summary.update(model_id=model_id, when=time.strftime("%Y-%m-%d %H:%M"),
                               load_seconds=self._server.get("load_seconds"), threads=self._server.get("threads"))
                (self.folder / f"test_{model_id}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
            except Exception:
                log.exception("The model test failed.")
                with self._lock:
                    self._run["error"] = "The test stopped with an error."
            finally:
                with self._lock:
                    self._run["finished"] = True

        threading.Thread(target=go, name="mia-model-test", daemon=True).start()

    def cancel_test(self) -> None:
        self._stop_run = True
