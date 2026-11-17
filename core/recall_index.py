"""
core.recall_index
===================

Recall by meaning (DEC-0210; Prompt 07's memory infrastructure, `docs/mia_os/MIA_OS_MEMORY_INFRASTRUCTURE.md` §2;
Zac's yes to Q-71: every personal store except the private journal and private-mode conversations). One index per
person, beside the stores and never instead of them.

**What it holds** (`recall_index.json` in his folder, a personal store): for each record that may be recalled, its
`kind:id` ref, a hash of its text, a vector and when it was indexed, plus which embedding model made the vectors.
**Never the record itself**: every hit is re-read from its store (`search`), so an erased record can't come back from
a stale vector, and a record that's gone is dropped from the index on the next refresh.

**What's in it** (`SOURCES`, first slice): what MIA remembers about him (`user_memories`), his notes (`journal`, the
plain one, never the private journal), what he promised, decided or set aside (`life_notes`) and his projects. Not the
private journal, not conversations (a later slice: those not in a private mode).

**How:** a background job (`recall_index`, every 10 minutes, held by stop everything) embeds what's new or changed,
`BATCH` at a time, with the embedding model on this computer's Ollama (`llm.embed_model`, nomic-embed-text, with its
document and query prefixes), called here so his vectors never land in the device's shared cache. Search embeds the
question and ranks by cosine; with no embedding model it falls back to matching words and says so (REQ-INT-017).
Asked "what do I have about the coop?" (`recall`), she lists what she found, each marked as related by meaning or
matching words.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

_FILE = DATA_DIR / "recall_index.json"
BATCH = 32  # records embedded per refresh, at most
SHOWN = 5  # hits returned
MIN_SCORE = 0.55  # below this a meaning match isn't shown
TEXT_CHARS = 1500  # of a record's text embedded


def _memories(store) -> list[tuple[str, str]]:
    """(id, text) of what MIA remembers about him."""
    return [(m.memory_id, m.text) for m in store.all_memories()]


def _journal(store) -> list[tuple[str, str]]:
    """(id, text) of his notes (the plain journal)."""
    return [(e.entry_id, f"{e.title}\n{e.body}".strip()) for e in store.all_entries()]


def _life_notes(store) -> list[tuple[str, str]]:
    """(id, text) of his promises, decisions, ideas and goals set aside."""
    return [(n["id"], " ".join(str(n.get(k) or "") for k in ("what", "who", "why")).strip()) for n in store.of_kind()]


def _projects(store) -> list[tuple[str, str]]:
    """(id, text) of his projects."""
    return [(p.project_id, f"{p.name}\n{p.description}".strip()) for p in store.all_projects()]


# kind: (the store's attribute on the context, list (id, text), re-read one by id, its title for a hit, the page)
SOURCES: dict[str, tuple[str, Callable, Callable, Callable, str]] = {
    "memory": ("user_memories", _memories, lambda s, i: s.get_memory(i), lambda r: r.text, "memories.html"),
    "journal": ("journal", _journal, lambda s, i: s.get_entry(i), lambda r: r.title or r.body[:60], "journal.html"),
    "note": ("life_notes", _life_notes, lambda s, i: s.get(i), lambda r: r.get("what", ""), "journal.html"),
    "project": ("projects", _projects, lambda s, i: s.get_project(i), lambda r: r.name, "projects.html"),
}


def _hash(text: str) -> str:
    """Pure logic. A short hash of a record's text (a change re-embeds it)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def records(context) -> dict[str, str]:
    """Every record that may be recalled, {ref: text}, from the stores on this context (missing stores skipped)."""
    out: dict[str, str] = {}
    for kind, (attr, lister, _get, _title, _page) in SOURCES.items():
        store = getattr(context, attr, None)
        if store is None:
            continue
        try:
            for rid, text in lister(store):
                if text and text.strip():
                    out[f"{kind}:{rid}"] = text.strip()[:TEXT_CHARS]
        except Exception:  # noqa: BLE001 - one store that can't be read never stops the rest
            log.exception("Recall: couldn't read %s", attr)
    return out


def embedder(context) -> Optional[Callable[[list[str], str], Optional[list]]]:
    """A function (texts, "document" or "query") -> vectors, on this computer's embedding model, or None when there's
    none configured. Called directly (not core/meaning.py's cache), so his vectors stay in his folder."""
    from core import meaning

    url = meaning._base_url(context)
    if url is None:
        return None
    model = meaning._model(context)

    def run(texts: list[str], kind: str) -> Optional[list]:
        """The vectors, or None when the model doesn't answer."""
        prefix = ("search_query: " if kind == "query" else "search_document: ") if model.startswith("nomic") else ""
        body = json.dumps({"model": model, "input": [prefix + t for t in texts]}).encode("utf-8")
        request = urllib.request.Request(f"{url}/api/embed", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                vectors = json.loads(response.read().decode("utf-8")).get("embeddings") or []
        except (urllib.error.URLError, OSError, ValueError) as problem:
            log.info("Recall: no embedding model (%s)", problem)
            return None
        return vectors if len(vectors) == len(texts) else None

    run.model = model
    return run


class RecallIndex:
    """One person's recall index (see the module's opening): refs, text hashes and vectors only."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the index from a person's folder (or data/); an unreadable one starts empty (it's rebuilt)."""
        from core.at_rest import open_text

        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _FILE.parent
        self._file = self.data_dir / _FILE.name
        self.model = ""
        self.items: dict[str, dict] = {}
        if self._file.exists():
            try:
                data = json.loads(open_text(self._file))
                self.model, self.items = str(data.get("model", "")), dict(data.get("items", {}))
            except (OSError, ValueError, TypeError, AttributeError):
                log.exception("recall_index.json unreadable, starting empty (it's rebuilt).")

    def _load(self) -> None:
        """Reads the file again (after an undo restored the stores it follows)."""
        self.__init__(self.context, self.data_dir)

    def _save(self) -> None:
        """Writes the index atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"model": self.model, "items": self.items}))

    def refresh(self, context, embed=None, now: Optional[datetime] = None) -> dict:
        """Drops what's gone, embeds up to BATCH new or changed records; {added, dropped, waiting}. A different
        embedding model starts the index over."""
        embed = embed if embed is not None else embedder(context)
        found = records(context)
        dropped = [ref for ref in self.items if ref not in found]
        for ref in dropped:
            del self.items[ref]
        if embed is None:
            if dropped:
                self._save()
            return {"added": 0, "dropped": len(dropped), "waiting": len(found) - len(self.items)}
        model = getattr(embed, "model", "")
        if model and model != self.model:
            self.items, self.model = {}, model
        todo = [(ref, text) for ref, text in found.items()
                if self.items.get(ref, {}).get("h") != _hash(text)][:BATCH]
        added = 0
        if todo:
            vectors = embed([t for _r, t in todo], "document")
            if vectors:
                at = (now or datetime.now()).isoformat(timespec="seconds")
                for (ref, text), vector in zip(todo, vectors):
                    self.items[ref] = {"h": _hash(text), "v": [round(x, 5) for x in vector], "at": at}
                added = len(todo)
        if added or dropped:
            self._save()
        return {"added": added, "dropped": len(dropped), "waiting": len(found) - len(self.items)}

    def forget(self, ref: str) -> None:
        """Takes one record out of the index at once (a deleted memory, an erased note)."""
        if self.items.pop(ref, None) is not None:
            self._save()


def _reread(context, ref: str):
    """(kind, the record re-read from its store) or None when it's gone."""
    kind, _, rid = ref.partition(":")
    source = SOURCES.get(kind)
    store = getattr(context, source[0], None) if source else None
    if store is None:
        return None
    try:
        record = source[2](store, rid)
    except Exception:  # noqa: BLE001 - a record that can't be read isn't shown
        return None
    return (kind, record) if record is not None else None


def _hit(context, ref: str, score: float, how: str) -> Optional[dict]:
    """One result, re-read from its store: {ref, kind, title, page, score, how}; None when the record is gone."""
    found = _reread(context, ref)
    if found is None:
        return None
    kind, record = found
    return {"ref": ref, "kind": kind, "title": str(SOURCES[kind][3](record))[:120], "page": SOURCES[kind][4],
            "score": round(score, 3), "how": how}


def words_of(text: str) -> set:
    """Pure logic. The words of a text worth matching on (three letters or more)."""
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3}


def search(context, query: str, embed=None, shown: int = SHOWN) -> dict:
    """What he has about `query`: {hits, how} where how is "meaning" or "words" (no embedding model, REQ-INT-017).
    Every hit is re-read from its store; a ref whose record is gone is dropped from the index."""
    index = getattr(context, "recall", None)
    embed = embed if embed is not None else embedder(context)
    vectors = embed([query], "query") if (embed is not None and index is not None and index.items) else None
    hits: list[dict] = []
    if vectors:
        from core.meaning import cosine

        ranked = sorted(((cosine(vectors[0], item["v"]), ref) for ref, item in index.items.items()), reverse=True)
        for score, ref in ranked:
            if score < MIN_SCORE or len(hits) >= shown:
                break
            hit = _hit(context, ref, score, "related")
            if hit is None:
                index.forget(ref)
            else:
                hits.append(hit)
        return {"hits": hits, "how": "meaning"}
    asked = words_of(query)
    scored = []
    for ref, text in records(context).items():
        common = len(asked & words_of(text))
        if common:
            scored.append((common / max(1, len(asked)), ref))
    for score, ref in sorted(scored, reverse=True)[:shown]:
        hit = _hit(context, ref, score, "words")
        if hit is not None:
            hits.append(hit)
    return {"hits": hits, "how": "words"}


def said(context, query: str) -> str:
    """"What do I have about X?" in words."""
    query = (query or "").strip()
    if not query:
        return "What should I look for?"
    found = search(context, query)
    if not found["hits"]:
        return f"I didn't find anything of yours about {query}."
    names = {"memory": "something I remember", "journal": "a note", "note": "a note to self", "project": "a project"}
    lines = [f"{names.get(h['kind'], h['kind'])}: {h['title']}" for h in found["hits"]]
    how = "related by meaning" if found["how"] == "meaning" else "matching your words (the meaning model isn't on)"
    return f"About {query}, {how}: " + "; ".join(lines) + "."


def register_recall_actions(registry) -> None:
    """Registers the recall tool."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="recall", domain="memory",
        description="Find what the person has about something across what MIA remembers, their notes, notes to self "
                    "and projects, by meaning (core/recall_index.py); each found record is re-read from its store.",
        parameters={"type": "object", "properties": {
            "about": {"type": "string", "description": "What to look for, in their words."}}, "required": ["about"]},
        handler=lambda context, arguments: said(context, str(arguments.get("about") or "")),
        prompt_arg="about",
        trigger_phrases=("what do i have about", "what have i got about", "find my notes about", "anything about",
                         "what did i write about", "remind me what i said about"),
        subjects=("about", "notes", "remember"),
    ))
