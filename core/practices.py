"""
core.practices
================

MIA's best practices, a series that keeps growing (DEC-0108; Zac, 2026-11-07:
"MIA should have some kind of understanding of best practices for AI
building, development of any kind, honestly everything she does she should
have an evolving best practices series of documentation").

One document per area in `docs/practices/` (AI building, development,
testing, security and privacy, design, documentation, interconnection,
monitoring, operations, working as a team), each in two parts:

1. **Principles**: the practices that hold, each with why, written here
   (`AREAS`). They change when the team learns better; edit them here.
2. **Learned building her**: every confirmed entry in the Knowledge Vault
   (`work/knowledge/`, DEC-0105) about that area, gathered when the series
   is written, newest first, so a lesson learned on Tuesday is in the
   practices by the next audit. MIA's own write-ups that nobody has
   confirmed yet are listed apart, as unconfirmed.

An entry belongs to an area when the files it concerns or its words match
the area's (`belongs()`); one entry can teach several areas. The series is
written by the weekly self-audit (core/self_audit.py) and by
`python -m core.practices`. MIA answers from it (core/self_docs.py reads
docs/). Never edit `docs/practices/` by hand: it's written from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "practices"


@dataclass(frozen=True)
class Area:
    """One area of practice: its id and title, the principles that hold (each "what. why."), and what marks a
    knowledge entry as being about it (file paths it concerns, words in it)."""
    id: str
    title: str
    principles: tuple[str, ...]
    paths: tuple[str, ...] = ()
    words: tuple[str, ...] = ()


AREAS: tuple[Area, ...] = (
    Area("ai_building", "Building AI", (
        "Facts come from code; a model only phrases them. A model's memory is not a source, and a number it wasn't "
        "given is a guess.",
        "Measure before changing anything: decide how a model will be judged, on data it never saw, before "
        "building it.",
        "Keep three sets apart: what a model learns from, what its settings are chosen on, and what its score is "
        "reported on. A score is only true for data that had no say in building it.",
        "Start with the simplest model that could work, and compare it with what's used now. A bigger model has to "
        "earn its cost.",
        "Every model has a card: what it is, what it learned from, what it was tested on, its scores, its limits, "
        "and what it serves.",
        "A model is judged by the problem it was made for, not only its test score: the loop it serves has to get "
        "better.",
        "Shadow before serving: a new model runs beside the current way on real requests, and goes in only when it "
        "wins there and a person approves. Keep the way back.",
        "Small models for narrow jobs (routing, sorting, reading a field, a forecast); a large model for open "
        "language.",
        "Text from outside (a document, an email, a web page) is data, never instructions: it can't make her take "
        "an action without a person's approval.",
        "Learn only from data she's allowed to: a person's words stay theirs, on their device, and never train "
        "anything shared without their say.",
        "Say how sure she is, and check it later (calibration); never claim an ability that wasn't measured.",
        "Same data, same model: no hidden randomness, versions recorded, so a result can be reproduced.",
        "Small differences on a small test set are noise; the cure is more held-out data, not more tuning.",
    ), paths=("core/model_forge.py", "core/llm", "core/local_model.py", "core/self_docs.py", "core/assistant_chat.py",
              "core/mia_coder.py", "core/benchmarks.py", "core/sight.py"),
       words=("model", "router", "llm", "prompt", "training", "held-out", "benchmark", "fine-tun")),
    Area("growth", "Learning and growth", (
        "Every desire is worked the same way (DEC-0112): understand it, plan the steps, teach, practise and log, "
        "homework as missions, statistics, verify by evidence, then the next stage. For a person and for MIA herself.",
        "Understand the desire first: the goal in their own words, and how much time they really have.",
        "Plan in stages small enough to finish, each ending in checks that prove it; a stage opens when the last "
        "one's checks pass.",
        "A skill counts when it's shown, not claimed: verify in code where possible (heard, measured), counted "
        "against a mark next, said only for what can't be measured yet, and the record says which.",
        "Progress comes from the log: missions take their numbers from what was done, never from a box ticked.",
        "Teach the next step for where they are, with why and the mistakes to watch for; never a wall of everything.",
        "Statistics say the truth gently: the week against the plan, the streak, the bests; a missed week is shown, "
        "never scolded.",
        "A plan she drafts is a proposal: grounded in what her specialists know, checked in code, started only when "
        "the person says so, and always said to be drafted.",
    ), paths=("core/paths.py", "core/guitar.py", "core/guitar_ear.py", "core/curriculum.py", "core/night_school.py",
              "core/assistant_path_actions.py"),
       words=("learn", "teach", "practice", "practise", "skill check", "path", "curriculum", "homework")),
    Area("development", "Software development", (
        "Read before writing: what the code takes, returns and does at its edges.",
        "The smallest change that does the job, matching the code around it: its naming, comment density and idiom.",
        "Keep the layers: core knows nothing of gui or modules; modules never import each other; the GUI talks to "
        "modules only through their contract.",
        "Pure logic where possible (no clock, file or network inside), with those passed in: it's what can be "
        "tested and trusted.",
        "One source of truth: derive what can be derived instead of storing a second copy that can drift.",
        "Stores write through atomic_write_text, so a crash never leaves half a file, undo can restore it, and the "
        "web knows to re-read.",
        "Cheap to construct, expensive work later: a module's __init__ runs every boot.",
        "Delete what isn't used; a second copy of the same code is two places to fix.",
    ), paths=("core/application.py", "core/module_manager.py", "core/app_context.py", "core/atomic_write.py",
              "docs/ARCHITECTURE.md"), words=("refactor", "architecture", "layering", "duplicat", "efficien")),
    Area("testing", "Testing and debugging", (
        "A test fails for the right reason before the change and passes after it; one that already passes proves "
        "nothing.",
        "Fix the code, not the test, unless the test is what's wrong; never skip or disable a test to get green.",
        "Change only what the failing test needs; leave passing tests alone unless the task names them.",
        "Pass in what's hard to control (the date, the folder, another service) so it can be tested.",
        "The full suite runs before anything is merged, and a new failure anywhere stops it.",
        "Read a traceback from the bottom up, and fix the cause, not the symptom.",
        "A check in a chain must fail loudly: a script that prints a problem and exits 0 hides it.",
    ), paths=("tests/",), words=("test", "pytest", "suite", "debug", "traceback", "flaky")),
    Area("security", "Security and privacy", (
        "Each person's data is their own (their folder); nothing is shared without a household's approval.",
        "Every endpoint and action checks who is asking, and an action runs as the person who approved it.",
        "Validate input where it enters: a path, a command, a query or a page never takes raw text.",
        "Secrets never in code or logs; logs are redacted (core/failure_log.redact).",
        "She proposes; a person approves. She never sends an email, pays or signs herself.",
        "Dependencies are audited weekly, and a known vulnerability is fixed, not waited out.",
        "Security testing is on herself only: her own code in the lab, her own server in-process, never anyone "
        "else's system.",
    ), paths=("server/", "core/actions.py", "core/password_vault.py", "core/child_accounts.py", "core/safety_floor.py"),
       words=("security", "vulnerab", "token", "auth", "privacy", "secret", "injection", "redact")),
    Area("design", "Design and user experience", (
        "One look: the theme's tokens (web/tokens.css), never a hard-coded colour.",
        "What a person came for comes first; detail can wait a tap.",
        "Every control has a label and a role, contrast is enough, and the keyboard works.",
        "Plain, short, kind words that never blame the person (docs/design/MIA_VOICE.md).",
        "Logic lives in core; a page only draws what core assembled.",
    ), paths=("web/", "docs/design/", "gui/"), words=("screen", "page", "design", "accessib", "layout", "css")),
    Area("documentation", "Documentation", (
        "Every file says what it is, what it does and how; every class, function and method has a docstring "
        "(DEC-0104).",
        "A docstring is a claim about the code: check it against the code. When they disagree, the code is right.",
        "Docs change with the code, in the same commit (DEC-0110): a function whose behaviour changed gets its "
        "docstring changed with it; python -m tools.docs stale lists the ones that may have been missed. Generated "
        "docs are regenerated, never hand-edited.",
        "Write why, not only what: the reasons and the mistakes go in the Knowledge Vault (DEC-0105).",
        "A guide is for someone who wasn't there: steps in order, an example, what can go wrong.",
        "In a docstring, describe escapes in words; a backslash is read as code.",
    ), paths=("docs/", "tools/docs.py", "core/code_atlas.py", "core/dev_knowledge.py"),
       words=("docstring", "document", "guide", "atlas", "knowledge entry")),
    Area("interconnection", "Interconnection", (
        "One shared context (AppContext) carries every service; no global, no ad-hoc import.",
        "Parts react to each other through the event bus, never by importing each other.",
        "Things relate by reference (kind:id) in links, never by copying a record.",
        "A meaningful change is recorded as a life event, so her history and the Chronicle see it.",
        "Her picture of a life (the life state) is derived from the stores, never stored beside them.",
        "Every store is considered for five connections: history, links, voice, the life state and a web page; one "
        "it goes without on purpose says why (BY_DESIGN in core/self_audit.py).",
        "An event that's published and never heard, or heard and never published, is a connection unmade or dead "
        "code.",
    ), paths=("core/links.py", "core/event_bus.py", "core/life_events.py", "core/context_assembler.py",
              "core/self_audit.py"), words=("interconnect", "event", "link", "life state", "life event")),
    Area("monitoring", "Monitoring", (
        "Every process has a loop that watches it, or a written reason it needs none.",
        "A loop judges only with enough readings (min_n); one reading against her usual isn't a trend.",
        "A slipping loop opens a task (or offers it, or shows it): watching without acting changes nothing.",
        "Nothing personal in a log or a loop's detail: numbers and kinds only.",
        "Watch the watchers: loop coverage is itself a loop.",
    ), paths=("core/loops.py", "core/loop_coverage.py", "core/dev_checks.py"),
       words=("loop", "monitor", "floor", "signal", "noise")),
    Area("operations", "Deploying and running", (
        "An install says what it needs (packages, settings, start-up) and is safe to run twice.",
        "Defaults are versioned and never overwritten; a person's settings are merged over them.",
        "CI runs what a contributor would run: the tests, the install, the phone build.",
        "A backup is only real once a restore from it has worked.",
        "New code runs only after a restart: say so when it matters.",
    ), paths=("deploy/", ".github/", "tools/pc_check.py", "core/backup_manager.py", "requirements.txt"),
       words=("deploy", "install", "ci", "restart", "backup", "release")),
    Area("teamwork", "Working as a team", (
        "Every piece of work is a task with where it came from; a decision is written down, and only Zac approves "
        "one.",
        "Changes go through the lab: written, tested in a copy, reviewed by someone other than the author, then "
        "approved.",
        "Never rewrite someone else's history; stage only your own changes when others are working too.",
        "Say plainly what was done, what wasn't, and what failed; a skipped step is reported, not hidden.",
        "Keep the running lists current (NEXT_SESSION, WAITING_ON) so nothing waits on a memory nobody has.",
    ), paths=("core/work_", "core/council.py", "core/dev_lab.py", "docs/DECISIONS.md", "docs/WAITING_ON.md"),
       words=("review", "task", "lab", "council", "approve", "decision")),
)


def belongs(entry: dict, area: Area) -> bool:
    """Pure logic. Whether a knowledge entry teaches this area: a file it concerns starts with one of the area's
    paths, or one of the area's words is in its title."""
    raw = entry.get("concerns") or []
    concerns = [str(c).strip() for c in (raw if isinstance(raw, (list, tuple)) else str(raw).split(",")) if str(c).strip()]
    if any(c.startswith(p) for c in concerns for p in area.paths):
        return True
    title = str(entry.get("title") or "").lower()
    return any(w in title for w in area.words)


def _first_sentence(text: str, limit: int = 220) -> str:
    """Pure logic. An entry's opening, one line: its first sentence, cut to a limit."""
    line = " ".join((text or "").split())
    for label in ("What happened:", "What:"):
        if line.startswith(label):
            line = line[len(label):].strip()
    end = line.find(". ")
    if 0 < end < limit:
        return line[: end + 1]
    return line if len(line) <= limit else line[:limit].rsplit(" ", 1)[0] + "…"


def render(area: Area, entries: list[dict]) -> str:
    """One area's document: its principles, then what was learned building her (confirmed entries, newest first),
    then her own unconfirmed write-ups."""
    live = [e for e in entries if e.get("status") not in ("superseded", "withdrawn") and belongs(e, area)]
    live.sort(key=lambda e: str(e.get("created") or ""), reverse=True)
    confirmed = [e for e in live if e.get("status") == "confirmed"]
    derived = [e for e in live if e.get("status") == "derived"]
    lines = [f"# Best practices: {area.title}", "",
             "*Written by `core/practices.py` (DEC-0108) from its principles and the Knowledge Vault; regenerated by "
             "the weekly self-audit. Don't edit by hand: change the principles in `core/practices.py`, or add what "
             "was learned to the vault.*", "", "## Principles", ""]
    lines += [f"{i}. {p}" for i, p in enumerate(area.principles, 1)]
    lines += ["", "## Learned building her", ""]
    lines += [f"- **{e.get('title')}** ({e['id']}): {_first_sentence(e.get('body', ''))}" for e in confirmed] or \
             ["- Nothing in the vault for this area yet."]
    if derived:
        lines += ["", "## Her own write-ups, not confirmed yet", ""]
        lines += [f"- {e.get('title')} ({e['id']}): {_first_sentence(e.get('body', ''))}" for e in derived]
    return "\n".join(lines) + "\n"


def index(counts: dict[str, int]) -> str:
    """The series' front page: every area with how many lessons it holds."""
    lines = ["# Best practices", "",
             "*MIA's evolving best practices (DEC-0108), one document per area: principles that hold, and what was "
             "learned building her, gathered from the Knowledge Vault. Written by `core/practices.py`.*", ""]
    lines += [f"- [{a.title}]({a.id}.md): {len(a.principles)} principles, {counts.get(a.id, 0)} "
              f"lesson{'' if counts.get(a.id, 0) == 1 else 's'} learned" for a in AREAS]
    return "\n".join(lines) + "\n"


def write(out: Path = OUT, folder=None) -> str:
    """Writes the whole series from the principles and the vault's entries; returns a line saying what it wrote."""
    from core.dev_knowledge import KNOWLEDGE, entries

    found = entries(folder or KNOWLEDGE)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for area in AREAS:
        text = render(area, found)
        counts[area.id] = text.count("\n- **")
        atomic_write_text(out / f"{area.id}.md", text)
    atomic_write_text(out / "README.md", index(counts))
    return f"{len(AREAS)} areas, {sum(counts.values())} lessons placed"


if __name__ == "__main__":
    print(write())
