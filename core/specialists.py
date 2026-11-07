"""
core.specialists
==================

MIA's specialists (DEC-0109; Zac, 2026-11-07: "she should be able to specialize
agents for each area of skill she is developing, like one that is catered
towards construction knowledge, one towards radio technologies, one towards
military strategy, one towards homesteading skills, one towards research, one
towards testing and auditing, etc. She could essentially specialize workers for
developing and maintaining her knowledge and skills").

**A specialist** (`SPECIALISTS`) is a worker with a charter: what it covers,
the skills it develops (her skill tree's categories), the curriculum tracks it
owns (core/curriculum.py), the loops it watches (core/loops.py), what it may
never do (`limits`), and the questions it starts from. Add one by adding it
here: the charter is code, so a test checks every skill, track and loop it
names is real.

**Its workbook** (`work/specialists/<id>.json`, versioned like the Knowledge
Vault): notes on what it knows, each with its sources (a book, a standard, an
article, a page in her reference library), and the open questions it hasn't
answered yet. A note starts **derived** (written by a model) and becomes
**confirmed** only when a person confirms it (`confirm()`); a wrong one is
**withdrawn**, kept so it isn't written again. MIA always says which a note
is.

**How it studies** (`study()`, from Night School, one specialist a night, the
one that studied longest ago): her teacher is given the specialist's charter,
its limits, its open questions, the titles it already has, and excerpts from
her own offline reference library (Kiwix packs) for those questions to cite
(`grounding()`), and writes up to `NOTES_PER_NIGHT` new notes, each with its
sources (a note without one is refused). The specialist's pages in `docs/specialists/` are rewritten after.

**How MIA uses it**: the `ask_specialist` tool answers from the workbooks (a
specialist named, or every one), with the note's sources and whether it's
confirmed; `python -m tools.specialists` lists, shows, confirms and runs them.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "work" / "specialists"
PAGES = ROOT / "docs" / "specialists"
NOTES_PER_NIGHT = 3
MAX_BODY = 1800
STATUSES = ("derived", "confirmed", "withdrawn")

COMMON_LIMITS = ("Every note says where it comes from; a claim without a source isn't written. When the right answer "
                 "depends on where someone lives (a code, a law, a licence), the note says so and names who to check "
                 "with. Nothing about a real person's private life.")


@dataclass(frozen=True)
class Specialist:
    """One worker for one area of what MIA knows: its charter, the skills and curriculum tracks it develops, the
    loops it watches, its limits, and the questions it starts from."""
    id: str
    name: str
    charter: str
    skills: tuple[str, ...] = ()  # her skill tree's categories
    tracks: tuple[str, ...] = ()  # core/curriculum.py
    loops: tuple[str, ...] = ()  # core/loops.py
    limits: str = ""
    starts_from: tuple[str, ...] = ()
    words: tuple[str, ...] = ()  # what a question about its area sounds like


SPECIALISTS: tuple[Specialist, ...] = (
    Specialist("construction", "Construction", "Building and fixing: carpentry, framing, concrete, plumbing, electrical, "
               "HVAC, roofing, drywall, finishing, tools, materials, estimating, and building codes and permits.",
               skills=("Construction",), limits="Work a code or a licence requires (structural, gas, electrical "
               "service, permits) is named as such, with who to call; safety first in every procedure.",
               starts_from=("How do you size a header for a load-bearing wall opening?",
                            "When does a project need a permit?", "How do you mix and cure concrete properly?"),
               words=("build", "frame", "framing", "concrete", "plumbing", "wiring", "drywall", "roof", "joist",
                      "stud", "permit", "code", "lumber", "deck", "foundation", "construction")),
    Specialist("homesteading", "Homesteading", "Growing and keeping: gardens, soil, seed starting, irrigation, "
               "hydroponics and aquaponics, chickens and other animals, preserving and storing food, and running a "
               "homestead through the seasons.", skills=("Homestead",),
               loops=(), limits="Food safety (canning, curing) follows tested guidance and says which; animal health "
               "beyond basics points to a vet.",
               starts_from=("What's a safe way to can low-acid vegetables?", "How do you keep hens laying in winter?",
                            "How do you build healthy soil in a new bed?"),
               words=("garden", "soil", "seed", "chicken", "hen", "egg", "compost", "canning", "harvest", "goat",
                      "aquaponic", "hydroponic", "homestead", "livestock", "preserv")),
    Specialist("radio", "Radio and communications", "Radio and how things talk: amateur (ham) radio and its licences, "
               "GMRS and FRS, Meshtastic and LoRa mesh, antennas and propagation, SDR, and keeping in touch without "
               "the internet or cell service.", skills=("Technology",), loops=("phone.link",),
               limits="Transmitting follows the licence and the band plan where it happens, and the note says which "
               "licence a thing needs; listening and receiving are described, never jamming or interference.",
               starts_from=("What licence does each kind of two-way radio need in the US?",
                            "How far can a Meshtastic node reach, and what improves it?",
                            "How do you build a simple dipole antenna for 2 metres?"),
               words=("radio", "ham", "antenna", "meshtastic", "lora", "gmrs", "frs", "frequency", "band", "sdr",
                      "repeater", "transmit", "callsign")),
    Specialist("strategy", "Strategy and preparedness", "Military history and strategy as ways of thinking: planning, "
               "logistics, decision making under pressure (the OODA loop), reading terrain and maps, leadership, and "
               "preparing a household for storms, outages and emergencies.", skills=("Social", "Outdoor"),
               limits="Strategy as history, principles, planning, logistics and protecting a household: never how to "
               "hurt people, make or modify weapons, or target anyone.",
               starts_from=("What is the OODA loop and how does it apply to everyday decisions?",
                            "How does a household plan for a week without power?",
                            "What did Sun Tzu mean by knowing yourself and your enemy?"),
               words=("strategy", "military", "tactic", "logistics", "ooda", "preparedness", "emergency", "plan",
                      "sun tzu", "clausewitz", "battle", "campaign", "contingency")),
    Specialist("maker", "Making and fabrication", "Making things: 3D printing, CAD, woodworking, metalwork, "
               "electronics and microcontrollers, laser engraving, prototyping.", skills=("Maker", "Technology"),
               limits="Mains electricity and pressure systems are named as dangerous, with the safe way.",
               starts_from=("How do you choose a 3D-printing filament for an outdoor part?",
                            "How do you wire a sensor to an ESP32?"),
               words=("3d print", "cad", "solder", "arduino", "esp32", "laser", "cnc", "weld", "prototype",
                      "filament", "woodwork")),
    Specialist("outdoors", "Outdoors and fieldcraft", "Being out there: navigation by map and compass and grid, "
               "hiking, camping, survival skills, weather, water, first aid in the field.", skills=("Outdoor",),
               limits="First aid is first aid: anything serious says to get emergency help.",
               starts_from=("How do you navigate with a map, a compass and MGRS?", "How do you make water safe to drink?"),
               words=("hike", "camp", "compass", "navigation", "survival", "trail", "weather", "fire", "shelter",
                      "first aid", "mgrs")),
    Specialist("research", "Research", "Finding out: how to search, judge a source, check a claim against a second "
               "one, read a study, and keep what was learned with where it came from. It answers the other "
               "specialists' open questions when they need digging.", skills=("Mind",),
               limits="Says how strong the evidence is, and never presents one source as settled.",
               starts_from=("How do you tell a reliable source from an unreliable one?",
                            "How do you read a scientific study's results honestly?"),
               words=("research", "source", "study", "evidence", "citation", "fact check", "paper")),
    Specialist("testing", "Testing and auditing", "Proving things work and finding where they don't: her tests, her "
               "weekly self-audit, security reviews and pen testing on herself, and the curriculum's testing and "
               "security tracks.", skills=("Technology",), tracks=("testing", "security", "pentest"),
               loops=("dev.audit_code", "dev.connected", "dev.suite", "dev.vulnerable"),
               limits="Security testing is on MIA herself only (core/curriculum.SECURITY_RULES).",
               starts_from=("Which of her endpoints have no test that they refuse a stranger?",
                            "What makes a test flaky, and how do you make it steady?"),
               words=("test", "audit", "bug", "security", "pentest", "vulnerab", "flaky", "regression")),
    Specialist("engineering", "Software and AI engineering", "Building her: software engineering, web pages and apps, "
               "deploying, monitoring, documentation, and making her own models (DEC-0106).",
               skills=("Technology", "Mind"), tracks=("engineering", "documentation", "design", "web", "apps",
                                                      "deploying", "monitoring"),
               loops=("models.router_shadow", "dev.docs", "dev.loop_coverage"),
               limits="Changes go through the lab and Zac approves them.",
               starts_from=("How should a small router model be evaluated before it's used?",),
               words=("code", "software", "python", "deploy", "model", "api", "web page", "app", "programming")),
)

BY_ID = {s.id: s for s in SPECIALISTS}


# ------------------------------------------------------------------ the workbooks

def _book_path(sid: str, folder: Path = BOOKS) -> Path:
    """Where a specialist's workbook lives."""
    return Path(folder) / f"{sid}.json"


def book(sid: str, folder: Path = BOOKS) -> dict:
    """A specialist's workbook: its notes, its open questions (the charter's starting ones until it has its own),
    and when it last studied. A missing or unreadable workbook starts fresh."""
    spec = BY_ID[sid]
    try:
        data = json.loads(_book_path(sid, folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {"notes": list(data.get("notes") or []),
            "questions": list(data.get("questions") if "questions" in data else spec.starts_from),
            "studied": str(data.get("studied") or "")}


def _save(sid: str, data: dict, folder: Path = BOOKS) -> None:
    """Writes a workbook atomically."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    atomic_write_text(_book_path(sid, folder), json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def add_note(sid: str, title: str, body: str, sources: list[str], by: str = "mia", status: str = "derived",
             answers: str = "", folder: Path = BOOKS) -> dict:
    """Keeps one note in a specialist's workbook: refused (ValueError) without a title, a body or a source, as a
    repeat of a live note's title, or longer than MAX_BODY. A note that answers an open question takes it off the
    list."""
    if sid not in BY_ID:
        raise ValueError(f"No specialist {sid!r}.")
    title, body = " ".join((title or "").split())[:120], (body or "").strip()
    sources = [" ".join(str(s).split())[:300] for s in sources or [] if str(s).strip()]
    if not title or not body:
        raise ValueError("A note needs a title and what it says.")
    if not sources:
        raise ValueError("Every note says where it comes from.")
    if len(body) > MAX_BODY:
        raise ValueError(f"A note is at most {MAX_BODY} characters; split it.")
    if status not in STATUSES[:2]:
        raise ValueError("A new note is derived or confirmed.")
    data = book(sid, folder)
    if any(n["title"].lower() == title.lower() and n["status"] != "withdrawn" for n in data["notes"]):
        raise ValueError(f"There's already a note called {title!r}.")
    note = {"id": uuid.uuid4().hex[:8], "title": title, "body": body, "sources": sources, "status": status, "by": by,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    data["notes"].append(note)
    if answers:
        data["questions"] = [q for q in data["questions"] if q.strip().lower() != answers.strip().lower()]
    _save(sid, data, folder)
    return note


def add_question(sid: str, question: str, folder: Path = BOOKS) -> None:
    """Adds an open question for a specialist to study (a repeat is ignored)."""
    question = " ".join((question or "").split())[:300]
    data = book(sid, folder)
    if question and question.lower() not in {q.lower() for q in data["questions"]}:
        data["questions"].append(question)
        _save(sid, data, folder)


def _mark(sid: str, note_id: str, status: str, why: str = "", folder: Path = BOOKS) -> dict:
    """Sets a note's status (with why, for a withdrawal); ValueError when it isn't there."""
    data = book(sid, folder)
    note = next((n for n in data["notes"] if n["id"] == note_id), None)
    if note is None:
        raise ValueError(f"No note {note_id} for {sid}.")
    note["status"] = status
    if why:
        note["why"] = why[:300]
    _save(sid, data, folder)
    return note


def confirm(sid: str, note_id: str, folder: Path = BOOKS) -> dict:
    """A person read the note and its sources and says it's right."""
    return _mark(sid, note_id, "confirmed", folder=folder)


def withdraw(sid: str, note_id: str, why: str, folder: Path = BOOKS) -> dict:
    """The note is wrong: kept, so it isn't written again, and never used."""
    return _mark(sid, note_id, "withdrawn", why, folder)


# ------------------------------------------------------------------ answering

def _words(text: str) -> set[str]:
    """Pure logic. A text's words, small ones left out, with a crude stem."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(w) > 2 and w not in {"the", "and", "for", "how", "what", "you", "does", "with", "can", "your", "are"}:
            out.add(w[:-1] if len(w) > 4 and w.endswith("s") else w)
    return out


def who_knows(question: str) -> list[Specialist]:
    """Pure logic. The specialists whose area a question sounds like, best first."""
    q = (question or "").lower()
    scored = [(sum(1 for w in s.words if w in q), s) for s in SPECIALISTS]
    return [s for n, s in sorted(scored, key=lambda x: -x[0]) if n]


def search(question: str, sid: str = "", folder: Path = BOOKS, limit: int = 3) -> list[tuple[float, str, dict]]:
    """The live notes that best answer a question (in one specialist's workbook, or every one), as (score,
    specialist, note); confirmed notes count a little more than derived ones."""
    want = _words(question)
    found = []
    for spec in ([BY_ID[sid]] if sid in BY_ID else SPECIALISTS):
        for note in book(spec.id, folder)["notes"]:
            if note["status"] == "withdrawn":
                continue
            have = _words(note["title"]) | _words(note["body"])
            hits = len(want & have)
            if hits:
                score = hits / max(1, len(want)) + 0.5 * len(want & _words(note["title"])) / max(1, len(want))
                found.append((round(score * (1.2 if note["status"] == "confirmed" else 1.0), 3), spec.id, note))
    found.sort(key=lambda x: -x[0])
    return found[:limit]


def answer(question: str, sid: str = "", folder: Path = BOOKS) -> str:
    """What MIA's specialists know about a question, in plain words: the best note, its sources, and whether a
    person has confirmed it; or that no specialist has a note on it yet (and the question is added for the one
    whose area it is, to study)."""
    found = search(question, sid, folder)
    if not found:
        area = BY_ID.get(sid) or next(iter(who_knows(question)), None)
        if area is not None:
            add_question(area.id, question, folder)
            return (f"My {area.name.lower()} specialist doesn't have a note on that yet; I've added it to what it "
                    "studies next.")
        return "None of my specialists has a note on that yet."
    _score, spec_id, note = found[0]
    status = "confirmed by a person" if note["status"] == "confirmed" else "written by a model, not confirmed yet"
    return (f"From my {BY_ID[spec_id].name.lower()} specialist ({status}): {note['title']}. {note['body']} "
            f"Sources: {'; '.join(note['sources'])}.")


# ------------------------------------------------------------------ studying (Night School)

STUDY_PROMPT = """You are writing notes for one of MIA's specialists: a worker that develops and maintains one area of
what MIA (a personal assistant) knows. Notes are kept in its workbook and MIA answers questions from them.

The specialist: {name}. What it covers: {charter}
Its limits: {limits} {common}

Its open questions (answer some of these first):
{questions}

From MIA's own offline reference library (prefer these; cite one as "Reference library: <pack>, '<article>'"):
{library}

Notes it already has (don't repeat them):
{titles}

Reply with only a JSON object:
{{"notes": [up to {count} of {{
    "title": "short",
    "body": "the note itself: clear, practical, correct, in plain words, at most {max_body} characters",
    "sources": ["where it comes from: a book with its author, a standard or code with its number, an official page,
                 a reference work; at least one, real ones only"],
    "answers": "the open question it answers, word for word, or empty"}}],
 "questions": ["up to 3 new questions this specialist should study next"]}}"""


def next_to_study(folder: Path = BOOKS) -> Specialist:
    """The specialist that studied longest ago (never first, in the charter's order)."""
    return min(SPECIALISTS, key=lambda s: (book(s.id, folder)["studied"], SPECIALISTS.index(s)))


def _library_search() -> Optional[Callable[[str, int], list]]:
    """Her offline reference library's search across every pack (core/reference_library_manager.py), or None when
    it can't be opened here."""
    try:
        from core.app_context import AppContext
        from core.config_manager import ConfigManager
        from core.event_bus import EventBus
        from core.reference_library_manager import ReferenceLibraryManager

        library = ReferenceLibraryManager(AppContext(config=ConfigManager(), events=EventBus()))
        return library.search_all_packs if library.list_packs() else None
    except Exception:
        return None


def grounding(questions: list[str], search: Optional[Callable[[str, int], list]], per_question: int = 2,
              chars: int = 600) -> str:
    """Excerpts from her reference library for a specialist's first open questions, each labelled with its pack and
    article so a note can cite it; "(no reference packs installed)" without a library or a hit."""
    if search is None:
        return "(no reference packs installed)"
    lines = []
    for q in questions[:3]:
        try:
            hits = search(q, per_question)
        except Exception:
            continue
        for h in hits:
            lines.append(f"- {h.pack_title}, '{h.article_title}' (for: {q}): {' '.join(h.snippet.split())[:chars]}")
    return "\n".join(lines) or "(nothing in the reference packs for these questions)"


def study(ask: Callable[[str], str], sid: str = "", folder: Path = BOOKS, pages: Optional[Path] = PAGES,
          count: int = NOTES_PER_NIGHT, search: Optional[Callable[[str, int], list]] = None,
          use_library: bool = True) -> dict:
    """One study session for a specialist (the next in turn unless named): its teacher (`ask`, a prompt in and the
    reply out) writes notes from its charter and open questions, given excerpts from her offline reference library
    to cite when it has packs (`search`, else found here unless use_library is False); each valid note is kept as
    derived, a bad one is counted and skipped; new questions are added. Returns what happened."""
    from core.night_school import _json_in

    spec = BY_ID[sid] if sid else next_to_study(folder)
    data = book(spec.id, folder)
    live = [n["title"] for n in data["notes"] if n["status"] != "withdrawn"]
    if search is None and use_library:
        search = _library_search()
    said = _json_in(ask(STUDY_PROMPT.format(
        name=spec.name, charter=spec.charter, limits=spec.limits, common=COMMON_LIMITS,
        questions="\n".join(f"- {q}" for q in data["questions"][:8]) or "(none: choose what matters most)",
        library=grounding(data["questions"], search),
        titles="\n".join(f"- {t}" for t in live[-40:]) or "(none yet)", count=count, max_body=MAX_BODY)))
    kept, refused = [], []
    for raw in (said.get("notes") or [])[:count]:
        try:
            note = add_note(spec.id, str(raw.get("title", "")), str(raw.get("body", "")), list(raw.get("sources") or []),
                            by="teacher", answers=str(raw.get("answers") or ""), folder=folder)
            kept.append(note["title"])
        except (ValueError, AttributeError, TypeError) as problem:
            refused.append(str(problem)[:120])
    for q in (said.get("questions") or [])[:3]:
        add_question(spec.id, str(q), folder)
    data = book(spec.id, folder)
    data["studied"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save(spec.id, data, folder)
    if pages is not None:
        write_pages(pages, folder)
    return {"specialist": spec.id, "kept": kept, "refused": refused}


# ------------------------------------------------------------------ their pages

def render(spec: Specialist, data: dict) -> str:
    """A specialist's page: its charter, limits, what it develops, its confirmed notes, its unconfirmed ones, and
    its open questions."""
    live = [n for n in data["notes"] if n["status"] != "withdrawn"]
    lines = [f"# {spec.name}", "",
             "*One of MIA's specialists (DEC-0109). Written by `core/specialists.py` from its workbook "
             f"(`work/specialists/{spec.id}.json`); don't edit by hand.*", "", spec.charter, "",
             f"**Limits:** {spec.limits} {COMMON_LIMITS}", ""]
    develops = [f"skills: {', '.join(spec.skills)}" if spec.skills else "",
                f"curriculum: {', '.join(spec.tracks)}" if spec.tracks else "",
                f"loops: {', '.join(spec.loops)}" if spec.loops else ""]
    if any(develops):
        lines += ["**Develops:** " + "; ".join(d for d in develops if d) + ".", ""]
    for heading, status in (("Notes, confirmed", "confirmed"), ("Notes, not confirmed yet", "derived")):
        these = [n for n in live if n["status"] == status]
        if these:
            lines += [f"## {heading}", ""]
            for n in these:
                lines += [f"### {n['title']}", "", n["body"], "", "Sources: " + "; ".join(n["sources"]), ""]
    if data["questions"]:
        lines += ["## Open questions", ""] + [f"- {q}" for q in data["questions"]] + [""]
    return "\n".join(lines)


def write_pages(out: Path = PAGES, folder: Path = BOOKS) -> str:
    """Writes every specialist's page and the index; returns a line saying what it wrote."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in SPECIALISTS:
        data = book(spec.id, folder)
        atomic_write_text(out / f"{spec.id}.md", render(spec, data))
        live = [n for n in data["notes"] if n["status"] != "withdrawn"]
        rows.append((spec, sum(n["status"] == "confirmed" for n in live), len(live), len(data["questions"])))
    index = ["# MIA's specialists", "", "*Workers that develop and maintain one area of what MIA knows (DEC-0109). "
             "Written by `core/specialists.py`.*", ""]
    index += [f"- [{s.name}]({s.id}.md): {n} notes ({c} confirmed), {q} open questions" for s, c, n, q in rows]
    atomic_write_text(out / "README.md", "\n".join(index) + "\n")
    return f"{len(rows)} specialists, {sum(r[2] for r in rows)} notes"


# ------------------------------------------------------------------ the Assistant's tool

def _action_ask(context, arguments: dict) -> str:
    """Tool ask_specialist: what her specialists know about a question (one named, or whichever's area it is)."""
    question = str(arguments.get("question") or "").strip()
    if not question:
        return "What should I ask?"
    named = str(arguments.get("specialist") or "").strip().lower()
    sid = next((s.id for s in SPECIALISTS if named and (named in s.id or named in s.name.lower())), "")
    return answer(question, sid)


def register_specialist_actions(registry) -> None:
    """Registers the ask_specialist tool."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="ask_specialist", domain="knowledge",
        description=("Ask one of MIA's specialists (construction, homesteading, radio, strategy and preparedness, "
                     "making, outdoors, research, testing, engineering) what its workbook says about a question, "
                     "with its sources and whether a person has confirmed it."),
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "The question, in their words."},
            "specialist": {"type": "string", "description": "Which specialist, only if they named one."}},
            "required": ["question"]},
        handler=_action_ask, prompt_arg="question",
        trigger_phrases=("ask your specialist", "ask the specialist", "your construction specialist",
                         "your radio specialist", "your homesteading specialist", "your strategy specialist",
                         "what do your specialists", "ask the expert", "specialist say"),
        subjects=("specialist", "expert"),
    ))
