"""
core.meaning
==============

Comparing what someone said with example sentences by meaning, not by
the words they share (DEC-0052; docs/TOOL_CALLING_RESEARCH.md R2). A
small local embedding model on the home computer's Ollama
(`llm.embed_model`, default nomic-embed-text) turns each sentence into a
vector; the nearest example wins. Measured 2026-10-30 on Zac's benchmark:
questions matched to *example questions* this way reached the right
question plan 23 times in 25; matched to tool descriptions they didn't,
so this is only ever used against examples.

Never required: with no embedding model (the phone, or Ollama down)
`nearest()` returns None and the caller falls back to words. The
examples' vectors are kept on disk (`data/cache/meaning.json`), so only
the question is embedded on each turn (about 20 ms).
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "cache" / "meaning.json"
_DEFAULT_MODEL = "nomic-embed-text"
_TIMEOUT = 20
_memory: dict[str, list[float]] = {}
_loaded = False
_down_until = 0.0  # after a failure, don't try again for a minute


def _base_url(context) -> Optional[str]:
    """This computer's Ollama, when it's what answers (never the phone's model)."""
    from core.llm_manager import OllamaBackend

    llm = getattr(context, "llm", None)
    backend = getattr(llm, "_backend", None)
    if not isinstance(backend, OllamaBackend) or getattr(llm, "home", None) is not None:
        return None
    return getattr(backend, "_base_url", None)


def _model(context) -> str:
    config = getattr(context, "config", None)
    return (config.get("llm.embed_model", _DEFAULT_MODEL) if config is not None else _DEFAULT_MODEL) or _DEFAULT_MODEL


def _key(model: str, kind: str, text: str) -> str:
    return hashlib.sha1(f"{model}|{kind}|{text}".encode("utf-8")).hexdigest()


def _load_cache() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        _memory.update(json.loads(_CACHE_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass


def _save_cache() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(_memory), encoding="utf-8")
    except OSError:
        log.warning("Couldn't save the meaning cache")


def embed(context, texts: list[str], kind: str = "query") -> Optional[list[list[float]]]:
    """Vectors for `texts`, or None when there's no embedding model.
    `kind` is "query" for what someone said and "example" for the
    examples (the model is told which, as it expects)."""
    import time

    global _down_until
    url = _base_url(context)
    if url is None or time.monotonic() < _down_until:
        return None
    model = _model(context)
    _load_cache()
    prefix = "search_query: " if model.startswith("nomic") else ""
    keys = [_key(model, "q", t) for t in texts]  # both kinds are embedded as queries: question to question
    todo = [t for t, k in zip(texts, keys) if k not in _memory]
    if todo:
        body = json.dumps({"model": model, "input": [prefix + t for t in todo]}).encode("utf-8")
        request = urllib.request.Request(f"{url}/api/embed", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                vectors = json.loads(response.read().decode("utf-8")).get("embeddings") or []
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.info("No embedding model (%s); matching by words instead.", exc)
            _down_until = time.monotonic() + 60
            return None
        if len(vectors) != len(todo):
            return None
        for t, v in zip(todo, vectors):
            _memory[_key(model, "q", t)] = v
        if kind == "example":
            _save_cache()
    return [_memory[k] for k in keys]


def cosine(a: list[float], b: list[float]) -> float:
    """Pure logic."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def nearest(context, text: str, examples: list[tuple[str, str]]) -> Optional[tuple[str, float]]:
    """(label, similarity) of the example nearest `text` in meaning, or
    None without an embedding model. `examples` are (label, sentence)."""
    if not examples:
        return None
    example_vectors = embed(context, [sentence for _label, sentence in examples], kind="example")
    if example_vectors is None:
        return None
    said = embed(context, [text])
    if said is None:
        return None
    score, label = max((cosine(said[0], v), label) for v, (label, _s) in zip(example_vectors, examples))
    return label, score
