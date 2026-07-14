"""
core.device_help_manager
==========================

Retrieval-grounded "what does this do / how do I use this device"
answers — docs/ROADMAP.md milestone 5.4. This is explicitly **stage 1
("Read & explain")** of the Self-Modification / Dev Mode staged plan in
docs/ROADMAP.md: read-only retrieval over `docs/*.md` and module
metadata, never a file write or code execution. Do not grow this into
stage 2 (propose-a-patch) without a deliberate, separate decision.

Retrieval is deliberately simple keyword overlap, not embeddings/vector
search — the whole corpus here is a handful of markdown docs (a few
dozen section headings total) plus a dozen or so module descriptions,
small enough that a heavier retrieval stack would be solving a problem
this project doesn't have, and would spend real dependencies/CPU on Pi
5 hardware whose AI HAT+2 budget is already earmarked for the LLM
itself (docs/HARDWARE.md). Same "don't over-engineer" spirit as
core/search_manager.py's substring matching.

Module metadata comes from a lazily-invoked callable
(`register_module_lister`), not a direct ModuleManager import — same
registration-callback shape as core/search_manager.py's
`register_provider`, so this module doesn't need to know about module
internals. core/application.py wires the real `ModuleManager.all` in,
mirroring its own `_register_search_providers`.

`register_reference_library()` (docs/ROADMAP.md milestone 5.6, added
at the user's request after using the app) is the same shape again:
`build_grounded_prompt()` blends in short plain-text snippets from
`core/reference_library_manager.py`'s `search_all_packs()` — the
actual installed Reference Library content (Wikipedia/iFixit/
Wikibooks/etc.), not just this app's own `docs/*.md`. Unlike the
`docs/*.md` retrieval above, reference-library hits are NOT re-scored
by `score_chunk()` — libzim's own full-text search relevance ranking
is used as-is, since it's a real information-retrieval engine and this
module's crude keyword-overlap heuristic would only make ranking
worse, not better, for that content.

**LLM query reformulation for Reference Library search** (2026-07-14,
the "AI advancement" thread's embedding-based-retrieval work — see
docs/ROADMAP.md for the full writeup on why this exists instead of a
real vector index). Measured directly against the real installed packs
that libzim's lexical search has a severe, genuine vocabulary-mismatch
problem: "hypothermia symptoms" correctly finds the Hypothermia
article, but "my hands are freezing and numb" (a far more natural way
to actually ask this) returns completely unrelated hits (an iPod Touch
logic board replacement page). A full semantic embedding index over
these packs would fix this properly, but the installed packs total
~1.8 million articles (Wikipedia top-mini alone is 875K) — pre-computing
and storing embeddings for all of that, re-indexed on every pack
install/removal, is a multi-hour, multi-GB undertaking that belongs on
Project 2's Home compute per docs/VISION.md's own established
Pi-vs-Home placement principle, not something to build blind on Pi-class
hardware in one pass. `_reformulate_query_for_search()` asks the
already-running LLM to translate a colloquial question into likely
technical/topical search keywords, then `_reference_library_chunks()`
searches with BOTH the original keywords and the reformulated ones,
merging and deduping results (reformulated first, since it specifically
targets the vocabulary-mismatch case the original keywords already
fail at) — no new index, no new dependency, reuses the LLM connection
that already exists for everything else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOCS_DIR = _PROJECT_ROOT / "docs"

_WORD_RE = re.compile(r"[a-z0-9]+")

# Filtered out of the *query* only (not chunk text) before scoring — these
# are common enough that substring-free, whole-word matches on them still
# carry no real signal about which chunk is relevant (e.g. "do" legitimately
# appears as a whole word all over technical prose: "how do I...", "to do
# this"). Chunk-side matching is unaffected; this only trims what a query
# is scored against.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "do", "does", "did",
    "what", "which", "who", "whom", "how", "why", "when", "where",
    "i", "you", "it", "this", "that", "these", "those", "to", "of", "in", "on",
    "and", "or", "for", "with", "about", "my", "me", "can", "should", "would",
}

_MODULE_NAME_MATCH_BONUS = 10

_SYSTEM_PREAMBLE = (
    "You are M.I.A.'s built-in assistant. Answer the user's question using "
    "ONLY the reference material below. If the answer isn't contained in "
    "it, say you don't know rather than guessing — do not use outside "
    "knowledge."
)
# A longer version of this preamble (explicitly describing the material as
# possibly including "reference library... encyclopedia articles, repair/
# how-to guides") was tried first and found, via real testing against the
# live model, to make llama3.2:3b MORE likely to falsely say "I don't
# know" even when the answer was clearly present in a single short
# reference chunk — some extra qualifying clause about what "counts"
# seems to make this small model more conservative, not more capable.
# Keep this preamble short; if it needs editing again, re-verify against
# the real model with a case like "what does the notes module do" before
# assuming a wording tweak is harmless.

# One hit per installed pack (search_all_packs()'s own shape), capped
# high enough to comfortably cover every pack a real device has
# installed (a handful in practice) rather than tuned as a performance
# knob — see that method's docstring for the real crowding bug this
# avoids.
_REFERENCE_LIBRARY_SNIPPET_LIMIT = 10

# See this module's docstring on LLM query reformulation. Deliberately
# asks for keywords, not a rephrased question — search_all_packs()
# hands this straight to libzim's own keyword/full-text index
# (core/reference_library_manager.py), not back through another LLM.
_QUERY_REFORMULATION_PROMPT_TEMPLATE = (
    "What is the single most likely encyclopedia article title for the "
    "subject of the following question? Reply with ONLY that title (2-3 "
    "words) — no punctuation, no explanation, no restating the question.\n\n"
    "Question: {query}"
)
# Verified directly against the real installed packs (docs/ROADMAP.md's
# writeup): asking libzim's search for MORE than ~3 words at once made
# results dramatically worse, not better — "hypothermia hypovolemia cold
# stress shock" (5 reformulated terms) returned ZERO hits at all, while
# "hypothermia frostbite" (2 terms) correctly ranked the real Frostbite
# article #1. Same "more retrieved context isn't always better" lesson
# this project already learned once for docs/*.md grounding (this
# module's own _SYSTEM_PREAMBLE comment), rediscovered here for
# Reference Library search terms specifically. Prompt was changed from
# "2 to 5 keywords" to "the single most likely article title (2-3
# words)" for exactly this reason — defensive cap kept in case the
# model ignores that and replies with more anyway.
_MAX_REFORMULATED_QUERY_WORDS = 4


@dataclass
class HelpChunk:
    source: str  # e.g. "docs/ARCHITECTURE.md" or "Module: Notes"
    heading: str
    text: str  # full chunk text, including its own heading line


def split_into_chunks(markdown_text: str, source: str) -> list[HelpChunk]:
    """
    Split a markdown doc into chunks at each ## or ### heading. Pure
    logic — testable without touching the filesystem (see
    tests/test_device_help_manager.py).
    """
    current_heading = "Introduction"
    current_lines: list[str] = []
    chunks: list[HelpChunk] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append(HelpChunk(source=source, heading=current_heading, text=body))

    for line in markdown_text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            flush()
            current_heading = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()
    return chunks


def score_chunk(query_words: set[str], chunk: HelpChunk) -> int:
    """
    Count of query words appearing in the chunk, weighted double for a
    heading match. Matches whole words (via _tokenize), not substrings
    — a naive `word in text` substring check would let a short word
    like "do" false-match inside unrelated words ("random", "wisdom",
    "kingdom"), which is exactly the bug that motivated this.
    """
    heading_words = _tokenize(chunk.heading)
    body_words = _tokenize(chunk.text)
    score = 0
    for word in query_words:
        if word in heading_words:
            score += 2
        elif word in body_words:
            score += 1
    return score


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _query_words(query: str) -> set[str]:
    """Tokenize a query and drop stopwords — falls back to the raw token set if that empties it out."""
    words = _tokenize(query)
    meaningful = words - _STOPWORDS
    return meaningful or words


class DeviceHelpManager:
    """Core-level device-help retrieval service (`AppContext.device_help`)."""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._doc_chunks: Optional[list[HelpChunk]] = None
        self._module_lister: Optional[Callable[[], list]] = None
        self._reference_library = None

    def register_module_lister(self, lister: Callable[[], list]) -> None:
        """`lister` returns the currently discovered modules (duck-typed: needs .display_name/.description)."""
        self._module_lister = lister

    def register_reference_library(self, reference_library) -> None:
        """`reference_library` is a core.reference_library_manager.ReferenceLibraryManager (duck-typed: needs .search_all_packs())."""
        self._reference_library = reference_library

    def _ensure_docs_loaded(self) -> None:
        """Reading a handful of small markdown files is cheap — unlike core/voice_manager.py's
        model loads, this doesn't need deferring past construction, but IS deferred to first
        use anyway so an app boot that never opens the Assistant never touches the filesystem
        for this at all."""
        if self._doc_chunks is not None:
            return

        chunks: list[HelpChunk] = []
        if _DOCS_DIR.exists():
            for doc_path in sorted(_DOCS_DIR.glob("*.md")):
                try:
                    text = doc_path.read_text(encoding="utf-8")
                except OSError as exc:
                    log.warning("Could not read doc %s: %s", doc_path, exc)
                    continue
                chunks.extend(split_into_chunks(text, source=f"docs/{doc_path.name}"))
        self._doc_chunks = chunks

    def _module_chunks(self) -> list[HelpChunk]:
        if self._module_lister is None:
            return []
        try:
            modules = self._module_lister()
        except Exception:
            log.exception("Module lister raised an error — skipping module metadata for device-help.")
            return []

        chunks = []
        for module in modules:
            # Explicitly says "The <Name> module" in the body text, not
            # just a "## <Name>" heading — verified against the live
            # model that this matters a lot: llama3.2:3b reliably
            # answered "what does the notes module do" once the chunk
            # literally said "The Notes module: ...", but said "I don't
            # know" for the exact same information under a bare "##
            # Notes" heading (with or without the strict "say you don't
            # know" instruction, so it wasn't the instruction wording —
            # the model needed the literal word "module" connected to
            # the name in the passage itself, not just implied.
            text = f"The {module.display_name} module: {module.description}"
            chunks.append(HelpChunk(source=f"Module: {module.display_name}", heading=module.display_name, text=text))
        return chunks

    def _scored_doc_and_module_chunks(self, query: str) -> list[tuple[int, HelpChunk]]:
        """(score, chunk) pairs for docs/*.md + module metadata only (not Reference Library), sorted descending."""
        query = query.strip()
        if not query:
            return []

        query_words = _query_words(query)
        if not query_words:
            return []

        self._ensure_docs_loaded()
        query_lower = query.lower()

        scored = [(score_chunk(query_words, chunk), chunk) for chunk in self._doc_chunks]
        for chunk in self._module_chunks():
            score = score_chunk(query_words, chunk)
            if chunk.heading.lower() in query_lower:
                # A module's own name appearing in the query is a much
                # stronger signal than generic keyword overlap — without
                # this, a question like "what does the notes module do"
                # loses to docs/ADDING_MODULES.md, whose every heading
                # contains the word "module" (it's a guide about modules
                # the concept), pushing the actual Notes description out
                # of the results entirely. This is the same "match by
                # name" idea core/search_manager.py's module search
                # already uses, layered on top of the generic scoring.
                score += _MODULE_NAME_MATCH_BONUS
            scored.append((score, chunk))

        scored = [(score, chunk) for score, chunk in scored if score > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored

    def retrieve(self, query: str, limit: int = 5) -> list[HelpChunk]:
        """Return the top `limit` chunks (docs + module metadata) ranked by keyword overlap with `query`."""
        return [chunk for _, chunk in self._scored_doc_and_module_chunks(query)[:limit]]

    def _search_reference_library(self, search_terms: str, limit: int) -> list:
        """Thin wrapper so both call sites in _reference_library_chunks() share one try/except."""
        try:
            return self._reference_library.search_all_packs(search_terms, limit=limit)
        except Exception:
            log.exception("Reference Library search raised an error — skipping it for device-help.")
            return []

    def _reformulate_query_for_search(self, query: str) -> Optional[str]:
        """
        See this module's docstring on LLM query reformulation. Returns
        None (not an exception) on any failure — no LLM configured, the
        backend unreachable, or an empty/non-compliant reply — since
        this is an enhancement on top of the original keyword search,
        never the only path to a result.
        """
        if self.context.llm is None:
            return None
        prompt = _QUERY_REFORMULATION_PROMPT_TEMPLATE.format(query=query)
        reply = self.context.llm.generate(prompt)
        if not reply:
            return None
        words = reply.strip().split()[:_MAX_REFORMULATED_QUERY_WORDS]
        reformulated = " ".join(words).strip()
        return reformulated or None

    def _reference_library_chunks(self, query: str, limit: int = _REFERENCE_LIBRARY_SNIPPET_LIMIT) -> list[HelpChunk]:
        """
        Snippets from the actual installed Reference Library content
        (docs/ROADMAP.md milestone 5.6), not re-scored by score_chunk()
        — see this module's docstring for why libzim's own relevance
        ranking is used as-is.

        Searches with BOTH the stopword-stripped original keywords
        (_query_words() — verified against the real medicine pack that
        this matters: "What are the symptoms of hypothermia?" ranked
        "Pulseless electrical activity" first with filler words diluting
        libzim's ranking, "symptoms hypothermia" correctly ranked
        "Hypothermia" first) AND an LLM-reformulated version (this
        module's docstring on the 2026-07-14 vocabulary-mismatch fix),
        merged and deduped by (pack, article) — reformulated results
        first, since they specifically target the case where the
        original keywords already fail (e.g. "my hands are freezing and
        numb" finding nothing hypothermia-related at all).
        """
        if self._reference_library is None:
            return []

        keywords = " ".join(_query_words(query))
        reformulated = self._reformulate_query_for_search(query)

        seen: set[tuple[str, str]] = set()
        snippets = []
        for search_terms in filter(None, [reformulated, keywords]):
            for snippet in self._search_reference_library(search_terms, limit):
                key = (snippet.pack_title, snippet.article_title)
                if key in seen:
                    continue
                seen.add(key)
                snippets.append(snippet)

        return [
            HelpChunk(source=f"Reference Library: {s.pack_title}", heading=s.article_title, text=s.snippet)
            for s in snippets[:limit]
        ]

    def build_grounded_prompt(self, query: str, limit: int = 5) -> str:
        """
        Build a prompt instructing the LLM to answer `query` using only
        retrieved M.I.A. documentation/module metadata plus any
        matching Reference Library content — the actual "grounding."
        Falls back to a "nothing matched" instruction (still read-only,
        still no outside-topic license) if nothing relevant is indexed
        anywhere, rather than silently falling through to open-ended
        chat.

        When there's already a strong, confident match (score >=
        _MODULE_NAME_MATCH_BONUS — a module named directly in the
        query), only that top chunk is included, and Reference Library
        snippets are skipped entirely. Verified against the real
        installed packs that including the rest is actively harmful,
        not just unhelpful padding: "what does the notes module do"
        already has the exact right answer (the Notes module's own
        description scores a confident module-name-match hit as chunk
        #1), but (a) docs/ADDING_MODULES.md's several large, verbose
        "how to write a module" code chunks also rank as lower partial
        matches, and (b) every one of the 8 installed Reference Library
        packs has *some* weak stemmed match on "module"/"modulator"/
        "note" (e.g. iFixit's "Loudspeaker Modules Replacement",
        Physics's "Electro-optic modulator") — piling either of those
        in alongside the one correct chunk made the LLM answer "I don't
        know" even while its own reasoning quoted the correct text
        verbatim. A confident, specific match doesn't need or benefit
        from extra "maybe related" context; a small model finds it
        actively distracting.
        """
        scored = self._scored_doc_and_module_chunks(query)
        top_score = scored[0][0] if scored else 0
        is_confident_match = top_score >= _MODULE_NAME_MATCH_BONUS

        doc_chunks = [chunk for _, chunk in scored[:1]] if is_confident_match else [chunk for _, chunk in scored[:limit]]
        reference_chunks = [] if is_confident_match else self._reference_library_chunks(query)
        chunks = doc_chunks + reference_chunks
        if not chunks:
            return (
                f"{_SYSTEM_PREAMBLE}\n\nNo reference material matched this question. Say that you "
                f"don't have information about this in M.I.A.'s documentation or reference library."
                f"\n\nQuestion: {query}"
            )

        material = "\n\n".join(f"[{chunk.source} — {chunk.heading}]\n{chunk.text}" for chunk in chunks)
        return (
            f"{_SYSTEM_PREAMBLE}\n\n--- Reference material ---\n{material}\n--- End reference material ---"
            f"\n\nQuestion: {query}"
        )
