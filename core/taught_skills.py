"""
core.taught_skills
====================

Taught skills, phase 1 (DEC-0123, approved 2026-11-15; part of MIA's one
skills system, DEC-0167; the proposal is `docs/PROCEDURES_PROPOSAL.md`):
something the person teaches MIA once, made of things she can already do,
that she practises with them watching until it's proven.

**A taught skill** (`Skill`) has a name, ordered **steps** and a
**practice state**. A step is one of:
- `tool`: one of her own tools, with its arguments (what she does when
  asked in conversation);
- `action`: an action kind with its parameters (what a screen's button
  does);
- `ask`: a question to the person; the answer gets a name and later steps
  can use it as `{name}`;
- `you`: something only the person can do; she waits for "done";
- `tell`: something she says.

Browser steps, schedules and events, phone and desktop steps are later
phases; nothing here pretends to do them.

**Taught two ways** (phase 1):
- **By watching** ("watch me: the Friday reset"). While she's watching,
  every tool she runs for the person in conversation and every change the
  person approves on a screen is noted as a step (`observe_tool`,
  `observe_action`). "That's it" keeps the skill.
- **By telling**: the steps written as lines (`parse_steps`), one a line:
  `tell: ...`, `ask: question -> name`, `you: ...`, `tool: name key=value`,
  `action: kind key=value`.

**Every step goes through the gate it already has.** Nothing here decides
what's safe:
- A `tool` step runs through the tool registry, which applies its own
  rules and records the change for undo.
- An `action` step runs through the action contract (propose, then
  approve), so it's checked, credited and undoable.

While a skill is **practising**, each step that changes something waits
for the person's yes, with the sentence the action itself writes. When
its last `CLEAN_RUNS` watched runs both finished cleanly it is
**learned**, and those steps stop asking. The exceptions always ask,
learned or not: paying, buying, sending, publishing, deleting and profile
changes. That is decided three ways, all in code: by the action kind
(`always_asks`), by the tool's name or its destructive mark
(`_needs_yes`), and, for a tool whose name doesn't say what it does, at
the moment it reaches for such an action (`guard`, called by
`core.actions.run_as_tool` and `ActionCenter.approve`): the action is refused, the person is asked,
and the step runs again on their yes.

**Demotion.** A run that stops on an error sends a learned skill back to
practising; so does changing its steps.

**In conversation** (`take_turn`, called by `core/assistant_turn.py`
after the safety floor, never in a private turn): "watch me: <name>",
"that's it", "run <a skill's name>", and the answer to the question a
run just asked are handled in code, not by the model.

**A run** (`Run`) is kept with the skill book, so a question can wait for
its answer across turns and devices. One runs at a time for a person.
`start()` and `answer()` advance it until it needs the person or ends,
and return what she said along the way.

`SkillBook` is the person's store (taught_skills.json in their folder,
written through atomic_write_text so "undo that" restores it).
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import re
import uuid
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
_FILE = "taught_skills.json"

STEP_KINDS = ("tool", "action", "ask", "you", "tell")
PRACTISING, LEARNED = "practising", "learned"
CLEAN_RUNS = 2  # watched runs in a row that must finish cleanly before a skill is learned
MAX_STEPS = 40
DOMAIN = "taught_skills"  # the tools that teach and run skills; never steps themselves

# Action kinds that ask every time, learned or not (the proposal: "never for money moves or sending").
_ALWAYS_ASK = re.compile(r"(\.pay$|\.buy$|\.send$|\.email$|\.publish$|\.delete$|share$|^freedom\.fund|^profile\."
                         r"|^browser\.commit|^taught_skill\.)")
# Tools that ask every time by their name (a tool's handler isn't an action kind, so its name is what's known).
_TOOL_ALWAYS = re.compile(r"(^|_)(pay|payment|paid|buy|purchase|spend|redeem|sell|send|email|publish|share|delete|remove"
                          r"|forget|clear|erase|wipe|unlink|cancel|undo|reset|transfer|order)(_|$)")
# Set while a skill runs a tool step the person hasn't said yes to: run_as_tool asks `guard` before each action.
_UNAPPROVED: ContextVar[Optional[dict]] = ContextVar("taught_skill_unapproved_step", default=None)
_NEEDS_YES = "needs your yes"
# What a tool says when it didn't work (core/assistant_actions.execute): a run stops there.
_TOOL_FAILED = ("Something on my side broke", "I got that mixed up on my end")
_NO = re.compile(r"^\s*(no|nope|stop|cancel|don'?t|never mind|skip it)\b", re.I)
_YES = re.compile(r"^\s*(yes|yeah|yep|ok|okay|sure|do it|go ahead|go on|please do|approved?)\b", re.I)


class SkillError(ValueError):
    """Something about a taught skill can't be done; its message is a plain sentence for the person."""


def _now() -> str:
    """The time now, as stored."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Skill:
    """One taught skill: its name, what it's for, the steps, its practice state (practising or learned), how many
    watched runs in a row finished cleanly, how many times it ran, how the last run ended, and where it was learned
    from (a note, or the source of a selection)."""
    skill_id: str
    name: str
    about: str = ""
    steps: list = field(default_factory=list)
    state: str = PRACTISING
    clean_runs: int = 0
    runs: int = 0
    last_run: str = ""
    last_result: str = ""
    source: str = ""
    created_at: str = ""


@dataclass
class Run:
    """A skill being run: which skill, the step it's at, the answers so far, what she's said, what she's waiting
    for (None, or {"kind": ask / you / confirm, "text": ...}), whether the person is watching, and whether it has
    gone cleanly so far."""
    run_id: str
    skill_id: str
    at: int = 0
    answers: dict = field(default_factory=dict)
    said: list = field(default_factory=list)
    waiting: Optional[dict] = None
    watched: bool = True
    clean: bool = True
    started: str = ""


def always_asks(kind: str) -> bool:
    """Pure logic. Whether an action kind asks every time, even in a learned skill: paying, buying, sending,
    publishing, deleting, profile changes, a browser's commit, and the skill actions themselves."""
    return bool(_ALWAYS_ASK.search(str(kind or "")))


def guard(kind: str) -> None:
    """Called by `core.actions.run_as_tool` and `ActionCenter.approve` before an action runs. While a skill is running a tool
    step the person hasn't said yes to, an action kind that always asks is refused here (and the run then asks):
    so a tool can't pay, send or delete inside a skill on the strength of its name alone."""
    held = _UNAPPROVED.get()
    if held is not None and always_asks(kind):
        from core.actions import ActionError

        held["blocked"] = kind
        raise ActionError("That step needs your yes first.")


# ---------------------------------------------------------------- steps


def _pairs(text: str) -> dict:
    """Pure logic. `key=value, key=value` (or a JSON object) as a dict; values that read as numbers or true/false
    become those."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            got = json.loads(text)
        except ValueError:
            raise SkillError("That step's values aren't readable: use key=value, key=value.") from None
        if not isinstance(got, dict):
            raise SkillError("That step's values aren't readable: use key=value, key=value.")
        return got
    out = {}
    for part in re.split(r",\s*(?=[A-Za-z_][A-Za-z0-9_]*\s*=)", text):
        if "=" not in part:
            raise SkillError(f"\"{part.strip()}\" isn't key=value.")
        key, value = part.split("=", 1)
        value = value.strip().strip('"')
        if re.fullmatch(r"-?\d+", value):
            value = int(value)
        elif re.fullmatch(r"-?\d+\.\d+", value):
            value = float(value)
        elif value.lower() in ("true", "false"):
            value = value.lower() == "true"
        out[key.strip()] = value
    return out


def parse_steps(text: str) -> list[dict]:
    """Pure logic. Steps written as lines, one a line (blank lines and a leading "1." or "-" are fine):
    `tell: words`, `ask: question -> name`, `you: what to do`, `tool: name key=value, ...`,
    `action: kind key=value, ...`. SkillError naming the line that can't be read."""
    steps = []
    for raw in str(text or "").splitlines():
        line = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", raw).strip()
        if not line:
            continue
        kind, _, rest = line.partition(":")
        kind, rest = kind.strip().lower(), rest.strip()
        if kind not in STEP_KINDS or not rest:
            raise SkillError(f"I can't read this step: \"{raw.strip()}\". Start it with tell:, ask:, you:, tool: "
                             f"or action:.")
        if kind == "tell":
            steps.append({"kind": "tell", "text": rest})
        elif kind == "you":
            steps.append({"kind": "you", "what": rest})
        elif kind == "ask":
            question, _, name = rest.partition("->")
            name = re.sub(r"\W+", "_", name.strip().lower()).strip("_") or f"answer{len(steps) + 1}"
            steps.append({"kind": "ask", "question": question.strip(), "as": name})
        else:
            name, _, values = rest.partition(" ")
            key = "tool" if kind == "tool" else "action"
            steps.append({"kind": kind, key: name.strip(), "arguments" if kind == "tool" else "params": _pairs(values)})
    return steps


def _plain(value) -> bool:
    """Pure logic. Whether a value reads back the same from `key=value` (else the step's values are written as
    JSON)."""
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return True
    return (isinstance(value, str) and value == value.strip() and bool(value) and "\n" not in value
            and '"' not in value and not re.search(r",\s*[A-Za-z_]\w*\s*=", value)
            and not re.fullmatch(r"-?\d+(\.\d+)?|true|false", value, re.I))


def format_steps(steps: list) -> str:
    """Pure logic. Steps as the lines `parse_steps` reads, for editing on the screen."""
    lines = []
    for s in steps:
        kind = s.get("kind")
        if kind == "tell":
            lines.append(f"tell: {s.get('text', '')}")
        elif kind == "you":
            lines.append(f"you: {s.get('what', '')}")
        elif kind == "ask":
            lines.append(f"ask: {s.get('question', '')} -> {s.get('as', '')}")
        else:
            values = s.get("arguments" if kind == "tool" else "params") or {}
            if all(_plain(v) for v in values.values()):
                tail = ", ".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in values.items())
            else:
                tail = json.dumps(values)
            lines.append(f"{kind}: {s.get('tool' if kind == 'tool' else 'action', '')} {tail}".rstrip())
    return "\n".join(lines)


def step_problems(context, steps: list) -> list[str]:
    """What's wrong with a list of steps, in words (none when they're sound): none or too many, an unknown kind, a
    tool or action kind MIA doesn't have, one of the skill tools or actions themselves (a skill can't teach or run
    skills), a question, task or sentence left empty."""
    from core.actions import ACTION_TYPES

    if not steps:
        return ["A skill needs at least one step."]
    if len(steps) > MAX_STEPS:
        return [f"A skill has at most {MAX_STEPS} steps."]
    registry = getattr(context, "assistant_actions", None)
    known = getattr(registry, "_actions", {}) if registry is not None else {}
    wrong = []
    for n, s in enumerate(steps, 1):
        kind = s.get("kind") if isinstance(s, dict) else None
        if kind not in STEP_KINDS:
            wrong.append(f"Step {n} isn't a kind of step I know.")
        elif kind == "tool":
            tool = known.get(str(s.get("tool") or ""))
            if tool is None:
                wrong.append(f"Step {n}: I don't have a tool called \"{s.get('tool')}\".")
            elif tool.domain == DOMAIN:
                wrong.append(f"Step {n}: a skill can't teach or run skills.")
        elif kind == "action":
            name = str(s.get("action") or "")
            if name not in ACTION_TYPES:
                wrong.append(f"Step {n}: I don't have an action called \"{name}\".")
            elif name.startswith("taught_skill."):
                wrong.append(f"Step {n}: a skill can't teach or run skills.")
        elif not str(s.get({"ask": "question", "you": "what", "tell": "text"}[kind]) or "").strip():
            wrong.append(f"Step {n} is empty.")
    return wrong


def _fill(value, answers: dict):
    """Pure logic. A step's value with each `{name}` replaced by that answer (in strings, lists and dicts); a name
    with no answer stays as written."""
    if isinstance(value, str):
        return re.sub(r"\{(\w+)\}", lambda m: str(answers.get(m.group(1), m.group(0))), value)
    if isinstance(value, list):
        return [_fill(v, answers) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, answers) for k, v in value.items()}
    return value


def _values(d: dict) -> str:
    """A step's values in words: "hours 9, day today"."""
    return ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in d.items() if v not in ("", None))


def say_step(context, step: dict) -> str:
    """A step in plain words, as the person reads it on the screen and before saying yes. An action step uses the
    sentence the action itself writes when it can (it may need a later answer); else its label and values."""
    from core.actions import ACTION_TYPES

    kind = step.get("kind")
    if kind == "tell":
        return f"Say: \"{step.get('text', '')}\""
    if kind == "ask":
        return f"Ask you: \"{step.get('question', '')}\""
    if kind == "you":
        return f"Wait for you to: {step.get('what', '')}"
    if kind == "tool":
        words = str(step.get("tool", "")).replace("_", " ")
        values = _values(step.get("arguments") or {})
        return f"Do \"{words}\"" + (f" ({values})" if values else "")
    action = ACTION_TYPES.get(str(step.get("action") or ""))
    params = step.get("params") or {}
    if action is not None and not re.search(r"\{\w+\}", json.dumps(params)):
        try:
            return str(action.describe(context, params))
        except Exception:  # noqa: BLE001 - it can't be described now (a record it needs isn't there yet)
            pass
    label = action.label if action is not None else str(step.get("action"))
    return f"{label}" + (f" ({_values(params)})" if params else "")


# ---------------------------------------------------------------- the store


class SkillBook:
    """The person's taught skills, what she's being shown right now (`recording`), and the run in progress
    (taught_skills.json in their folder, written atomically so undo can restore it)."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the person's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the skills, the recording and the run, keeping only known fields; an unreadable file is logged,
        reported and starts empty."""
        self.skills: list[Skill] = []
        self.recording: Optional[dict] = None
        self.active: Optional[Run] = None
        if not self._file.exists():
            return
        try:
            raw = json.loads(open_text(self._file))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.skills = [pick(Skill, d) for d in raw.get("skills", [])]
            self.recording = raw.get("recording") if isinstance(raw.get("recording"), dict) else None
            self.active = pick(Run, raw["active"]) if isinstance(raw.get("active"), dict) else None
        except (ValueError, OSError, TypeError, AttributeError, KeyError):
            log.exception("taught_skills.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes everything atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({
            "skills": [asdict(s) for s in self.skills], "recording": self.recording,
            "active": asdict(self.active) if self.active is not None else None}, indent=2))

    def _save_run(self) -> None:
        """Writes after a run moved or ended, outside the change being recorded: how a run went is a log of what
        happened, so "undo that" takes back the step she just did, never the fact that the skill ran."""
        from core.undo_log import outside_undo

        with outside_undo():
            self._save()

    def get(self, skill_id: str) -> Optional[Skill]:
        """The skill with this id, or None."""
        return next((s for s in self.skills if s.skill_id == skill_id), None)

    def find(self, words: str) -> Optional[Skill]:
        """The skill a few words name: an exact name first, else the one whose name holds every word; None when
        none or several do."""
        wanted = " ".join(re.sub(r"\b(the|my|skill)\b", " ", str(words or "").lower()).split())
        if not wanted:
            return None
        exact = [s for s in self.skills if s.name.lower() == wanted]
        if len(exact) == 1:
            return exact[0]
        hits = [s for s in self.skills if all(w in s.name.lower() for w in wanted.split())]
        return hits[0] if len(hits) == 1 else None

    def add(self, name: str, steps: list, about: str = "", source: str = "") -> Skill:
        """Keeps a new skill, practising (SkillError without a name, with a name already used, or with steps that
        aren't sound)."""
        name = " ".join(str(name or "").split())
        if not name:
            raise SkillError("A skill needs a name.")
        if any(s.name.lower() == name.lower() for s in self.skills):
            raise SkillError(f"There's already a skill called {name}.")
        wrong = step_problems(self.context, steps)
        if wrong:
            raise SkillError(" ".join(wrong))
        skill = Skill(skill_id=uuid.uuid4().hex[:10], name=name[:80], about=str(about or "").strip()[:300],
                      steps=list(steps), source=str(source or "").strip()[:300], created_at=_now())
        self.skills.append(skill)
        self._save()
        return skill

    def set_steps(self, skill_id: str, steps: list) -> Skill:
        """Replaces a skill's steps; it goes back to practising, since what was proven has changed."""
        skill = self.get(skill_id)
        if skill is None:
            raise SkillError("That skill isn't here anymore.")
        wrong = step_problems(self.context, steps)
        if wrong:
            raise SkillError(" ".join(wrong))
        skill.steps, skill.state, skill.clean_runs = list(steps), PRACTISING, 0
        self._save()
        return skill

    def delete(self, skill_id: str) -> None:
        """Forgets a skill (and stops its run, if it's the one running)."""
        if self.get(skill_id) is None:
            raise SkillError("That skill isn't here anymore.")
        self.skills = [s for s in self.skills if s.skill_id != skill_id]
        if self.active is not None and self.active.skill_id == skill_id:
            self.active = None
        self._save()

    # ---------------------------------------------------------------- teaching by watching

    def start_watching(self, name: str) -> None:
        """Starts noting what's done as the steps of a new skill (SkillError without a name, with a name already
        used, or while already watching)."""
        name = " ".join(str(name or "").split())
        if not name:
            raise SkillError("What should I call it? (\"Watch me: the Friday reset\")")
        if self.recording is not None:
            raise SkillError(f"I'm already watching for \"{self.recording['name']}\". Say \"that's it\" to keep it "
                             f"or \"never mind\" to drop it.")
        if any(s.name.lower() == name.lower() for s in self.skills):
            raise SkillError(f"There's already a skill called {name}.")
        self.recording = {"name": name[:80], "steps": [], "started": _now()}
        self._save()

    def note_step(self, step: dict) -> None:
        """Adds a step to what's being shown (nothing when she isn't watching, or past MAX_STEPS)."""
        if self.recording is None or len(self.recording["steps"]) >= MAX_STEPS:
            return
        self.recording["steps"].append(step)
        self._save()

    def keep_watched(self) -> Skill:
        """Ends the watching and keeps what was shown as a skill (SkillError when she wasn't watching or saw
        nothing; the watching goes on in that case)."""
        if self.recording is None:
            raise SkillError("I wasn't watching anything. Say \"watch me: \" and a name first.")
        if not self.recording["steps"]:
            raise SkillError("I haven't seen you do anything yet. Do the steps with me, then say \"that's it\".")
        shown, self.recording = self.recording, None
        try:
            return self.add(shown["name"], shown["steps"], source="shown by doing it")
        except SkillError:
            self.recording = shown
            raise

    def stop_watching(self) -> bool:
        """Drops what's being shown; whether she was watching."""
        was = self.recording is not None
        self.recording = None
        if was:
            self._save()
        return was


def mark(context) -> Optional[int]:
    """How many steps she's been shown so far (None when she isn't watching). Taken before a tool runs, so the
    actions that tool approves on its way aren't noted beside it (`observe_tool`)."""
    book = getattr(context, "taught_skills", None)
    return len(book.recording["steps"]) if book is not None and book.recording is not None else None


def observe_tool(context, name: str, arguments: dict, result: str = "", since: Optional[int] = None) -> None:
    """Called after a tool ran for the person (core/assistant_actions.execute): while she's watching, it's noted
    as a step, in place of any actions it approved on its way (`since`, from `mark`). Not noted: the skill tools,
    the undo, a tool that failed, and anything while a skill is running."""
    book = getattr(context, "taught_skills", None)
    if book is None or book.recording is None or book.active is not None or name == "undo_last_change":
        return
    registry = getattr(context, "assistant_actions", None)
    tool = getattr(registry, "_actions", {}).get(name) if registry is not None else None
    if tool is None or tool.domain == DOMAIN or str(result).startswith(_TOOL_FAILED):
        return
    if since is not None:
        del book.recording["steps"][since:]
    book.note_step({"kind": "tool", "tool": name, "arguments": dict(arguments or {})})


def observe_action(context, kind: str, params: dict) -> None:
    """Called after the person approved a change on a screen (core/actions.ActionCenter.approve): while she's
    watching, it's noted as a step, unless it's one of the skill actions or a skill's own run made it."""
    book = getattr(context, "taught_skills", None)
    if book is None or book.recording is None or str(kind).startswith("taught_skill.") or book.active is not None:
        return
    book.note_step({"kind": "action", "action": kind, "params": dict(params or {})})


# ---------------------------------------------------------------- running


def _result(book: SkillBook, run: Run, status: str) -> dict:
    """What a front door gets back from a run: its status (waiting, done or stopped), what she said since the last
    answer, and what she's waiting for."""
    said, run.said = run.said, []
    if status == "waiting":
        book.active = run
    else:
        book.active = None
    book._save_run()
    return {"status": status, "run_id": run.run_id, "skill_id": run.skill_id, "said": said, "waiting": run.waiting}


def _finish(book: SkillBook, skill: Skill, run: Run, failed: str = "", declined: bool = False) -> dict:
    """Ends a run and updates the skill's practice state. Finished cleanly while watched: one more clean run, and
    learned at CLEAN_RUNS. Stopped on an error: the clean runs start over, and a learned skill goes back to
    practising. Declined or cancelled by the person: nothing changes."""
    skill.runs += 1
    skill.last_run = _now()
    if failed:
        skill.last_result = f"stopped: {failed}"
        skill.clean_runs = 0
        if skill.state == LEARNED:
            skill.state = PRACTISING
            run.said.append(f"That didn't go cleanly, so \"{skill.name}\" is back to practising with you.")
        return _result(book, run, "stopped")
    if declined:
        skill.last_result = "stopped by you"
        return _result(book, run, "stopped")
    skill.last_result = "finished"
    if run.watched and run.clean and skill.state == PRACTISING:
        skill.clean_runs += 1
        if skill.clean_runs >= CLEAN_RUNS:
            skill.state = LEARNED
            run.said.append(f"That's {CLEAN_RUNS} clean runs: I've learned \"{skill.name}\". From now on I'll only "
                            f"stop for questions, and for anything that pays, sends or deletes.")
        else:
            left = CLEAN_RUNS - skill.clean_runs
            run.said.append(f"Done. {left} more clean run{'s' if left != 1 else ''} with you and I'll have learned it.")
    else:
        run.said.append("Done.")
    return _result(book, run, "done")


def _needs_yes(context, skill: Skill, step: dict) -> bool:
    """Whether a step waits for the person's yes before it runs. While the skill is practising: every action
    step, and every tool that may change records. Always, learned or not: an action kind that always asks, a tool
    the registry marks destructive, and a tool whose name says it pays, sends or deletes."""
    from core.main_thread import changes_records

    if step["kind"] == "action":
        return skill.state != LEARNED or always_asks(step.get("action"))
    if step["kind"] == "tool":
        name = str(step.get("tool") or "")
        registry = getattr(context, "assistant_actions", None)
        if (registry is not None and registry.is_destructive(name)) or _TOOL_ALWAYS.search(name):
            return True
        return skill.state != LEARNED and changes_records(name)
    return False


def _cannot(context, step: dict) -> str:
    """Why an action step can't be done right now, in the action's own words ("" when it can, or for a tool):
    its describe runs the same checks its screen would."""
    from core.actions import ACTION_TYPES

    if step["kind"] != "action":
        return ""
    try:
        ACTION_TYPES[step["action"]].describe(context, dict(step.get("params") or {}))
    except KeyError:
        return "I don't have that action anymore"
    except ValueError as problem:  # ActionError is one
        return str(problem)
    return ""


def _do(context, step: dict, approved: bool = False) -> tuple[str, str]:
    """Runs a tool or action step through its own gate: (what happened, "" or why it failed). A tool goes through
    the registry; an action through the action contract (propose, approve) when this MIA has one, so it's checked
    and can be undone. A tool the person hasn't said yes to runs under `guard`: if it reached for an action that
    always asks, nothing was done and the reason is `_NEEDS_YES`."""
    from core.actions import ActionError, run_as_tool

    if step["kind"] == "tool":
        registry = getattr(context, "assistant_actions", None)
        if registry is None:
            return "", "my tools aren't available here"
        held = {"blocked": None}
        token = _UNAPPROVED.set(None if approved else held)
        try:
            said = str(registry.execute(context, step["tool"], dict(step.get("arguments") or {})))
        finally:
            _UNAPPROVED.reset(token)
        if held["blocked"]:
            return "", _NEEDS_YES
        return (said, said) if said.startswith(_TOOL_FAILED) else (said, "")
    center = getattr(context, "actions", None)
    try:
        if center is None:
            return run_as_tool(context, step["action"], dict(step.get("params") or {})), ""
        proposal = center.propose(context, step["action"], dict(step.get("params") or {}), proposed_by="mia")
        done = center.approve(context, proposal.proposal_id)
        if done.status != "executed":
            return "", str(done.result or "it didn't go through")
        return str(done.result or "Done."), ""
    except (ActionError, ValueError) as problem:
        return "", str(problem)


def _advance(context, book: SkillBook, skill: Skill, run: Run, approved: bool = False) -> dict:
    """Runs steps from where the run is until it needs the person or ends. `approved` means the person just said
    yes to the step it was waiting on."""
    while run.at < len(skill.steps):
        step = _fill(skill.steps[run.at], run.answers)
        kind = step["kind"]
        if kind == "tell":
            run.said.append(step["text"])
        elif kind == "ask":
            run.waiting = {"kind": "ask", "text": step["question"], "as": step.get("as") or f"answer{run.at + 1}"}
            return _result(book, run, "waiting")
        elif kind == "you":
            run.waiting = {"kind": "you", "text": f"Over to you: {step['what']}. Tell me when it's done."}
            return _result(book, run, "waiting")
        else:
            if _needs_yes(context, skill, step) and not approved:
                refused = _cannot(context, step)
                if refused:  # never ask for a yes to something that can't be done
                    run.clean = False
                    run.said.append(f"Step {run.at + 1} didn't work: {refused}")
                    return _finish(book, skill, run, failed=refused)
                run.waiting = {"kind": "confirm", "text": f"{say_step(context, step)}. OK?"}
                return _result(book, run, "waiting")
            said, failed = _do(context, step, approved)
            approved = False
            if failed == _NEEDS_YES:  # the tool reached for something that always asks (`guard`)
                run.waiting = {"kind": "confirm", "text": f"{say_step(context, step)}. OK?"}
                return _result(book, run, "waiting")
            if failed:
                run.clean = False
                run.said.append(f"Step {run.at + 1} didn't work: {failed}")
                return _finish(book, skill, run, failed=failed)
            if said:
                run.said.append(said)
        run.waiting = None
        run.at += 1
    return _finish(book, skill, run)


def start(context, skill_id: str, watched: bool = True) -> dict:
    """Starts a skill and runs it until it needs the person or ends: {"status": waiting / done / stopped, "said":
    her lines, "waiting": what she needs}. SkillError when the skill is gone, another is still running, she's being
    shown one, or (unwatched) it isn't learned yet."""
    book = getattr(context, "taught_skills", None)
    skill = book.get(skill_id) if book is not None else None
    if skill is None:
        raise SkillError("That skill isn't here anymore.")
    if book.recording is not None:
        raise SkillError(f"I'm still watching for \"{book.recording['name']}\". Finish that first.")
    if book.active is not None:
        other = book.get(book.active.skill_id)
        raise SkillError(f"\"{other.name if other else 'A skill'}\" is still running and waiting on you. Answer it "
                         f"or stop it first.")
    if not watched and skill.state != LEARNED:
        raise SkillError(f"\"{skill.name}\" is still practising: it only runs with you there.")
    run = Run(run_id=uuid.uuid4().hex[:10], skill_id=skill.skill_id, watched=watched, started=_now())
    run.said.append(f"{skill.name}:" if skill.state == LEARNED else f"{skill.name} (practising, "
                    f"{skill.clean_runs} of {CLEAN_RUNS} clean runs):")
    return _advance(context, book, skill, run)


def answer(context, text: str) -> dict:
    """Gives the waiting run its answer and carries on: an answer to a question; "done" (or a no, which stops it)
    to a task of the person's; yes or no to a step that asked. SkillError when nothing is waiting."""
    book = getattr(context, "taught_skills", None)
    run = book.active if book is not None else None
    if run is None or run.waiting is None:
        raise SkillError("No skill is waiting on an answer.")
    skill = book.get(run.skill_id)
    if skill is None:
        book.active = None
        book._save_run()
        raise SkillError("That skill isn't here anymore.")
    waiting, text = run.waiting, str(text or "").strip()
    if waiting["kind"] == "ask":
        if not text:
            raise SkillError("I need an answer to carry on (or stop the skill).")
        run.answers[waiting["as"]] = text
        run.waiting = None
        run.at += 1
        return _advance(context, book, skill, run)
    if _NO.match(text):
        run.said.append("Stopped.")
        return _finish(book, skill, run, declined=True)
    if waiting["kind"] == "you":
        run.waiting = None
        run.at += 1
        return _advance(context, book, skill, run)
    if not _YES.match(text):
        raise SkillError("Is that a yes or a no?")
    run.waiting = None
    return _advance(context, book, skill, run, approved=True)


def stop(context) -> bool:
    """Stops the run in progress (it doesn't count for or against the skill); whether one was running."""
    book = getattr(context, "taught_skills", None)
    if book is None or book.active is None:
        return False
    skill = book.get(book.active.skill_id)
    if skill is not None:
        skill.last_run, skill.last_result = _now(), "stopped by you"
    book.active = None
    book._save_run()
    return True


# ---------------------------------------------------------------- in conversation


_WATCH = re.compile(r"^\s*(?:hey mia[,:]?\s+)?(?:watch me|learn this|let me teach you)\s*[:,-]?\s*(?:do |how to )?(.*)$", re.I)
_KEEP = re.compile(r"^\s*(that'?s it|that is it|that'?s all|that'?s the skill|done teaching|keep (it|that))\b", re.I)
_RUN = re.compile(r"^\s*(?:please\s+)?(?:run|do|start|practi[sc]e)\s+(?:the\s+|my\s+)?(.+?)(?:\s+skill)?[.!]?\s*$", re.I)


def say(result: dict) -> str:
    """A run's result as what she says: her lines, then what she's waiting for."""
    lines = list(result.get("said") or [])
    if result.get("waiting"):
        lines.append(result["waiting"]["text"])
    return "\n".join(line for line in lines if line)


def take_turn(context, last_said: str, prompt: str) -> Optional[str]:
    """What she says when this message is about a taught skill, handled in code (None: it's an ordinary message).
    In order: "watch me: <name>"; while watching, "that's it" keeps it and "never mind" drops it; the answer to
    what a run just asked (`last_said` is her last message: a run only takes the answer to its own question, so a
    person who moved on isn't held); "run <a skill's name>"."""
    from core.child_accounts import is_child

    book = getattr(context, "taught_skills", None)
    if book is None or (getattr(context, "config", None) is not None and is_child(context)):
        return None
    text = str(prompt or "").strip()
    try:
        watch = _WATCH.match(text)
        if watch and watch.group(1).strip(" .!"):
            name = watch.group(1).strip(" .!")
            book.start_watching(name)
            return (f"Watching. Do \"{name}\" with me, one thing at a time, and say \"that's it\" when you're "
                    f"done (or \"never mind\").")
        if book.recording is not None:
            if _KEEP.match(text):
                skill = book.keep_watched()
                steps = "; ".join(say_step(context, s) for s in skill.steps)
                return (f"Kept \"{skill.name}\": {steps}. Say \"run {skill.name}\" and we'll practise it "
                        f"together; after {CLEAN_RUNS} clean runs I'll have learned it.")
            if _NO.match(text):
                name = book.recording["name"]
                book.stop_watching()
                return f"Dropped \"{name}\". Nothing was kept."
        run = book.active
        if run is not None and run.waiting is not None and run.waiting["text"] in str(last_said or ""):
            kind = run.waiting["kind"]
            if kind == "ask" or _NO.match(text) or _YES.match(text) or (
                    kind == "you" and re.match(r"^\s*(done|finished|did it|ready|next)\b", text, re.I)):
                return say(answer(context, text))
            return None
        wanted = _RUN.match(text)
        if wanted and book.recording is None:
            skill = book.find(wanted.group(1))
            if skill is not None:
                return say(start(context, skill.skill_id))
    except SkillError as problem:
        return str(problem)
    return None
