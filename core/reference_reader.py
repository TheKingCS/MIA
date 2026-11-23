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

**The floor** (`floor`): like core/safety_floor.py for a crisis, a rule in code under every library answer about one
thing a source must never be read as leaving out: canning a low-acid food (green beans, corn, meat...) is only in a
pressure canner. Only when canning is really asked (`canning_asked`: never "can I eat corn") and never for a pickled
or acidified food (boiling water suits those); an answer telling a low-acid food into a water bath (`unsafe_bath`)
isn't said at all: the rule and the guide's own page for that food instead (`usda_passage`, stopping where another
food's times begin), any other is kept whole with the USDA's rule after it; tomatoes get the added-acid rule. A plain
canning question never reads the pickle recipes (`not_pickling`): their water bath is right only with vinegar.
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
    "disagree, say so. The people who wrote these aren't him: never say a detail of theirs (where they live, their "
    "house, their fence) is his. If they don't cover what was asked, say that plainly rather than filling the gap. Keep to "
    "what was asked: the answer in a few short paragraphs at most, then offer to read further (read_reference with "
    "a passage's ref) if there's more worth knowing.")


_CANNING = re.compile(
    r"\b(?:canning|canner|home[- ]canned|pressure[- ]can(?:ned|ning)?)\b"
    r"|\b(?:how\s+(?:do|should|would|to)\s+(?:i\s+|you\s+|we\s+)?(?:safely\s+|properly\s+)?|(?<!what\s)to\s+|"
    r"safely\s+|properly\s+)can\s+(?!i\b|you\b|we\b|they\b|it\b|be\b|eat\b|grow\b|have\b|get\b|go\b|use\b|keep\b|"
    r"make\b|do\b|survive\b|freeze\b|store\b)[a-z]")
# Not low-acid once acid is added: pickles and relishes go in a boiling-water canner (USDA Guide 6).
_ACIDIFIED = re.compile(r"\b(?:pickl\w*|relish\w*|dilly|sauerkraut|chutney|fermented|vinegar|jams?|jell(?:y|ies)|"
                        r"preserves|marmalade|salsa)\b")


def canning_asked(text: str) -> bool:
    """Pure logic. Whether a question is about canning food (preserving it in jars), never the "can" of "can I eat
    corn" or "what can the dog eat": the words canning, canner or pressure-canning, or "can" as the thing to do
    ("how do I safely can green beans", "to can tomatoes")."""
    return bool(_CANNING.search((text or "").lower()))


# The names the references use for what people call something else: the USDA's canning guide says "snap beans" for
# green beans, "summer squash" for zucchini.
OTHER_NAMES = {"green beans?": "snap", "string beans?": "snap", "zucchinis?": "summer", "courgettes?": "summer",
               "sweet ?corn": "corn", "bell peppers?": "peppers", "scallions?": "onions"}


def terms(text: str) -> list[str]:
    """Pure logic. The words of a question worth matching, in order, once each (a simple plural matched too). "can"
    as preserving food ("safely can green beans", "to can tomatoes") is the word that matters: it's kept as
    "canning" (`canning_asked`), never thrown away with "can I"."""
    lowered = (text or "").lower()
    out = []
    for w in _WORD.findall(lowered):
        if w not in _STOP and w not in out:
            out.append(w)
    if canning_asked(lowered) and "canning" not in out:
        out.insert(0, "canning")
    for said, also in OTHER_NAMES.items():  # what the references call it, near the front (a question keeps 5 words)
        if re.search(rf"\b{said}\b", lowered) and also not in out:
            out.insert(1 if out and out[0] == "canning" else 0, also)
    return out


_FAMILY = {"canning": "canning", "canner": "canning", "canners": "canning", "canned": "canning"}


def _stem(word: str) -> str:
    """Pure logic. A word without its plain endings, so 'posts' finds 'post' and 'setting' finds 'sett': a plural s,
    then -ing or -ed on a longer word (a doubled last letter undone), never down to a stopword or under four letters.
    canning, canner and canned are one word ('canning'), so the modal "can" never counts as one of them. No -er: it
    made corner corn and butter but."""
    if word in _FAMILY:
        return _FAMILY[word]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    for end in ("ing", "ed"):
        if len(word) > len(end) + 4 and word.endswith(end):
            cut = word[:-len(end)]
            if len(cut) > 3 and cut[-1] == cut[-2] and cut[-1] not in "lsz":
                cut = cut[:-1]
            if len(cut) >= 4 and cut not in _STOP:
                word = cut
            break
    return word


# The floor under her library answers (like core/safety_floor.py for a crisis): what a source must never be read as
# leaving out. Canning a low-acid food in a boiling-water bath can grow botulism; the USDA Complete Guide to Home
# Canning processes each of these only in a pressure canner (Guides 1, 4 and 5). Acidified foods (pickles, relishes)
# are another matter: boiling water is right for them (Guide 6), so the floor stands aside.
LOW_ACID = ("green beans", "snap beans", "string beans", "wax beans", "lima beans", "beans", "bean", "peas", "pea",
            "corn", "carrots", "carrot", "potatoes", "potato", "sweet potatoes", "beets", "beet", "asparagus", "okra",
            "pumpkin", "squash", "mushrooms", "mushroom", "peppers", "pepper", "onions", "onion", "greens", "spinach",
            "garlic", "meat", "beef", "pork", "venison", "chicken", "turkey", "poultry", "fish", "salmon", "tuna",
            "seafood", "chili", "stew", "soup", "stock", "broth", "vegetables", "vegetable")
_BATH = re.compile(r"boiling[- ]?water\s+(?:bath|canner|canning|process\w*)|(?<!ice )(?<!cold )(?<!iced )water[- ]?bath"
                   r"|open[- ]kettle|oven[- ]can|boil(?:ing)?\s+(?:the\s+)?(?:filled\s+)?jars|steam\s+canner", re.I)
_NEGATED = re.compile(r"\b(?:never|not|don'?t|do not|isn'?t|can'?t|cannot|unsafe|instead of|rather than)\b", re.I)


def not_pickling(question: str, found: list[dict]) -> list[dict]:
    """Pure logic. For a question about canning a food plainly (not pickled, not a relish), the passages without the
    pickle and relish recipes: those go in a boiling-water bath because vinegar is added, and read beside green
    beans they made her give green beans a water bath (2026-11-23, live). Any other question: all of them."""
    asked = (question or "").lower()
    if not canning_asked(asked) or _ACIDIFIED.search(asked):
        return found
    return [p for p in found if not _ACIDIFIED.search((p["article"] + " " + p["text"][:600]).lower())]


NO_PAGE = " I won't give a water-bath method for it. Want me to read you the guide's pressure-canning steps?"


def unsafe_bath(answer: str) -> bool:
    """Pure logic. Whether an answer tells a food to go in a boiling-water bath (or the oven, open kettle, boiled
    jars), in a sentence that doesn't say not to; "a pressure canner or a water bath" offers the bath, so it counts.
    An ice or cold water bath (cooling blanched food) isn't canning."""
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer or ""):
        if _BATH.search(sentence) and not _NEGATED.search(sentence):
            return True
    return False


def usda_passage(sources: str, food: str) -> str:
    """Pure logic. From what her library gave this turn, the USDA guide's passage about this food that says
    pressure: its text, cut short, and cut where another food's process-time table starts (a PDF page runs one food
    into the next: snap beans' steps, then lima beans' times), with a note that its own times may be on the next page;
    "" when there's none."""
    blocks = re.split(r"\n\s*\n", sources or "")
    words = set(food.lower().split()) | {"snap", "italian", "green", "wax"} if "bean" in food else set(food.lower().split())
    stem = food.split()[-1].rstrip("s")
    for block in blocks:
        low = block.lower()
        if "usda" in low and "pressure" in low and stem in low and not _ACIDIFIED.search(low):
            body = " ".join("\n".join(line for line in block.splitlines()
                                      if not line.startswith(("From ", "ref: ", "["))).split())
            for m in re.finditer(r"(?:\b[A-Za-z]+\s+){0,2}Recommended process time for ([^.]{0,40})", body):
                if not (set(m.group(1).lower().split()) & (words - {"beans", "bean"})):
                    return body[:m.start()].strip()[:1500] + " (Its own process times are on the next page of the " \
                        "guide: ask and I'll read them.)"
            return body[:1500]
    return ""


def floor(question: str, answer: str, sources: str = "") -> str:
    """Pure logic. A library answer with its safety floor. About canning a low-acid food (green beans, corn, meat...;
    never a pickled or acidified one, which boiling water suits): an answer that tells it to go in a boiling-water
    bath is not said at all, only the USDA's rule and the guide's own page for that food from what she read
    (`usda_passage`, `sources`), or an offer to read it; any other answer is
    kept whole (its own lines too) with the rule after it. Tomatoes get the USDA's added-acid rule. Anything else is
    returned as it was. `question` may hold what was looked up too (a follow-up names the food in its look-up)."""
    asked = (question or "").lower()
    if not canning_asked(asked) or _ACIDIFIED.search(asked):
        return answer
    if re.search(r"\btomato(?:es)?\b", asked):
        return (answer or "").rstrip() + (
            "\n\nThe USDA's guide adds acid to every jar of tomatoes, whichever canner: 2 tablespoons of bottled lemon "
            "juice or 1/2 teaspoon of citric acid per quart (half that per pint).")
    food = next((f for f in LOW_ACID if re.search(rf"\b{re.escape(f)}\b", asked)), "")
    if not food:
        return answer
    rule = (f"One thing the USDA's canning guide is firm about: low-acid foods like {food} go only in a pressure "
            "canner, at the pressure and time it gives for your altitude; a boiling-water bath can't make them safe "
            "(botulism).")
    if unsafe_bath(answer):
        passage = usda_passage(sources, food)
        if passage:
            return rule + "\n\nHere is the guide's own page for them:\n" + passage
        return rule + NO_PAGE
    return ((answer or "").rstrip() + "\n\n" + rule).strip()


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
    ref, score, distinct}]. Her own index first (each index's own best two: `pack_index.search` per_index, within
    its own SEARCH_SECONDS: the small guides and PDFs live only there), then Kiwix's; at most READS articles read
    whole, within SECONDS."""
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
    root = getattr(library, "root_path", None)
    if root is not None:  # her own index first, with its own time: the small guides (PDFs) live only there
        for hit in pack_index.search(Path(root), library, question, full=True, packs=packs, per_index=2):
            window, distinct = best_window(hit.snippet, wanted)
            found.append({"pack": hit.pack_title, "article": hit.article_title, "text": window,
                          "ref": f"{hit.pack_id}|{hit.path}|{hit.page}", "score": score(wanted, hit.article_title, window),
                          "distinct": distinct})
    started = time.monotonic()  # the articles' own time
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
    them, at least one), so one word repeated doesn't fill the places; the same page found in two packs is one."""
    need = max(1, (wanted + 1) // 2)
    if words:
        found = weighed(found, words)
    if found and all("meaning" in p for p in found):  # ranked by meaning first, the words breaking ties
        order = sorted(found, key=lambda p: (round(p["meaning"], 3), p["score"]), reverse=True)
    else:
        order = sorted(found, key=lambda p: p["score"], reverse=True)
    seen, out = set(), []
    for p in order:
        key = " ".join(p["text"].split())[:160]  # the same page in two packs (the preppers' PDFs) is one passage
        if p["score"] >= 10 and p.get("distinct", need) >= need and key not in seen:
            seen.add(key)
            out.append(p)
    return out[:keep]


MEANING_TOP = 24  # passages, best by their words, that are then ranked by meaning
MEANING_SECONDS = 5  # the embedding's own time, at most: then the words decide


def by_meaning(context, question: str, found: list[dict], top: int = MEANING_TOP) -> Optional[list[dict]]:
    """The best `top` passages by their words, ranked again by how close each is in meaning to the question (her
    embedding model, core/meaning.py: the question as a search query, each passage as a document), each with its
    `meaning` (cosine, 0 to 1); at most two passages of one article or PDF in the pool, and MEANING_SECONDS for the
    embedding. None when there's no embedding model here: the words' ranking stands. Words alone
    can't tell "a deep cut" from prickly pears to cut, or canning beans from feeding a cat beans."""
    from core import meaning

    url = meaning._base_url(context)
    if url is None or not found:
        return None
    from core.llm_manager import OllamaBackend

    model = meaning._model(context)
    query, document = ("search_query: ", "search_document: ") if model.startswith("nomic") else ("", "")
    pool, per_article = [], {}
    for p in sorted(found, key=lambda p: p["score"], reverse=True):  # at most two passages of one article or PDF
        key = (p["pack"], p["article"].split(", page ")[0])
        if per_article.get(key, 0) < 2:
            per_article[key] = per_article.get(key, 0) + 1
            pool.append(p)
        if len(pool) >= top:
            break
    try:
        vectors = OllamaBackend(url, model, "5m").embed(
            model, [query + question] + [document + (p["article"] + ". " + p["text"])[:2000] for p in pool],
            MEANING_SECONDS)
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
