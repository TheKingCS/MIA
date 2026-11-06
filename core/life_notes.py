"""
core.life_notes
=================

Remembering what you say you'll do, decide and want to try (DEC-0054,
T-0018). Four kinds of note MIA picks up from normal conversation, never
a form, each shown back for a yes before it's kept (Propose → Approve):

- a **commitment** ("I promised Sam I'd fix his gate by Saturday"): who,
  what, by when;
- a **decision** ("we're going with the metal roof because it lasts"):
  what, and why;
- an **idea** ("I should try selling honey"): not acted on yet;
- a **goal set aside** ("I'm giving up on the half marathon, my knee
  can't take it"): what, and the reason in their words.

Spotted in code (`noticed()`): first-person statements only, never a
question, never in a private journal or an off-the-record turn. After
MIA's reply she asks once ("Want me to keep that as a promise to Sam?
Say “keep it”."), never in a turn that already asked something else;
"keep it" next keeps it (a bare "yes" doesn't: it may answer something
else), anything else lets it go. Each note is the person's own (a personal store,
`life_notes.json`), with its date and the conversation it came from,
and can be marked done or forgotten. They answer "what did I promise?",
"what did we decide?", "what ideas haven't I tried?", "what goals have
I dropped and why?" (the `recall` question plan).

The offers themselves are counted, kind and kept-or-not only, never the
words, so the `notes.offers` loop can tell when the spotting asks about
things people don't want kept.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text

FILE_NAME = "life_notes.json"
KINDS = ("commitment", "decision", "idea", "dropped_goal")
SAID = {"commitment": "a promise", "decision": "a decision", "idea": "an idea", "dropped_goal": "a goal set aside"}
OPEN, DONE = "open", "done"
_MAX_OFFERS = 500

_END = r"(?=[.!;,]|$|\s+and (?:then )?i\b)"
_WHO = r"(?P<who>[A-Z][a-z]+|my [a-z]+|him|her|them)"
_BY = r"(?:\s+by\s+(?P<by>tomorrow|tonight|today|next week|next month|the weekend|this weekend|(?:next |this )?" \
      r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|the \d{1,2}(?:st|nd|rd|th)?))?"
_WHY = r"(?:,?\s+(?:because|since|as|so)\s+(?P<why>[^.!?;]+))?"
_PATTERNS = (
    ("commitment", re.compile(r"\bi (?:promised|told) " + _WHO + r" (?:that )?i(?:'d| would| will|'ll) "
                              r"(?P<what>[^.!?;]+?)" + _BY + _END, re.IGNORECASE)),
    ("commitment", re.compile(r"\bi promised (?:to )?(?P<what>[^.!?;]+?)" + _BY + _END, re.IGNORECASE)),
    ("commitment", re.compile(r"\bi(?:'ll| will) (?P<what>[^.!?;]+?) for " + _WHO + r"(?:\s+by\s+(?P<by>[a-z0-9 ]+?))"
                              + _END, re.IGNORECASE)),
    ("dropped_goal", re.compile(r"\bi(?:'m| am| have|'ve)? (?:giving up on|gave up on|given up on|not going to pursue|"
                                r"no longer pursuing|abandoning|abandoned) "
                                r"(?P<what>(?:the |my |on )?[^.!?;,]+?)" + _WHY + _END, re.IGNORECASE)),
    ("decision", re.compile(r"\b(?:we(?:'re| are) going with|(?:we|i)(?:'re| are|'m| am) going to go with|"
                            r"(?:we|i)(?:'ll| will) go with|let'?s go with) (?P<what>[^.!?;,]+?)" + _WHY + _END,
                            re.IGNORECASE)),
    ("decision", re.compile(r"\b(?:we|i)(?:'ve| have)? decided (?:to |on |that |against )?(?P<what>[^.!?;,]+?)" + _WHY
                            + _END, re.IGNORECASE)),
    ("idea", re.compile(r"\bi should (?:really )?(?:try|look into|think about|get into|start(?= \w+ing\b)) (?P<what>[^.!?;,]+?)" + _END,
                        re.IGNORECASE)),
    ("idea", re.compile(r"\b(?:it would be|it'd be) (?:cool|nice|fun|great|smart) to (?P<what>[^.!?;,]+?)" + _END,
                        re.IGNORECASE)),
    ("idea", re.compile(r"\bmaybe i (?:could|should|'ll|will) (?:try |start )?(?P<what>[^.!?;,]+?) (?:some ?day|one day|"
                        r"someday)" + _END, re.IGNORECASE)),
)
_QUESTION = re.compile(r"^\s*(?:should|could|would|can|do|does|did|is|are|was|what|why|how|when|where|who|which)\b",
                       re.IGNORECASE)
# "Keep it" only: a bare "yes" may answer something else in the same reply (her own question, a passing-mention offer)
_KEEP = re.compile(r"^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please)[,.!\s]*)?keep (?:it|that|them)(?:\s+please)?[.!]*\s*$",
                   re.IGNORECASE)


def _clean(text: str) -> str:
    return " ".join(str(text or "").split()).strip(" ,.")


def noticed(text: str) -> Optional[dict]:
    """Pure logic. The note someone's words carry, or None: {"kind", "what", "who", "by", "why"}."""
    said = _clean(text)
    if not said or said.endswith("?") or _QUESTION.match(said):
        return None
    for kind, pattern in _PATTERNS:
        m = pattern.search(said)
        if m is None:
            continue
        parts = m.groupdict()
        what = _clean(parts.get("what"))
        if len(what) < 3 or len(what.split()) > 16:
            continue
        return {"kind": kind, "what": what[:160], "who": _clean(parts.get("who"))[:40],
                "by": _clean(parts.get("by"))[:30], "why": _clean(parts.get("why"))[:200]}
    return None


def describe(note: dict) -> str:
    """Pure logic. A note in a line: "a promise to Sam: fix his gate (by Saturday)"."""
    kind = note.get("kind", "")
    head = SAID.get(kind, "a note") + (f" to {note['who']}" if kind == "commitment" and note.get("who") else "")
    tail = (f" (by {note['by']})" if note.get("by") else "") + (f", because {note['why']}" if note.get("why") else "")
    return f"{head}: {note.get('what', '')}{tail}"


_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def due_date(by: str, said: date) -> Optional[date]:
    """Pure logic. The day a "by ..." means, from the day it was said; None when it isn't a day."""
    by = (by or "").lower().strip()
    if by in ("today", "tonight"):
        return said
    if by == "tomorrow":
        return said + timedelta(days=1)
    if by == "next week":
        return said + timedelta(days=7)
    if by == "next month":
        return said + timedelta(days=30)
    if by in ("the weekend", "this weekend"):
        by = "saturday"
    m = re.fullmatch(r"(?:(next|this) )?(" + "|".join(_DAYS) + ")", by)
    if m:
        # The next one after today ("next Friday" is said both ways, so it's the next one too: a day early is safe)
        return said + timedelta(days=(_DAYS.index(m.group(2)) - said.weekday()) % 7 or 7)
    m = re.fullmatch(r"the (\d{1,2})(?:st|nd|rd|th)?", by)
    if m:
        day = int(m.group(1))
        for months in range(0, 3):
            year, month = said.year + (said.month - 1 + months) // 12, (said.month - 1 + months) % 12 + 1
            try:
                found = date(year, month, day)
            except ValueError:
                continue
            if found >= said:
                return found
    return None


def reminders(context, today: Optional[date] = None) -> list:
    """The daily check (DEC-0054): a promise with a day, the day before and on the day, once each, through the
    gate. Marked as said in the note itself."""
    from core.communication_gate import TIMELY, Candidate

    store = getattr(context, "life_notes", None)
    if store is None:
        return []
    today = today or date.today()
    out = []
    for note in store.of_kind("commitment", open_only=True):
        if not note.get("due"):
            continue
        try:
            due = date.fromisoformat(note["due"])
        except ValueError:
            continue
        stage = "today" if due == today else "tomorrow" if due == today + timedelta(days=1) else ""
        if not stage or stage in note.get("reminded", []):
            continue
        who = f" to {note['who']}" if note.get("who") else ""
        out.append(Candidate(topic="promise_due", title="A promise" + (" for today" if stage == "today" else
                                                                       " for tomorrow"),
                             message=f"Your promise{who}: {note['what']}, {stage}.", urgency=TIMELY, source="life_notes",
                             fingerprint=f"promise:{note['id']}:{stage}"))
        note.setdefault("reminded", []).append(stage)
    if out:
        store._save()
    return out


def offer_text(note: dict) -> str:
    kind = note.get("kind", "")
    head = SAID.get(kind, "a note") + (f" to {note['who']}" if kind == "commitment" and note.get("who") else "")
    return f"(Want me to keep that as {head}? Say “keep it”.)"


class LifeNotes:
    """One person's commitments, decisions, ideas and goals set aside (context.life_notes)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.notes: list[dict] = []
        self.offers: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self.notes, self.offers = list(data.get("notes") or []), list(data.get("offers") or [])
        except (OSError, ValueError, AttributeError):
            self.notes, self.offers = [], []

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"notes": self.notes, "offers": self.offers[-_MAX_OFFERS:]}, indent=1,
                                                 ensure_ascii=False))

    def add(self, kind: str, what: str, who: str = "", by: str = "", why: str = "",
            conversation_id: Optional[str] = None) -> dict:
        if kind not in KINDS:
            raise ValueError(f"A note is one of {', '.join(KINDS)}.")
        what = _clean(what)
        if not what:
            raise ValueError("What should I keep?")
        same = next((n for n in self.notes if n["kind"] == kind and n["what"].lower() == what.lower()
                     and n["status"] == OPEN), None)
        if same is not None:
            return same
        note = {"id": uuid.uuid4().hex[:10], "kind": kind, "what": what[:160], "who": _clean(who)[:40],
                "by": _clean(by)[:30], "why": _clean(why)[:200], "status": OPEN,
                "at": datetime.now().isoformat(timespec="seconds"), "conversation_id": conversation_id or ""}
        due = due_date(note["by"], date.today()) if note["by"] else None
        if due is not None:
            note["due"] = due.isoformat()  # a promise with a day is mentioned the day before and on it (reminders())
        self.notes.append(note)
        self._save()
        return note

    def offered(self, kind: str, kept: bool) -> None:
        self.offers.append({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "kept": bool(kept)})
        self._save()

    def get(self, note_id: str) -> Optional[dict]:
        return next((n for n in self.notes if n["id"] == note_id), None)

    def mark_done(self, note_id: str) -> Optional[dict]:
        note = self.get(note_id)
        if note is not None:
            note["status"], note["done_at"] = DONE, datetime.now().isoformat(timespec="seconds")
            self._save()
        return note

    def forget(self, note_id: str) -> bool:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n["id"] != note_id]
        if len(self.notes) != before:
            self._save()
            return True
        return False

    def of_kind(self, kind: Optional[str] = None, open_only: bool = False) -> list[dict]:
        return [n for n in self.notes if (kind is None or n["kind"] == kind) and (not open_only or n["status"] == OPEN)]


TITLES = {"commitment": "Promises", "decision": "Decisions", "idea": "Ideas", "dropped_goal": "Goals set aside"}


def screen(context) -> dict:
    """The Kept screen (web/kept.html): each kind's notes, open first, newest first."""
    store = getattr(context, "life_notes", None)
    kinds = []
    for kind in KINDS:
        mine = store.of_kind(kind) if store is not None else []
        newest = lambda notes: sorted(notes, key=lambda n: n.get("at", ""), reverse=True)  # noqa: E731
        found = newest([n for n in mine if n.get("status") == OPEN]) + newest([n for n in mine if n.get("status") != OPEN])
        kinds.append({"kind": kind, "title": TITLES[kind],
                      "notes": [{"id": n["id"], "line": describe(n), "status": n.get("status", OPEN),
                                 "at": n.get("at", "")[:10], "due": n.get("due", "")} for n in found]})
    return {"kinds": kinds}


# ------------------------------------------------------------------ said out loud

_LEAD = r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?"
_DONE = re.compile(_LEAD + r"(?:i\s+)?(?:kept|did|finished|fulfilled|completed|mark|marked)\s+(?:my |the |that )?"
                   r"(?P<kind>promise|idea)(?:\s+(?:to|for|about)\s+(?P<who>[\w' ]+?))?(?:\s+(?:as\s+)?done)?[.!]*\s*$",
                   re.IGNORECASE)
_FORGET = re.compile(_LEAD + r"forget\s+(?:my |the |that )?(?P<kind>promise|decision|idea|goal)"
                     r"(?:\s+(?:to|for|about)\s+(?P<who>[\w' ]+?))?[.!]*\s*$", re.IGNORECASE)
_KIND_WORD = {"promise": "commitment", "decision": "decision", "idea": "idea", "goal": "dropped_goal"}


def _which(store, kind: str, about: str) -> Optional[dict]:
    """The latest open note of that kind, about someone or something when it's said."""
    about = (about or "").lower().strip()
    found = [n for n in store.of_kind(kind, open_only=True)
             if not about or about in f"{n.get('who', '')} {n.get('what', '')}".lower()]
    return found[-1] if found else None


def reply(context, text: str) -> Optional[str]:
    """Quick commands: "I kept my promise to Sam", "forget the idea about honey"; through the action contract."""
    store = getattr(context, "life_notes", None)
    actions = getattr(context, "actions", None)
    if store is None or actions is None:
        return None
    m, kind_of = _DONE.match(text or ""), "life_note.done"
    if m is None:
        m, kind_of = _FORGET.match(text or ""), "life_note.forget"
    if m is None:
        return None
    kind = _KIND_WORD[m.group("kind").lower()]
    note = _which(store, kind, m.group("who") or "")
    if note is None:
        return f"I don't have {SAID[kind]}" + (f" about {m.group('who')}" if m.group("who") else "") + " kept."
    from core.actions import ActionError

    try:
        done = actions.approve(context, actions.propose(context, kind_of, {"note_id": note["id"]},
                                                        proposed_by="person").proposal_id)
    except ActionError as problem:
        return str(problem)
    return f"{done.result} (Say “undo that” to take it back.)" if done.status == "executed" else done.result


# ------------------------------------------------------------------ in the conversation


def _private(conversation) -> bool:
    from core.conversation_modes import PERSONAL_MODES

    return conversation is None or bool(getattr(conversation, "off_record", False) or getattr(conversation, "journal",
                                                                                              False)
                                        or getattr(conversation, "private_turn", False)
                                        or getattr(conversation, "mode", None) in PERSONAL_MODES)


def answer_offer(context, conversation, prompt: str) -> Optional[str]:
    """Before a turn: "keep it" after an offer keeps the note; anything else lets it go."""
    pending = getattr(conversation, "pending_note", None) if conversation is not None else None
    if not pending:
        return None
    conversation.pending_note = None
    store = getattr(context, "life_notes", None)
    if store is None:
        return None
    if not _KEEP.match(prompt or "") or not (prompt or "").strip():
        store.offered(pending["kind"], False)
        return None
    note = store.add(pending["kind"], pending["what"], pending.get("who", ""), pending.get("by", ""),
                     pending.get("why", ""), getattr(conversation, "conversation_id", None))
    store.offered(pending["kind"], True)
    ask = {"commitment": "what did I promise?", "decision": "what did I decide?", "idea": "what ideas haven't I tried?",
           "dropped_goal": "what goals have I set aside?"}[note["kind"]]
    return f"Kept: {describe(note)}. Ask “{ask}” any time."


def offer_after(context, conversation, prompt: str) -> Optional[str]:
    """After MIA's reply: the note the person's words carried, offered once for a yes."""
    if _private(conversation) or getattr(context, "life_notes", None) is None:
        return None
    passing = getattr(conversation, "pending_offer", None)
    if passing is not None and getattr(passing, "shown", False):
        return None  # she already asked something this turn (core/passing_mentions.py): one question at a time
    found = noticed(prompt)
    if found is None:
        return None
    if any(n["kind"] == found["kind"] and n["what"].lower() == found["what"].lower()
           for n in context.life_notes.of_kind(found["kind"], open_only=True)):
        return None  # already kept
    conversation.pending_note = found
    return offer_text(found)
