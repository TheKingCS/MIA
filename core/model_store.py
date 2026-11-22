"""
core.model_store
==================

MIA's models, removable and fetched again (FW-12, REQ-HW-014, DEC-0193): "models and packs shall be removable and
re-fetchable without touching his records; his records never share a deletion path with them."

Her models live in the model server's own store (Ollama's), never among his records. Everything here goes through
that server's API by a model's name, and never deletes a file: `remove` asks Ollama to delete one model
(`/api/delete`), `fetch` asks it to download one again (`/api/pull`). So no path of his can ever be in a removal.

- `installed()`: each model the server has, its size, and whether it's the one she answers with.
- `remove()`: refused for the model she answers with (she'd have no words); a removed model's name is kept
  (`models.removed`) so it can be fetched again.
- `fetch()`: only a model she knows (the one she answers with, her fallbacks, one removed here), started in the
  background, since a download takes minutes; its outcome is told when it ends.
- `in_use()`: the models she works with (words, meaning: `llm.embed_model`, sight: `sight.model`); none of them
  can be removed.

Both are actions that need his yes (`model.remove`, `model.fetch`), on Settings and by voice (a card, never done on
her own say-so).
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

_NAME = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,80}$")
_fetching: dict = {}  # model -> "fetching", "fetched" or "failed: why" (this run)
_lock = threading.Lock()


def _base(context) -> str:
    """The model server's address (core/llm_manager.local_server_url)."""
    from core.llm_manager import local_server_url

    return local_server_url(context)


def _call(context, path: str, payload: Optional[dict], method: str = "GET", timeout: float = 10.0) -> dict:
    """One request to the model server's API; {} for an empty answer. URLError and OSError pass up."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(_base(context) + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (MIA's own model server)
        body = response.read().decode("utf-8")
    try:
        return json.loads(body or "{}")
    except ValueError:
        return {}


def chosen(context) -> str:
    """The model she answers with (`llm.model`)."""
    return str(context.config.get("llm.model", "") or "")


def _same(a: str, b: str) -> bool:
    """Pure logic. Whether two model names are one model ("qwen2.5:14b" and "qwen2.5:14b"; "llama3.2" and its ":latest")."""
    norm = lambda n: n if ":" in n else n + ":latest"  # noqa: E731
    return bool(a and b) and norm(a) == norm(b)


def known(context) -> list[str]:
    """The models she may fetch: the one she answers with, her fallbacks, and those removed here."""
    from core.llm_manager import FALLBACK_MODELS

    names = [chosen(context), *(context.config.get("llm.fallback_models", FALLBACK_MODELS) or []),
             *(context.config.get("models.removed", []) or [])]
    return list(dict.fromkeys(n for n in names if n and _NAME.match(n)))


def installed(context) -> list[dict]:
    """Each model the server has: {name, size_gb, in_use}; [] when it can't be asked."""
    try:
        models = _call(context, "/api/tags", None).get("models") or []
    except (urllib.error.URLError, OSError):
        return []
    me = chosen(context)
    return [{"name": m.get("name", ""), "size_gb": round(float(m.get("size") or 0) / 1e9, 1),
             "in_use": _same(m.get("name", ""), me)} for m in models if m.get("name")]


def page(context) -> dict:
    """Settings' section: the installed models, the ones that can be fetched again, and downloads in progress."""
    have = installed(context)
    names = {m["name"] for m in have}
    return {"installed": have, "fetchable": [n for n in known(context) if not any(_same(n, h) for h in names)],
            "fetching": dict(_fetching)}


def _check_remove(context, name: str) -> str:
    """The model to remove, checked: installed, and not one in use (`in_use`: words, meaning or sight)."""
    name = str(name or "").strip()
    if not _NAME.match(name) or not any(_same(name, m["name"]) for m in installed(context)):
        raise ActionError("That isn't one of the models on this computer.")
    if _same(name, chosen(context)):
        raise ActionError("That's the model I answer with: choose another first, or I'd have no words.")
    if any(_same(name, used) for used in in_use(context)):
        raise ActionError("I use that model for finding things by meaning or for looking at pictures: removing it "
                          "would quietly break those.")
    return name


def in_use(context) -> list[str]:
    """The models her other work needs besides the one she answers with: the embedding model (core/meaning.py) and
    the vision model (core/sight.py)."""
    from core import meaning, sight

    config = context.config
    return [m for m in (config.get("llm.embed_model", meaning._DEFAULT_MODEL), config.get("sight.model", sight.MODEL))
            if m]


def remove(context, name: str) -> str:
    """Removes one model through the server (never a file); its name is kept so it can be fetched again."""
    name = _check_remove(context, name)
    try:
        _call(context, "/api/delete", {"model": name}, method="DELETE")
    except (urllib.error.URLError, OSError) as problem:
        raise ActionError(f"The model server didn't remove it: {problem}") from None
    removed = [n for n in (context.config.get("models.removed", []) or []) if n != name] + [name]
    context.config.set("models.removed", removed[-20:])
    context.config.save()
    return f"Removed {name}. It can be fetched again from Settings."


def _check_fetch(context, name: str) -> str:
    """The model to fetch, checked: one she knows, and not already downloading."""
    name = str(name or "").strip()
    if name not in known(context):
        raise ActionError("I only fetch the models I use: the one I answer with, my fallbacks, or one removed here.")
    if _fetching.get(name) == "fetching":
        raise ActionError(f"{name} is already being fetched.")
    return name


def fetch(context, name: str, run_now: bool = False) -> str:
    """Starts downloading one model again, in the background (a download takes minutes); its end is told."""
    name = _check_fetch(context, name)

    def work() -> None:
        """The download, then the note."""
        try:
            _call(context, "/api/pull", {"model": name, "stream": False}, method="POST", timeout=6 * 3600)
            outcome = "fetched"
        except (urllib.error.URLError, OSError) as problem:
            outcome = f"failed: {str(problem)[:120]}"
        with _lock:
            _fetching[name] = outcome
        notes = getattr(context, "notifications", None)
        if notes is not None:
            notes.notify(f"Model {outcome.split(':')[0]}", f"{name}: {outcome}.", source="models")

    with _lock:
        _fetching[name] = "fetching"
    if run_now:
        work()
    else:
        threading.Thread(target=work, name=f"fetch {name}", daemon=True).start()
    return f"Fetching {name}; I'll tell you when it's done."


MODEL_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("model.remove", "Remove it", {"name": "a model's name, as Settings lists it"},
               lambda c, p: f"Remove the model {_check_remove(c, p.get('name'))} from this computer (it can be "
                            "fetched again; none of your records are touched)",
               lambda c, p: remove(c, p.get("name"))),
    ActionType("model.fetch", "Fetch it", {"name": "a model's name"},
               lambda c, p: f"Download the model {_check_fetch(c, p.get('name'))} again (several gigabytes)",
               lambda c, p: fetch(c, p.get("name"))),
)}
ACTION_TYPES.update(MODEL_ACTIONS)
