"""
core.reference_reader
=======================

How she reads her offline library to answer (Zac, 2026-11-22: "make her really good at reading through these
references and talking naturally but factually about what knowledge they contain").

**Reading the right part** (`gather`, `best_window`): an article's opening is rarely where the answer is. Every
pack is searched first; then the best few articles found are read whole (each pack's best before any pack's second,
at most READS, inside SECONDS) (core/reference_library_manager.article_text), and so
are the pages her own index finds (core/pack_index.py: the PDFs and the packs Kiwix didn't index); from each, the
window of text where the question's words gather most, cut at sentence ends. `rank` then keeps the windows that hold
the most of the question (all of its words beat one of them repeated, rare words beat common ones; the title
counts too), and, where her embedding model answers, the best of those are ranked by how close they are in meaning to
the question (`by_meaning`): words alone can't tell a deep cut from a fruit to cut.

**Reading further** (`read`): a passage carries its `ref` (pack, entry, page); asked for more ("tell me more about
that", "what does it say about hardening off?"), she reads that source at length, around what's asked.

**Talking about it** (`HOW_TO_TALK`): the material comes framed as outside text (core/browser_safety.outside), with
how to use it: in her own words and naturally, as someone who has read it, but every fact, number and step from the
text, the source named in passing, and what it doesn't cover said plainly. The facts are found in code; the model
only phrases them.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

WINDOW = 1400  # characters of an article kept per passage
SECONDS = 12.0  # reading whole articles stops here, inside the answer's own budget
PER_PACK = 2  # articles read whole per pack
READS = 80  # articles read whole per question, at most
_WORD = re.compile(r"[a-z0-9]{3,}")
_STOP = {"the", "and", "for", "how", "what", "with", "can", "you", "does", "should", "when", "why", "from", "that",
         "this", "are", "into", "about", "best", "way", "make", "get", "use", "need", "much", "many", "which", "tell",
         "more", "there", "their", "them", "have", "has", "was", "were", "will", "would", "could", "your", "mine"}

HOW_TO_TALK = (
    "Answer from these the way someone who has just read them would: naturally, in your own words, the useful part "
    "first. Every fact, number, quantity, time and step comes from the text above, exactly as it says (never round "
    "or change a safety figure); name where it's from in passing (\"the USDA canning guide says...\"). If they "
    "disagree, say so. If they don't cover what was asked, say that plainly rather than filling the gap. Keep to "
    "what was asked: the answer in a few short paragraphs at most, then offer to read further (read_reference with "
    "a passage's ref) if there's more worth knowing.")


_CANNING = re.compile(r"\b(?:safely|properly|to|and|or|should|we'll|i'll)\s+can\b|\bcan\s+(?:my|our|the|some|fresh|"
                      r"green|home|tomato|tomatoes|beans|corn|peaches|pears|apples|jam|jelly|meat|chicken|fish|soup|"
                      r"stock|salsa|pickles|vegetables|veggies|fruit|peppers|carrots|potatoes)\b")


def terms(text: str) -> list[str]:
    """Pure logic. The words of a question worth matching, in order, once each (a simple plural matched too). "can"
    as preserving food ("safely can green beans", "to can tomatoes") is the word that matters: it's kept as
    "canning", never thrown away with "can I"."""
    lowered = (text or "").lower()
    out = []
    for w in _WORD.findall(lowered):
        if w not in _STOP and w not in out:
            out.append(w)
    if _CANNING.search(lowered) and "canning" not in out:
        out.insert(0, "canning")
    return out


def _stem(word: str) -> str:
    """Pure logic. A word without a plain plural ending, so 'posts' finds 'post'."""
    return word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word


def _hits(chunk: str, wanted: list[str]) -> tuple[int, int]:
    """Pure logic. (how many of the wanted words a chunk holds, how many times in all)."""
    words = [_stem(w) for w in _WORD.findall(chunk.lower())]
    stems = [_stem(w) for w in wanted]
    return sum(1 for s in stems if s in words), sum(words.count(s) for s in stems)


_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")


def best_window(text: str, wanted: list[str], size: int = WINDOW) -> tuple[str, int]:
    """Pure logic. The stretch of text, about `size` characters cut at sentence ends, where the wanted words gather
    most: (the window, how many of the wanted words it holds). An opening when none is found."""
    text = " ".join((text or "").split())
    if len(text) <= size:
        return text, _hits(text, wanted)[0]
    sentences = [s for s in _SENTENCE.split(text) if s]
    best, best_score, best_distinct = (0, 0), (-1, -1), 0
    for start in range(len(sentences)):
        length, end = 0, start
        while end < len(sentences) and length + len(sentences[end]) <= size:
            length += len(sentences[end]) + 1
            end += 1
        end = max(end, start + 1)
        distinct, count = _hits(" ".join(sentences[start:end]), wanted)
        if (distinct, count) > best_score:
            best, best_score, best_distinct = (start, end), (distinct, count), distinct
    start, end = best
    window = " ".join(sentences[start:end])[:size + 200]
    return ("... " if start else "") + window + (" ..." if end < len(sentences) else ""), best_distinct


def score(question_terms: list[str], title: str, window: str) -> float:
    """Pure logic. How well a passage answers: distinct words of the question it holds (most of all), how often,
    and its title's share."""
    distinct, count = _hits(window, question_terms)
    in_title = _hits(title, question_terms)[0]
    return distinct * 10 + min(count, 20) * 0.5 + in_title * 6


def gather(library, question: str, per_pack: int = PER_PACK) -> list[dict]:
    """Every pack searched, then the best articles read whole and cut to their best window: [{pack, article, text,
    ref, score, distinct}]. Kiwix's index and hers (each index's own best two: `pack_index.search` per_index) both;
    at most READS articles read, within SECONDS."""
    from core import pack_index

    wanted = terms(question)
    if not wanted:
        return []
    started = time.monotonic()
    packs = library.list_packs()  # once per question
    hits = []  # every pack searched first (cheap); then the best hits read whole, each pack's first before seconds
    for pack in packs:
        for n, hit in enumerate(library.search(pack.pack_id, question, limit=per_pack)):
            hits.append((n, -_hits(hit.title, wanted)[0], pack, hit))
    found = []
    for n, _t, pack, hit in sorted(hits, key=lambda h: (h[0], h[1]))[:READS]:
        if time.monotonic() - started > SECONDS:
            break  # the answer's time budget comes first
        article = library.article_text(pack.pack_id, hit.path, max_chars=80_000)
        if not article or not article.get("text"):
            continue
        window, distinct = best_window(article["text"], wanted)
        found.append({"pack": pack.title, "article": article.get("title") or hit.title, "text": window,
                      "ref": f"{pack.pack_id}|{hit.path}|0", "score": score(wanted, hit.title, window),
                      "distinct": distinct})
    root = getattr(library, "root_path", None)
    if root is not None:
        for hit in pack_index.search(Path(root), library, question, full=True, packs=packs, per_index=2):
            window, distinct = best_window(hit.snippet, wanted)
            found.append({"pack": hit.pack_title, "article": hit.article_title, "text": window,
                          "ref": f"{hit.pack_id}|{hit.path}|{hit.page}", "score": score(wanted, hit.article_title, window),
                          "distinct": distinct})
    return found


def weighed(found: list[dict], wanted: list[str]) -> list[dict]:
    """Pure logic. Each passage scored again with every question word weighed by how rare it is among the passages
    found (a word most of them hold, like "green" or "home", counts for less than "canning" or "beans"), its title
    counting too: the same passages, each with its new `score`."""
    import math

    stems = [_stem(w) for w in wanted]
    words_of = [set(_stem(w) for w in _WORD.findall((p["article"] + " " + p["text"]).lower())) for p in found]
    n = max(len(found), 1)
    weight = {s: 1 + math.log(n / max(1, sum(1 for ws in words_of if s in ws))) for s in stems}
    out = []
    for p, ws in zip(found, words_of):
        title = set(_stem(w) for w in _WORD.findall(p["article"].lower()))
        count = sum(_hits(p["text"], [s])[1] for s in stems)
        new = sum(weight[s] for s in stems if s in ws) * 10 + min(count, 20) * 0.5 + \
            sum(weight[s] for s in stems if s in title) * 3
        out.append({**p, "score": new})
    return out


def rank(found: list[dict], keep: int = 4, wanted: int = 0, words: Optional[list] = None) -> list[dict]:
    """Pure logic. The best passages, one per article, best first (weighed by how rare each question word is among
    them, when the question's `words` are given); only those holding about half the question's words (`wanted` of
    them, at least one), so one word repeated doesn't fill the places."""
    need = max(1, (wanted + 1) // 2)
    if words:
        found = weighed(found, words)
    if found and all("meaning" in p for p in found):  # ranked by meaning first, the words breaking ties
        order = sorted(found, key=lambda p: (round(p["meaning"], 3), p["score"]), reverse=True)
    else:
        order = sorted(found, key=lambda p: p["score"], reverse=True)
    seen, out = set(), []
    for p in order:
        key = (p["pack"], p["article"])
        if p["score"] >= 10 and p.get("distinct", need) >= need and key not in seen:
            seen.add(key)
            out.append(p)
    return out[:keep]


MEANING_TOP = 24  # passages, best by their words, that are then ranked by meaning


def by_meaning(context, question: str, found: list[dict], top: int = MEANING_TOP) -> Optional[list[dict]]:
    """The best `top` passages by their words, ranked again by how close each is in meaning to the question (her
    embedding model, core/meaning.py: the question as a search query, each passage as a document), each with its
    `meaning` (cosine, 0 to 1). None when there's no embedding model here: the words' ranking stands. Words alone
    can't tell "a deep cut" from prickly pears to cut, or canning beans from feeding a cat beans."""
    from core import meaning

    url = meaning._base_url(context)
    if url is None or not found:
        return None
    from core.llm_manager import OllamaBackend

    model = meaning._model(context)
    query, document = ("search_query: ", "search_document: ") if model.startswith("nomic") else ("", "")
    pool = sorted(found, key=lambda p: p["score"], reverse=True)[:top]
    try:
        vectors = OllamaBackend(url, model, "5m").embed(
            model, [query + question] + [document + (p["article"] + ". " + p["text"])[:2000] for p in pool], 30)
    except Exception:  # noqa: BLE001 - no meaning: the words decide
        vectors = None
    if not vectors or len(vectors) != len(pool) + 1:
        return None
    asked = vectors[0]
    return [{**p, "meaning": meaning.cosine(asked, v)} for p, v in zip(pool, vectors[1:])]


def read(library, ref: str, focus: str = "", size: int = 6000) -> Optional[dict]:
    """One source read further: {pack, article, text} (around `focus` when given, else from its start), or None for
    a ref that isn't here."""
    from core import pack_index

    try:
        pack_id, path, page = (str(ref or "").split("|") + ["", "", "0"])[:3]
        page_no = int(page or 0)
    except ValueError:
        return None
    pack = library.get_pack(pack_id) if library is not None else None
    if pack is None:
        return None
    text, title = "", path
    if page_no or path.lower().endswith(".pdf"):
        text, title = pack_index.page_text(Path(library.root_path), Path(pack.file_path), path, page_no)
    if not text:
        article = library.article_text(pack_id, path, max_chars=200_000)
        if article:
            text, title = article.get("text", ""), article.get("title") or path
    if not text:
        return None
    wanted = terms(focus)
    body = best_window(text, wanted, size)[0] if wanted else " ".join(text.split())[:size]
    return {"pack": pack.title, "article": title + (f", page {page_no}" if page_no else ""), "text": body}
