"""
core.model_registry
=====================

Which AI model MIA is running, asked of the runtime itself (2026-10-21,
the intelligence spec's first slice: "What AI model are you using?" was
answered with "I don't have that kind of technical information").

Never from a model's name or a hardcoded list: each fact says where it
came from.
- **Ollama** (the computer): `/api/show` (family, parameters,
  quantization, what it supports) and `/api/ps` (loaded or not, the
  context it runs with, how much sits on the graphics card), plus
  `/api/version`. `source` "the Ollama runtime".
- **llama.cpp on the phone**: its `/props` (the model file, the context
  it runs with) when it answers; else the configured name, `source`
  "MIA's settings".
- **The home computer from the phone**: the computer's own
  `/api/model/info` (server/app.py), which is this module's `runtime_info`
  run there.

`runtime_info()` gathers it; `describe()` says it in plain words; the
Assistant's `get_model_info` tool answers with it, in code, so the model
can't make it up.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

_TIMEOUT = 3.0


def _get(url: str, payload: Optional[dict] = None, timeout: float = _TIMEOUT) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (a local runtime)
        return json.loads(response.read().decode("utf-8") or "{}")


def ollama_info(base_url: str, model: str, timeout: float = _TIMEOUT) -> dict:
    """What Ollama says about `model`: details from /api/show, whether it's
    loaded (and how) from /api/ps, the server's version. {} if it can't be
    reached."""
    base = base_url.rstrip("/")
    try:
        shown = _get(f"{base}/api/show", {"model": model}, timeout)
    except (urllib.error.URLError, OSError, ValueError):
        return {}
    details = shown.get("details") or {}
    trained = next((v for k, v in (shown.get("model_info") or {}).items() if k.endswith(".context_length")), None)
    info = {"runtime": "Ollama", "model": model, "family": details.get("family") or "",
            "parameters": details.get("parameter_size") or "", "quantization": details.get("quantization_level") or "",
            "format": details.get("format") or "", "capabilities": list(shown.get("capabilities") or []),
            "trained_context": trained, "loaded": False, "context": None, "on_gpu": None, "size_gb": None,
            "source": "the Ollama runtime"}
    try:
        running = _get(f"{base}/api/ps", None, timeout).get("models") or []
        mine = next((m for m in running if m.get("name") == model or m.get("model") == model), None)
        if mine is not None:
            size, vram = float(mine.get("size") or 0), float(mine.get("size_vram") or 0)
            info.update(loaded=True, context=mine.get("context_length"), size_gb=round(size / 1e9, 1) if size else None,
                        on_gpu=round(vram / size, 2) if size else None)
        info["others_loaded"] = [m.get("name") for m in running if m is not mine]
        info["version"] = _get(f"{base}/api/version", None, timeout).get("version", "")
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return info


def llamacpp_info(base_url: str, model: str, timeout: float = _TIMEOUT) -> dict:
    """What the phone's llama.cpp server says about itself (/props), else
    just the configured name."""
    base = base_url.rstrip("/")
    for root in (base[:-3] if base.endswith("/v1") else base, base):
        try:
            props = _get(f"{root}/props", None, timeout)
        except (urllib.error.URLError, OSError, ValueError):
            continue
        path = str(props.get("model_path") or "")
        settings = props.get("default_generation_settings") or {}
        return {"runtime": "llama.cpp", "model": model or path.rsplit("/", 1)[-1], "file": path.rsplit("/", 1)[-1],
                "context": settings.get("n_ctx") or props.get("n_ctx"), "loaded": True, "source": "the llama.cpp runtime"}
    return {"runtime": "llama.cpp", "model": model, "loaded": None, "source": "MIA's settings"}


def runtime_info(context) -> dict:
    """This device's own model, from its runtime (what /api/model/info serves)."""
    from core.llm_manager import OllamaBackend, OpenAIBackend

    llm = getattr(context, "llm", None)
    backend = getattr(llm, "backend", None) if llm is not None else None
    model = getattr(backend, "_model", "") or (context.config.get("llm.model", "") if getattr(context, "config", None) else "")
    if isinstance(backend, OllamaBackend):
        found = ollama_info(backend._base_url, model)
        return found or {"runtime": "Ollama", "model": model, "loaded": None, "source": "MIA's settings",
                         "problem": "Ollama isn't answering"}
    if isinstance(backend, OpenAIBackend):
        return llamacpp_info(backend._base_url, model)
    return {"runtime": "", "model": model, "loaded": None, "source": "MIA's settings"}


def assistant_info(context) -> dict:
    """Who answers the Assistant right now: the home computer's model
    (asked of the computer) when this phone is linked and it's reachable,
    else this device's own; plus the fallback."""
    from core.home_link import HOME_PC, PHONE, THIS_COMPUTER

    llm = getattr(context, "llm", None)
    here = runtime_info(context)
    home = getattr(llm, "home", None) if llm is not None else None
    if home is not None:
        reach = getattr(llm, "home_reach", None)
        if reach is None or reach.up():
            try:
                from core.home_link import _request

                pc = _request(f"{home.url}/api/model/info", None, _TIMEOUT, home.token)
                details = pc.get("details") or {"model": pc.get("model", ""), "source": "the home computer"}
                return {"where": HOME_PC, "now": details, "fallback": {**here, "where": PHONE}}
            except (OSError, ValueError):
                pass
        return {"where": PHONE, "now": here, "fallback": None, "home_unreachable": True}
    from core.llm_manager import OpenAIBackend

    where = PHONE if isinstance(getattr(llm, "backend", None), OpenAIBackend) else THIS_COMPUTER
    return {"where": where, "now": here, "fallback": None}


def _one(info: dict) -> str:
    name = info.get("model") or "an unnamed model"
    bits = [b for b in (info.get("family") and f"{info['family']} family", info.get("parameters") and
                        f"{info['parameters']} parameters", info.get("quantization") and f"{info['quantization']} quantization")
            if b]
    text = name + (f" ({', '.join(bits)})" if bits else "")
    if info.get("runtime"):
        text += f", running in {info['runtime']}" + (f" {info['version']}" if info.get("version") else "")
    return text


def describe(info: dict) -> str:
    """Pure logic. assistant_info() in plain words, saying where each fact came from."""
    from core.home_link import HOME_PC, PHONE

    now = info.get("now") or {}
    where = {HOME_PC: "on your home computer", PHONE: "on this phone"}.get(info.get("where"), "on this computer")
    lines = [f"Right now I'm answering with {_one(now)}, {where}."]
    extra = []
    if now.get("context"):
        extra.append(f"it runs with a {int(now['context']):,}-token context")
    if now.get("on_gpu") is not None:
        extra.append("all on the graphics card" if now["on_gpu"] >= 0.99 else f"{round(now['on_gpu'] * 100)}% on the graphics card")
    if now.get("capabilities"):
        extra.append("it supports " + " and ".join("tool calling" if c == "tools" else c for c in now["capabilities"]))
    if extra:
        lines.append(extra[0][0].upper() + "; ".join(extra)[1:] + ".")
    if now.get("problem"):
        lines.append(f"({now['problem']}: that's from my settings, not checked.)")
    if info.get("fallback"):
        fb = info["fallback"]
        lines.append(f"If the computer can't be reached, this phone's own {fb.get('model') or 'model'} takes over.")
    if info.get("home_unreachable"):
        lines.append("Your home computer isn't reachable right now, so this phone's own model is answering.")
    lines.append(f"(Checked just now with {now.get('source') or 'my settings'}.)")
    return " ".join(lines)
