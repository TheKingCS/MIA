"""
core.stop
===========

"Stop" and "stop everything" (REQ-AUT-010; DEC-0181, DEC-0185; Zac, Q-34 and Q-40: "we need to specify what stopping
everything really means"; the definition is `docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md` section 4, and
this module is that table in code). Prompt 23's review, UI-2, built on the run record (core/runs.py).

**Recognised in code, never by a model** (`recognise`): the whole message is "stop" (or "stop it", "halt"...), "stop
everything" (optionally "until tonight", "for two hours"; a time it can't read is asked about, never held with no
end), or, only while a stop-everything is on, "carry on". "Stop the timer", "stop the skill" or "stop all alarms" are
other things and aren't taken here. The turn pipeline asks first, before anything else (core/assistant_turn.py, the
model's turn and the desktop panels' `instant_answer`), so it works when the model is slow, wrong or down, on every
device.

**"Stop"** (`stop_now`) ends what MIA is doing right now for the person: her speech, the taught skill she's running
with them, the job she's walking them through, and her browser tasks (a held step is let go, never pressed; the run
ends at its step). Step plans aren't touched: they wait on him, nothing of hers runs in them. Nothing is undone:
what finished stays finished, each change with its Undo. Runs she started on her own, background jobs and her
messages keep going.

**"Stop everything"** (`stop_everything`) does that, and holds all of her own initiative until "carry on" or the
time he named (`holding`): background jobs that change records or reach outside wait (`defer_reason`, asked by the
scheduler and the daily checks; `JOBS_THAT_WAIT`, `CHECKS_THAT_WAIT`), her unprompted messages are held by the gate
and offered when he resumes (urgent ones and the reminders he set, `TOPICS_NEVER_HELD`, still come), and anything she'd start herself that changes a record is
refused (`core/grants.require` asks `held_now`). It survives a restart: the hold is his own setting.

**Never stopped, by either:** alarms and reminders he set, the safety floor, nightly backups, sync of what he
changes, homeostasis's watching, and everything he asks or presses himself. **The greenhouse is never touched**
(DEC-0185): its node's own control loop keeps running and settings already applied stay; this module has no call
that reaches it. A device's state is left as it is.

**Afterwards she says, from records** (`report`): what was running and where each thing stopped, and how to resume.

**Other processes** (a Night School run already going, a lab merge) have no settings to ask, so the hold also keeps
a small mark on disk (`hold_file`, `held_on_disk`); Night School asks it before each step and the lab before a
merge. An end time that can't be read never lifts a stop by itself.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

KEY = "mia.stop_everything"  # the person's setting: {"since", "until"} while a stop-everything is on, else None

# Background jobs (core/background_jobs.JOBS) that wait while everything is stopped: they change records on her own
# initiative or reach outside. The others never wait: alarms, the battery warning, the once-a-day tick itself, and
# watching the connection (which is how "remind me when I'm back online" works).
JOBS_THAT_WAIT = frozenset({"recall_index", "activity_watch", "world_intel", "mission_auto_assignment", "inbox", "inbox_mail", "finance_snapshots",
                            "homestead_snapshots", "lite_captures"})
JOBS_THAT_RUN = frozenset({"alarms", "power", "daily_occasions", "online", "self_repair"})
# Daily checks (DAILY_CHECKS) that wait: her own work, things she makes or changes, and anything that goes online.
# The rest only notice something and offer a message, which the gate holds until he resumes.
CHECKS_THAT_WAIT = frozenset({"workflows", "night_school", "good_news", "chronicle", "chronicle_issue",
                              "vault_captions", "dependency_audit", "system_map", "self_report", "capability_gaps",
                              "seasons_of_memory", "loops", "fix_report", "findings", "rewards", "momentum"})
# Never waiting, by name, because the definition says so: backups, the greenhouse's watch, reminders he set.
CHECKS_THAT_ALWAYS_RUN = frozenset({"auto_backup", "greenhouse", "grow_alert", "obligation_reminders", "loop",
                                    "recurring_mission", "calendar_digest", "birthday", "warranty",
                                    "insurance_renewal", "promises"})
# The rest only notice something and offer a message: they run, and the gate holds what they offer until he resumes.
CHECKS_THAT_ONLY_OFFER = frozenset({"self_changes", "checkin", "budget_nudge", "smart_suggestion", "maintenance_insight",
                                    "mission_insight", "pattern_insight", "skill_pattern_insight",
                                    "skill_decline_insight", "skill_momentum_insight", "walkthrough_suggestion",
                                    "journal_reflection", "memory_callback", "season", "operating_journal",
                                    "direction_nudge", "capability_reminder"})
# The gate's topics (core/communication_gate.py) of what the checks in CHECKS_THAT_ALWAYS_RUN offer: reminders he set
# and the greenhouse's alerts, which "stop everything" never holds (as she says in `report`).
TOPICS_NEVER_HELD = frozenset({"birthday", "calendar_digest", "warranty", "grow_alert", "greenhouse",
                               "insurance_renewal", "obligation_deadline", "promise_due"})

_PRE = r"^\s*(?:hey,?\s+)?(?:mia[,:]?\s+)?(?:please\s+)?"  # "hey MIA, please ..."
_POST = r"(?:[,\s]+(?:please|now|mia))*\s*[.!]*\s*$"  # "..., please", "..., MIA", "!"
_STOP = re.compile(_PRE + r"(?:stop|stop it|stop this|stop that|stop now|stop talking|halt|that'?s enough,? stop|"
                   r"cancel that)" + _POST, re.I)
# Only nothing or a time may follow "stop everything": "stop all alarms" or "freeze all my cards" are other things.
_EVERYTHING = re.compile(_PRE + r"(?:stop|halt|pause|freeze)\s+(?:everything|it all|all of it)"
                         r"(?:[,\s]+((?:until|till|til|'til|for)\s.*?|tonight|this evening|tomorrow(?:\s+morning)?))?"
                         + _POST, re.I)
_CARRY_ON = re.compile(r"^\s*(?:hey\s+)?(?:mia[,:]?\s+)?(?:ok(?:ay)?[,]?\s+)?(?:please\s+)?(?:carry on|you can carry on|"
                       r"go ahead again|resume everything|start again|you can start again|unpause)\s*[.!]*\s*$", re.I)
_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
            "forty five": 45, "fifty": 50, "sixty": 60, "ninety": 90}
_HALF = frozenset({"half", "half a", "half an", "a half"})
_UNTIL_HE_SAYS = frozenset({"", "now", "for now", "for the moment", "for the time being", "until i say",
                            "until i say so", "until i say carry on"})

_held_until: Optional[datetime] = None  # this process's copy of the hold, for checks that have no context
_held_known = False


def _number(words: str) -> Optional[float]:
    """Pure logic. A count in digits or words: "30", "seven", "twenty five", "a couple of", "half an", "one and a
    half"; None when it isn't one."""
    text = " ".join(re.sub(r"-", " ", words or "").split())
    extra = 0.0
    if text.endswith(" and a half"):
        text, extra = text[: -len(" and a half")], 0.5
    if text in _HALF:
        return 0.5 + extra
    if re.fullmatch(r"(?:a )?couple(?: of)?", text):
        return 2 + extra
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text) + extra
    if text in _NUMBERS:
        return _NUMBERS[text] + extra
    parts = text.split()
    if len(parts) == 2 and _NUMBERS.get(parts[0], 0) >= 20 and 0 < _NUMBERS.get(parts[1], 0) < 10:
        return _NUMBERS[parts[0]] + _NUMBERS[parts[1]] + extra
    return None


def _clock(text: str, now: datetime, tomorrow: bool) -> Optional[datetime]:
    """Pure logic. A time of day ("5pm", "5:30", "9 in the morning", "17:00"), at its next occurrence (on tomorrow's
    date when `tomorrow`); with no am or pm, "5" is the next 5 o'clock in 12-hour terms. None when the words aren't a
    time; ValueError for one that can't be ("5:75", "13pm")."""
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s*o'?clock)?(?:\s+(?:in the\s+)?"
                     r"(morning|afternoon|evening|tonight|night))?", text)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if minute > 59:
        raise ValueError(f"{text} isn't a time")
    meridiem = m.group(3) or {"morning": "am"}.get(m.group(4) or "", "pm" if m.group(4) else "")
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError(f"{text} isn't a time")
        hours = [hour % 12 + (12 if meridiem == "pm" else 0)]
    elif hour > 23:
        raise ValueError(f"{text} isn't a time")
    elif hour == 0 or hour > 12:
        hours = [hour]
    else:
        hours = [hour % 12, hour % 12 + 12]
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if tomorrow:
        if len(hours) > 1:  # "until 5 tomorrow": 1 to 6 o'clock in the afternoon, 7 to 11 in the morning, 12 noon
            hours = [hours[1] if hour <= 6 or hour == 12 else hours[0]]
        return day + timedelta(days=1, hours=hours[0], minutes=minute)
    return min(at for h in hours for at in (day + timedelta(hours=h, minutes=minute),
                                            day + timedelta(days=1, hours=h, minutes=minute)) if at > now)


def until_from(words: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Pure logic. When a stop-everything ends, from the words after it: "until tonight" (8 pm; after 7 pm or before
    5 am, the next morning at 8), "until morning" (8 am: today's before 8), "until tomorrow" (8 am), "until noon",
    "until 5pm", "until 5pm tomorrow", "until 5" (the next 5 o'clock), "for two hours", "for fifteen minutes", "for
    half an hour", "for a couple of hours", "for today" (the next morning); None for no end (until he says, or "for
    now"). ValueError for words it can't read, so an unreadable time never becomes a hold with no end."""
    now = now or datetime.now()
    low = " ".join(str(words or "").lower().replace("’", "'").replace("a.m.", "am").replace("p.m.", "pm").split())
    low = low.strip(" ,.!")
    if low in _UNTIL_HE_SAYS:
        return None
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    morning_after = day + timedelta(days=0 if now.hour < 5 else 1, hours=8)
    if re.fullmatch(r"for (?:today|the day|the rest of (?:the|to)day)", low):
        return morning_after
    if low.startswith("for "):
        m = re.fullmatch(r"for\s+(.+?)\s*(minute|min|hour|hr|day|week)s?(\s+and\s+a\s+half)?", low)
        n = _number(m.group(1)) if m else None
        if not n or n <= 0:
            raise ValueError(f"I can't tell how long \"{words}\" is")
        n += 0.5 if m.group(3) else 0
        unit = {"minute": "minutes", "min": "minutes", "hour": "hours", "hr": "hours", "day": "days",
                "week": "weeks"}[m.group(2)]
        return now + timedelta(**{unit: n})
    rest = re.sub(r"^(?:until|till|til|'til|up to)\s+", "", low)
    tomorrow = bool(re.search(r"\btomorrow\b", rest))
    rest = " ".join(re.sub(r"\b(?:tomorrow|today|at)\b", " ", rest).split())
    at = _clock(rest, now, tomorrow)
    if at is not None:
        return at
    if rest in ("noon", "midday", "lunch", "lunchtime"):
        noon = day + timedelta(days=1 if tomorrow else 0, hours=12)
        return noon if tomorrow or noon > now else noon + timedelta(days=1)
    if rest == "midnight":
        return day + timedelta(days=1)
    if rest in ("tonight", "this evening", "evening", "night", "tomorrow night", "tomorrow evening"):
        if tomorrow:
            return day + timedelta(days=1, hours=20)
        return morning_after if now.hour >= 19 or now.hour < 5 else day + timedelta(hours=20)
    if rest in ("", "morning", "the morning", "this morning"):
        return day + timedelta(hours=8) if not tomorrow and now.hour < 8 else day + timedelta(days=1, hours=8)
    raise ValueError(f"I can't tell when \"{words}\" is")


def recognise(prompt: str, holding_now: bool = False) -> Optional[tuple[str, str]]:
    """Pure logic. ("stop", ""), ("everything", the words after it) or ("carry_on", "") when the whole message is one
    of the commands, else None: "stop everything" only with nothing or a time after it ("stop all alarms" is
    None). "Carry on" counts only while a stop-everything is on (elsewhere it means other things)."""
    text = str(prompt or "")
    m = _EVERYTHING.match(text)
    if m:
        return "everything", m.group(1) or ""
    if _STOP.match(text):
        return "stop", ""
    if holding_now and _CARRY_ON.match(text):
        return "carry_on", ""
    return None


# ------------------------------------------------------------------ the hold


def _read(context) -> Optional[dict]:
    """The person's hold as kept, or None."""
    from core import person_settings

    try:
        value = person_settings.get(context, KEY, None)
    except Exception:  # noqa: BLE001 - no settings here: no hold
        return None
    return value if isinstance(value, dict) and value.get("since") else None


def state(context, now: Optional[datetime] = None) -> Optional[dict]:
    """The stop-everything in force for this person ({"since", "until"}), or None; one whose time has passed is
    lifted here. Keeps this process's copy current for `held_now`; an end time that can't be read holds."""
    global _held_until, _held_known
    now = now or datetime.now()
    value = _read(context)
    if value and value.get("until"):
        try:
            if datetime.fromisoformat(value["until"]) <= now:
                _write(context, None)
                value = None
        except ValueError:
            pass
    _held_known = True
    try:
        _held_until = None if not value else (datetime.fromisoformat(value["until"]) if value.get("until") else datetime.max)
    except ValueError:  # an end time that can't be read holds until he says carry on, never lifts by itself
        _held_until = datetime.max
    return value


def holding(context, now: Optional[datetime] = None) -> bool:
    """Whether a stop-everything is on for this person now."""
    return state(context, now) is not None


def held_now(now: Optional[datetime] = None) -> bool:
    """Whether this process last saw a stop-everything in force (for checks with no context: core/grants.require).
    False until something has asked `state`; the runtime asks at start and at every scheduler turn."""
    return _held_known and _held_until is not None and (now or datetime.now()) < _held_until


def _write(context, value: Optional[dict]) -> None:
    """Keeps (or clears) the hold in the person's settings, outside "undo that": a stop isn't something an undo of
    another change may lift. The mark other processes read follows it (`_mark_on_disk`)."""
    from core import person_settings
    from core.undo_log import outside_undo

    with outside_undo():
        person_settings.put(context, KEY, value)
    _mark_on_disk(value)


def hold_file():
    """Where the stop's mark for other processes is kept: beside the person's config file."""
    from core import config_manager

    return config_manager._CONFIG_FILE.with_name("stop_everything.hold")


def _mark_on_disk(value: Optional[dict]) -> None:
    """Keeps the mark (`hold_file`) in step with the hold: there while a stop is on (holding its end time, or nothing for
    "until he says"), gone when it's lifted. Work in another process reads it (`held_on_disk`): Night School and the
    lab's merges have no settings of their own to ask."""
    try:
        mark = hold_file()
        if value:
            mark.parent.mkdir(parents=True, exist_ok=True)
            mark.write_text(str(value.get("until") or ""), encoding="utf-8")
        else:
            mark.unlink(missing_ok=True)
    except OSError:
        log.exception("Couldn't keep the stop's mark for other processes")


def held_on_disk(now: Optional[datetime] = None) -> bool:
    """Whether a stop-everything is in force, for a process with no context (Night School, a lab merge): the mark
    is there and its end time, if it has one, hasn't passed. A mark that can't be read counts as held."""
    try:
        until = hold_file().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    try:
        return not until or datetime.fromisoformat(until) > (now or datetime.now())
    except ValueError:
        return True


# ------------------------------------------------------------------ the commands


def quiet(context) -> None:
    """Cuts off her speech at once. Safe from any thread and never raises, so the frame's Stop can call it before
    waiting for a turn in progress to finish."""
    voice = getattr(context, "voice", None)
    if voice is None:
        return
    try:
        voice.stop_playback()
    except Exception:  # noqa: BLE001
        log.exception("Stop: her speech didn't stop cleanly.")


def _stop_job(context) -> list[str]:
    """Ends the job or diagnosis she's walking the person through (core/trade_session.py), as `trade.stop` does when
    he says "stop the job" (proposed and approved as the person, so it's recorded like any other change). Step plans
    aren't touched: they wait on the person, nothing of hers is running in them. Returns what was stopped, in words."""
    store = getattr(context, "trade_session", None)
    live = store.live() if store is not None else None
    if live is None:
        return []
    where = f"\"{live.title}\"" + (f" at step {live.at + 1}" if live.kind == "job" else "")
    actions = getattr(context, "actions", None)
    if actions is not None:
        import core.trade_actions  # noqa: F401 - registers trade.stop

        done = actions.approve(context, actions.propose(context, "trade.stop", {}, proposed_by="person").proposal_id)
        if done.status != "executed":
            log.warning("Stop: the job walkthrough didn't stop: %s", done.result)
            return []
    else:
        from core import trade_session

        trade_session.stop(live)
        store.save()
    return [f"walking you through {where}"]


def stop_now(context) -> dict:
    """"Stop": ends her speech, the skill she's running with the person, the job she's walking them through
    (`_stop_job`) and her browser tasks, after the step in progress. Returns {"stopped": [what, in words]}. Never
    raises: a part that fails to stop is logged and the rest still stop."""
    stopped: list[str] = []
    quiet(context)
    try:
        from core import taught_skills

        book = getattr(context, "taught_skills", None)
        if book is not None and book.active is not None:
            skill = book.get(book.active.skill_id)
            at = book.active.at + 1
            if taught_skills.stop(context):
                stopped.append(f"\"{skill.name if skill else 'the skill'}\" at step {at}")
    except Exception:  # noqa: BLE001
        log.exception("Stop: the skill didn't stop cleanly.")
    try:
        stopped.extend(_stop_job(context))
    except Exception:  # noqa: BLE001
        log.exception("Stop: the job walkthrough didn't stop cleanly.")
    try:
        hub = getattr(context, "browsers", None)
        browser = hub.for_person(context) if hub is not None else None
        if browser is not None:
            for pending_id, pending in list(browser.pending.items()):
                browser.drop_pending(pending_id, "you said stop")
                actions = getattr(context, "actions", None)
                if actions is not None and pending.proposal_id:
                    try:
                        actions.reject(context, pending.proposal_id)
                    except Exception:  # noqa: BLE001 - the held step is already gone
                        pass
                stopped.append(f"a browser step that was waiting ({pending.summary()}): not pressed")
            if getattr(browser, "teaching", None) is not None:
                name = browser.teaching.get("name", "a task")
                browser.teaching = None
                stopped.append(f"watching you for \"{name}\"")
    except Exception:  # noqa: BLE001
        log.exception("Stop: the browser didn't stop cleanly.")
    try:
        from core.runs import book as run_book

        runs = run_book(context)
        for run in (runs.open_runs() if runs is not None else []):
            if run.source == "browser_routines":
                runs.finish(run.run_id, "stopped", f"at step {run.at}: you said stop")
                if not any(run.title in s for s in stopped):
                    stopped.append(f"\"{run.title}\" at step {run.at}")
    except Exception:  # noqa: BLE001
        log.exception("Stop: the run book couldn't be updated.")
    return {"stopped": stopped}


def stop_everything(context, until: Optional[datetime] = None, now: Optional[datetime] = None) -> dict:
    """"Stop everything": `stop_now`, and her own initiative held until he says "carry on" or `until`. Returns the
    report's parts: {"stopped", "until"}."""
    now = now or datetime.now()
    done = stop_now(context)
    _write(context, {"since": now.isoformat(timespec="seconds"),
                     "until": until.isoformat(timespec="seconds") if until else ""})
    state(context, now)
    done["until"] = until
    log.info("Stop everything is on%s.", f" until {until:%Y-%m-%d %H:%M}" if until else "")
    return done


def carry_on(context) -> bool:
    """Lifts a stop-everything; whether one was on. Her held messages are offered at the gate's next turn. While
    a lockdown is on (core/lockdown.py) nothing is lifted: only his password lifts that."""
    from core import lockdown

    if lockdown.active(context) is not None:
        return False
    was = _read(context) is not None
    _write(context, None)
    state(context)
    if was:
        log.info("Stop everything is lifted.")
    return was


def defer_reason(context, name: str) -> str:
    """Why a background job or daily check waits now ("" to run it): only while a stop-everything is on, and only the
    ones that change records on her own or reach outside."""
    if name in JOBS_THAT_WAIT or name in CHECKS_THAT_WAIT:
        return "you asked me to stop everything" if holding(context) else ""
    return ""


# ------------------------------------------------------------------ what she says


def _when(until: Optional[datetime], now: Optional[datetime] = None) -> str:
    """Pure logic. "until 8:00 PM", "until tomorrow at 8:00 AM", or "until you say carry on"."""
    if until is None:
        return "until you say \"carry on\""
    now = now or datetime.now()
    clock = f"{until.hour % 12 or 12}:{until:%M} {'PM' if until.hour >= 12 else 'AM'}"
    return f"until {clock}" if until.date() == now.date() else f"until {until:%A} at {clock}"


def report(done: dict, everything: bool, now: Optional[datetime] = None) -> str:
    """Pure logic. What she says after a stop, from what was stopped: each thing and where it stopped, that nothing
    was undone, what's held (for stop everything), and how to resume."""
    said = []
    if done["stopped"]:
        said.append("Stopped: " + "; ".join(done["stopped"]) + ".")
        said.append("Nothing was undone: what finished stays, and you can undo any of it from Recent Changes.")
    else:
        said.append("Nothing of mine was running." if not everything else "Nothing was running.")
    if everything:
        said.append(f"I've stopped everything of my own {_when(done.get('until'), now)}: my background work waits and "
                    "I'll hold what I'd have told you. Alarms, reminders you set, backups and the greenhouse carry on "
                    "as they are, and I'll still do whatever you ask.")
    elif done["stopped"]:
        said.append("Start any of them again when you like.")
    return " ".join(said)


def handle(context, prompt: str) -> Optional[str]:
    """The turn pipeline's first question: when the message is a stop command, does it and returns what she says;
    else None. A "stop everything" whose time can't be read stops what's running, holds nothing and asks. "Carry
    on" is refused while a lockdown is on (core/lockdown.py)."""
    command = recognise(prompt, holding_now=_read(context) is not None)
    if command is None:
        return None
    kind, rest = command
    if kind == "carry_on":
        from core import lockdown

        if lockdown.active(context) is not None:
            return "Lockdown is on, so I'm staying stopped. Sign in with your password to lift it."
        carry_on(context)
        return "Carrying on: my background work and messages are back. Anything I held comes through at its own pace."
    if kind == "everything":
        try:
            until = until_from(rest)
        except ValueError:  # an unreadable time never becomes a hold with no end: what's running stops, and she asks
            return (report(stop_now(context), everything=False) + f" I didn't catch how long you meant by \"{rest}\", "
                    "so nothing is held yet. Say \"stop everything for two hours\", \"until 5pm\" or \"until "
                    "tonight\", or just \"stop everything\" to hold it until you say \"carry on\".")
        return report(stop_everything(context, until), everything=True)
    return report(stop_now(context), everything=False)


def for_shell(context, now: Optional[datetime] = None) -> Optional[dict]:
    """What the frame shows while a stop-everything is on at `now` (the clock's when None): {"since", "until",
    "line"}, else None."""
    value = state(context, now)
    if not value:
        return None
    until = datetime.fromisoformat(value["until"]) if value.get("until") else None
    return {"since": value["since"], "until": value.get("until", ""),
            "line": f"Everything of MIA's own is stopped {_when(until, now)}."}
