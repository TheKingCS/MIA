"""
core.self_docs
================

MIA about her own design, from her own documents (DEC-0041; the
intelligence spec's Phase 2C/3, docs/INTELLIGENCE_AUDIT.md): "how does
the freedom estimate work?", "why can't the phone connect banks?", "what
did we decide about eggs?", answered with the passage and the file it
came from, never from the model's memory.

What's searched, and how much it counts:
- **Decisions** (`docs/DECISIONS.md`), one decision per passage, with its
  status: approved ones count most; proposed ones say they're proposals.
- **Current state, guides, audits and specs** (`docs/*.md` except the
  history, `docs/specs/`, `docs/user_help/`): passages by heading.
- **History** (`docs/ROADMAP.md`): counts least, and is labelled history,
  so an old plan never reads as how things are now.
- Never `data/`, `config/` or anything personal: only the repo's own docs.

Keyword search (the help system's own chunking and scoring,
core/device_help_manager.py): it works the same on the phone and needs no
model. Built once per process, rebuilt when a file changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.device_help_manager import HelpChunk, _query_words, _tokenize, split_into_chunks

DOCS = Path(__file__).resolve().parent.parent / "docs"
HISTORY = {"ROADMAP.md"}
SKIP = {"NEXT_SESSION.md"}  # the to-do list: what's pending, not how MIA works
WEIGHT = {"decision": 3.0, "proposal": 1.5, "doc": 2.0, "spec": 1.5, "help": 2.0, "history": 0.5}
_DEC = re.compile(r"^### (DEC-\d{4}): (.+)$", re.M)
# Words about asking, not about the subject.
_ABOUT_MIA = {"decide", "decided", "decision", "decisions", "mia", "you", "your", "we", "why", "work", "works",
              "design", "built", "build"}


@dataclass
class Passage:
    file: str  # relative to the repo: "docs/DECISIONS.md"
    heading: str
    text: str
    kind: str  # decision, proposal, doc, spec, help, history

    @property
    def chunk(self) -> HelpChunk:
        return HelpChunk(source=self.file, heading=self.heading, text=self.text)


def _decisions(text: str, file: str) -> list[Passage]:
    out = []
    matches = list(_DEC.finditer(text))
    for i, m in enumerate(matches):
        body = text[m.start(): matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        status = re.search(r"- Status: (\w+)", body)
        kind = "decision" if status and status.group(1).upper() == "APPROVED" else "proposal"
        out.append(Passage(file, f"{m.group(1)}: {m.group(2)}", body, kind))
    return out


def build(root: Path = DOCS) -> list[Passage]:
    """Every passage, from the docs folder."""
    passages: list[Passage] = []
    for path in sorted(root.rglob("*.md")):
        rel = "docs/" + path.relative_to(root).as_posix()
        name = path.name
        if name in SKIP or "/HANDOFFS/" in rel or "/design_handoff/" in rel or "/vision_assets/" in rel:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if name == "DECISIONS.md":
            passages.extend(_decisions(text, rel))
            continue
        kind = ("history" if name in HISTORY else "spec" if "/specs/" in rel else "help" if "/user_help/" in rel
                else "doc")
        for chunk in split_into_chunks(text, rel):
            passages.extend(_bullets(Passage(rel, chunk.heading, chunk.text, kind)))
    return passages


def _bullets(p: Passage, longest: int = 1500) -> list[Passage]:
    """Pure logic. A very long section that's a list ("Recent changes") as
    one passage per top-level bullet, so one entry is found, not the
    whole list because it mentions everything."""
    items = re.split(r"\n(?=- )", p.text)
    if len(p.text) <= longest or len(items) < 3:
        return [p]
    out = []
    for item in items[1:]:
        first = re.sub(r"[*`]", "", item[2:].split("\n", 1)[0])[:80].strip()
        out.append(Passage(p.file, f"{p.heading}: {first}", item.strip(), p.kind))
    return out


class SelfDocs:
    """The index, rebuilt when any doc changes (checked by modification times)."""

    def __init__(self, root: Path = DOCS) -> None:
        self.root = root
        self._stamp: Optional[tuple] = None
        self._passages: list[Passage] = []

    def _fresh(self) -> list[Passage]:
        if not self.root.exists():
            return []
        stamp = tuple(sorted((str(p), p.stat().st_mtime) for p in self.root.rglob("*.md")))
        if stamp != self._stamp:
            self._passages, self._stamp = build(self.root), stamp
        return self._passages

    def search(self, question: str, limit: int = 3) -> list[tuple[float, Passage]]:
        from core.capabilities import _stem
        from core.device_help_manager import score_chunk

        words = _query_words(question)
        # "What did we decide about eggs?": the question's subject is the eggs.
        content = {w for w in words if w not in _ABOUT_MIA} or words
        stems = {_stem(w) for w in content}
        scored = []
        for p in self._fresh():
            base = score_chunk(content, p.chunk)  # on the subject, not the asking words
            if not base:
                continue
            # A passage matching more of the question beats a long one matching one word often.
            have = {_stem(w) for w in _tokenize(p.heading) | _tokenize(p.text)}
            coverage = len(stems & have) / max(1, len(stems))
            scored.append((round(base * WEIGHT[p.kind] * coverage * coverage, 3), p))
        scored.sort(key=lambda x: (-x[0], x[1].file, x[1].heading))
        return scored[:limit]


_INDEX: Optional[SelfDocs] = None


def index() -> SelfDocs:
    global _INDEX
    if _INDEX is None:
        _INDEX = SelfDocs()
    return _INDEX


LABEL = {"decision": "an approved decision", "proposal": "a proposal, not decided yet", "doc": "MIA's docs",
         "spec": "a spec (what was asked for, not necessarily built)", "help": "the user guide",
         "history": "history (may be out of date)"}


def _plain(text: str) -> str:
    """Pure logic. Markdown to plain words: no #, **, backticks or bullets."""
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def _gist(p: Passage, chars: int) -> str:
    """The part of a passage worth saying: a decision's Decision (and its
    honest limits), else the passage without its heading line."""
    body = p.text
    if p.kind in ("decision", "proposal"):
        m = re.search(r"^- Decision.*?(?=^- (?!\s)|\Z)", body, re.M | re.S)
        limits = re.search(r"^- Honest limits.*?(?=^- (?!\s)|\Z)", body, re.M | re.S)
        body = (m.group(0) if m else body) + ("\n" + limits.group(0) if limits else "")
        body = re.sub(r"^- (Decision|Honest limits)[^:]*:\s*", lambda x: "" if x.group(1) == "Decision" else "Limits: ",
                      body, flags=re.M)
    else:
        body = body.split("\n", 1)[1] if body.startswith("#") and "\n" in body else body
    text = _plain(body)
    return text if len(text) <= chars else text[:chars].rsplit(" ", 1)[0] + "…"


def answer(question: str, docs: Optional[SelfDocs] = None, limit: int = 3, chars: int = 600) -> str:
    """What MIA's own documents say about `question`, in plain words, with
    the file and what kind of source it is; or that they don't cover it."""
    found = (docs or index()).search(question, limit)
    if not found:
        return "Nothing in my own documents covers that, so I won't guess how I work there."
    best = found[0][1]
    head = best.heading.split(": ", 1)
    title = f"{head[0]} ({head[1]})" if best.kind in ("decision", "proposal") and len(head) == 2 else best.heading
    text = f"From my own documents, {LABEL[best.kind]}: {title} ({best.file}). {_gist(best, chars)}"
    others = [f"{p.heading} ({p.file})" for _s, p in found[1:]]
    if others:
        text += " Related: " + "; ".join(others) + "."
    return text
