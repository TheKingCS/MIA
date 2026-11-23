"""
core.reference_reader
=======================

How she reads her offline library to answer (Zac, 2026-11-22: "make her really good at reading through these
references and talking naturally but factually about what knowledge they contain").

**Reading the right part** (`gather`, `best_window`): an article's opening is rarely where the answer is. For each
pack, the best few articles Kiwix's index finds are read whole (core/reference_library_manager.article_text), and so
are the pages her own index finds (core/pack_index.py: the PDFs and the packs Kiwix didn't index); from each, the
window of text where the question's words gather most, cut at sentence ends. `rank` then keeps the windows that hold
the most of the question (all of its words beat one of them repeated; the title counts too).

**Reading further** (`read`): a passage carries its `ref` (pack, entry, page); asked for more ("tell me more about
that", "what does it say about hardening off?"), she reads that source at length, around what's asked.

**Talking about it** (`HOW_TO_TALK`): the material comes framed as outside text (core/browser_safety.outside), with
how to use it: in her own words and naturally, as someone who has read it, but every fact, number and step from the
text, the source named in passing, and what it doesn't cover said plainly. The facts are found in code; the model
only phrases them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

WINDOW = 1400  # characters of an article kept per passage
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


def terms(text: str) -> list[str]:
    """Pure logic. The words of a question worth matching, in order, once each (a simple plural matched too)."""
    out = []
    for w in _WORD.findall((text or "").lower()):
        if w not in _STOP and w not in out:
            out.append(w)
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
    """Every pack's best articles for the question, each read whole and cut to its best window: [{pack, article,
    text, ref, score}]. Kiwix's index and hers both; at most READS articles read whole."""
    from core import pack_index

    wanted = terms(question)
    if not wanted:
        return []
    found, reads = [], 0
    for pack in library.list_packs():
        if reads >= READS:
            break
        for hit in library.search(pack.pack_id, question, limit=per_pack):
            article = library.article_text(pack.pack_id, hit.path, max_chars=80_000)
            reads += 1
            if not article or not article.get("text"):
                continue
            window, _distinct = best_window(article["text"], wanted)
            found.append({"pack": pack.title, "article": article.get("title") or hit.title, "text": window,
                          "ref": f"{pack.pack_id}|{hit.path}|0", "score": score(wanted, hit.title, window)})
    root = getattr(library, "root_path", None)
    if root is not None:
        for hit in pack_index.search(Path(root), library, question, limit=30, full=True):
            window, _distinct = best_window(hit.snippet, wanted)
            found.append({"pack": hit.pack_title, "article": hit.article_title, "text": window,
                          "ref": f"{hit.pack_id}|{hit.path}|{hit.page}", "score": score(wanted, hit.article_title, window)})
    return found


def rank(found: list[dict], keep: int = 4) -> list[dict]:
    """Pure logic. The best passages, one per article, best first; none that holds none of the question."""
    seen, out = set(), []
    for p in sorted(found, key=lambda p: p["score"], reverse=True):
        key = (p["pack"], p["article"])
        if p["score"] >= 10 and key not in seen:
            seen.add(key)
            out.append(p)
    return out[:keep]


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
