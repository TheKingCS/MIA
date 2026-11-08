"""
core.connections
==================

The magic is in the connections (Zac, 2026-11-08). Something said in passing ("picked up chicken feed today") can
matter to a project started three weeks ago, an idea set aside, a goal still open. MIA notices that tie, holds it,
and brings it up naturally in a later conversation, once, then lets it go. That's when the whole of her starts to feel
like one mind instead of many apps.

How (facts in code, the model only phrases):

1. `notice(context, conversation, prompt)` runs before each turn (`core/talk_it_out.py`'s `pre_turn`, after the
   danger check, never in a private or personal turn). It finds the records the words name (an asset, a material, a
   skill: `MENTIONABLE`) and follows the link graph (`core/links.py`) to an *open* project, goal or mission on the far
   end. Failing that, it looks for an open project, goal or mission, or an idea set aside (`core/life_notes.py`), that
   shares a distinctive word with what was said. Only things at least a week old count (yesterday's project is still
   top of mind), and a thing named outright is the topic, not a connection.
2. It keeps one connection per thing (`connections.json`, sealed at rest, DEC-0126): what was said, when, what it ties
   to and how.
3. `connections_for(context)` puts the newest one into the everyday conversation's system message, held back a couple
   of hours so it lands in a later conversation. Never in the personal "talk it out" path or a turn about faith or
   meaning, and framed as "only if it fits naturally, one sentence, then let it go."
4. The next turn, `settle` reads her last reply: named it, so it's mentioned; two weeks unmentioned, it expires.
   Either way it's done, and the same thing isn't raised again for a month.
5. "Don't bring that up" (`decline`, the action `connection.decline` from the Connections page and the voice tool,
   web/connections.html, core/web_connections.py): the connection is settled as declined and its thing joins a quiet
   list `_recent` respects, so it's never raised again until the person allows it (`allow`).

Two loops watch it (`core/loops.py`): `connections.landed`, the share she actually brings up (are they chosen and
framed well?), and `connections.unlinked`, the system side Zac asked for: ties found only by shared words, between
kinds of records her link graph doesn't connect yet. Each is a place her systems could interconnect; when they pile
up it opens a task to teach the graph that connection (counted by kind, never by name).
"""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "connections.json"

MIN_AGE_DAYS = 7  # a thing must be at least this old to be "remembered"; newer is still top of mind
HOLD_HOURS = 2  # a connection waits this long, so it comes up in a later conversation, not mid-thought
EXPIRE_DAYS = 14  # unmentioned this long, it's let go
COOLDOWN_DAYS = 30  # the same thing isn't raised again for this long
MAX_OPEN = 3  # at most this many held at once
_KEEP = 200  # the history kept for the loops

# Things a sentence can name that may tie into something bigger (links.KINDS). People, pets, money and the calendar
# are left out on purpose: tying a person to a project from a passing remark is too easy to get wrong.
MENTIONABLE = ("asset", "property", "material", "skill", "inventory_item", "component", "product", "business",
               "flock", "craft_recipe", "recipe", "energy_source", "place", "textbook", "trip")
TARGETS = ("project", "intent", "mission")  # what can be started weeks ago and still be open
_NOTE_KINDS = ("idea", "dropped_goal")  # from life_notes: set aside, not finished
_DONE = frozenset({"done", "complete", "completed", "finished", "archived", "achieved", "abandoned", "dropped",
                   "cancelled", "canceled", "sold"})
_LABELS = {"project": "project", "intent": "goal", "mission": "mission", "idea": "idea they set aside",
           "dropped_goal": "goal they set aside"}

_STOP = frozenset("""about after again also back been before being both build building came come could does doing done
down each even every from going gonna good great have here into just know like little made make making many maybe more
most much need only other over plan planning pretty project really right said same some something someday start started
still such sure take than that their them then there these they thing things think this those time today very want
wanna week well were what when where which while will with work working would year your yours""".split())


def _words(text: str) -> set:
    """Pure logic. The distinctive words of a text: lowercase, four letters or more, common words dropped, a plain
    plural folded ("boards" to "board"), so "chicken feed" meets "a chicken tractor"."""
    out = set()
    for w in re.findall(r"[a-z][a-z']+", (text or "").lower()):
        w = w.strip("'")
        if len(w) < 4 or w in _STOP:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def _names(name: str, said_lower: str) -> bool:
    """Pure logic. Whether lowercased text names a thing outright: its whole name as words (a plain plural allowed),
    three letters or more so "TV" or "a" never match by accident."""
    name = (name or "").strip().lower()
    if len(name) < 3:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(name) + r"s?(?![a-z0-9])", said_lower) is not None


def _mentioned(name: str, reply: str) -> bool:
    """Pure logic. Whether her reply brought a thing up: its name outright, or (for a long name like an idea) most of
    its distinctive words."""
    if _names(name, (reply or "").lower()):
        return True
    key = _words(name)
    return bool(key) and len(key & _words(reply)) >= min(2, len(key))


def _date_of(value) -> Optional[date]:
    """Pure logic. The date of an ISO date or datetime string, or None when there isn't a readable one."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:19]).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _snippet(text: str, limit: int = 140) -> str:
    """Pure logic. What was said, on one line and short enough to quote back."""
    one = " ".join((text or "").split())
    return one if len(one) <= limit else one[:limit - 1].rstrip() + "…"


def _named(context, said_lower: str) -> list:
    """The records the words name outright, of the kinds a passing remark can tie in: (kind, ref, name) each."""
    from core import links

    out = []
    for kind in MENTIONABLE:
        for record in links.records(context, kind):
            name = str(getattr(record, links.KINDS[kind].name_attr, "") or "").strip()
            if _names(name, said_lower):
                out.append((kind, links.ref_of(kind, record), name))
    return out


def _targets(context) -> list:
    """The open things a remark could tie into: projects, goals and missions not finished, and ideas or goals set
    aside, each with when it began (None when its date can't be read)."""
    from core import links

    out = []
    for kind in TARGETS:
        for record in links.records(context, kind):
            name = str(getattr(record, links.KINDS[kind].name_attr, "") or "").strip()
            status = str(getattr(record, "status", "") or "").strip()
            if not name or status.lower() in _DONE:
                continue
            out.append({"ref": links.ref_of(kind, record), "kind": kind, "name": name, "status": status,
                        "text": f"{name} {getattr(record, 'description', '') or ''}",
                        "since": _date_of(getattr(record, "created_at", ""))})
    notes = getattr(context, "life_notes", None)
    if notes is not None and hasattr(notes, "of_kind"):
        for kind in _NOTE_KINDS:
            for note in notes.of_kind(kind, open_only=True):
                out.append({"ref": f"note:{note['id']}", "kind": kind, "name": note["what"], "status": "",
                            "text": f"{note['what']} {note.get('why', '')}", "since": _date_of(note.get("at", ""))})
    return out


def find(context, text: str, today: Optional[date] = None) -> list:
    """The connections a remark makes, best first: through the link graph from a thing it names, then by a
    distinctive word it shares with an open thing. Each is a target dict plus `via` ("link" or "words"), `through`
    (the named thing, if any), `through_kind` and `shared`."""
    from core import links

    today = today or date.today()
    said = (text or "").lower()
    named = _named(context, said)
    targets = [t for t in _targets(context)
               if t["since"] is not None and (today - t["since"]).days >= MIN_AGE_DAYS and not _names(t["name"], said)]
    if not targets:
        return []
    by_ref = {t["ref"]: t for t in targets}
    found, seen = [], set()
    for kind, ref, name in named:
        try:
            touching = links.links_for(context, ref)
        except Exception:  # noqa: BLE001 - a graph that won't read just means no graph connection this turn
            log.exception("Couldn't read the links for a connection.")
            touching = []
        for link in touching:
            other = link.target if link.source == ref else link.source
            if other in by_ref and other not in seen:
                seen.add(other)
                found.append({**by_ref[other], "via": "link", "through": name, "through_kind": kind, "shared": []})
    words = _words(text)
    for t in targets:
        if t["ref"] in seen:
            continue
        shared = sorted(words & _words(t["text"]))
        if shared and (len(shared) >= 2 or any(len(w) >= 5 for w in shared)):
            seen.add(t["ref"])
            first = named[0] if named else ("", "", "")
            found.append({**t, "via": "words", "through": first[2], "through_kind": first[0], "shared": shared[:3]})
    return found


def _age(since: str, today: date) -> str:
    """Pure logic. How long ago something began, in words: "3 weeks", "10 days"."""
    began = _date_of(since)
    if began is None:
        return "a while"
    days = (today - began).days
    return f"{days // 7} weeks" if days >= 14 else f"{days} days"


class ConnectionBook:
    """A person's noticed connections (connections.json): what they said, what it ties into, and whether MIA brought
    it up. Sealed at rest; one open connection per thing; the history feeds the two connection loops."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at the person's connections.json (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.items: list[dict] = []
        self.quiet: list[str] = []
        self._load()

    def _load(self) -> None:
        """Reads the connections; a missing file starts empty, one that won't open is set aside (DEC-0126)."""
        try:
            raw = json.loads(open_text(self._file))
        except FileNotFoundError:
            return
        except (ValueError, OSError):
            log.exception("Couldn't read connections.json, starting empty.")
            return
        self.items = list(raw.get("connections", []))
        self.quiet = list(raw.get("quiet", []))  # refs the person asked never to be raised ("don't bring that up")

    def _save(self) -> None:
        """Writes the connections and the quiet list atomically (undoable), sealed at rest, keeping the newest
        `_KEEP` connections."""
        self.items = self.items[-_KEEP:]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"connections": self.items, "quiet": self.quiet}, indent=1,
                                                 ensure_ascii=False))

    def open_ones(self) -> list:
        """The connections still waiting to be brought up, oldest first."""
        return [c for c in self.items if c.get("state") == "open"]

    def _recent(self, ref: str, now: datetime) -> bool:
        """Whether this thing is already held, or was settled inside the cooldown, so it isn't raised twice."""
        cutoff = (now - timedelta(days=COOLDOWN_DAYS)).isoformat(timespec="seconds")
        if ref in self.quiet:
            return True  # they asked her not to bring it up
        return any(c["ref"] == ref and (c["state"] == "open" or c.get("settled_at", "") >= cutoff) for c in self.items)

    def consider(self, found: list, said: str, now: Optional[datetime] = None) -> Optional[dict]:
        """Keep the best new connection from `find` (one per turn, at most MAX_OPEN held), or None when there's
        nothing new to keep."""
        now = now or datetime.now()
        if len(self.open_ones()) >= MAX_OPEN:
            return None
        for f in found:
            if self._recent(f["ref"], now):
                continue
            item = {"id": uuid.uuid4().hex[:10], "ref": f["ref"], "kind": f["kind"], "name": f["name"][:80],
                    "status": f.get("status", ""), "since": f["since"].isoformat() if f.get("since") else "",
                    "via": f["via"], "through": f.get("through", "")[:60], "through_kind": f.get("through_kind", ""),
                    "shared": list(f.get("shared", [])), "said": _snippet(said),
                    "noticed_at": now.isoformat(timespec="seconds"), "state": "open", "settled_at": ""}
            self.items.append(item)
            self._save()
            return item
        return None

    def settle(self, reply: str, now: Optional[datetime] = None) -> list:
        """After a reply: a connection she named is mentioned; one held past EXPIRE_DAYS is let go. Returns the ones
        settled now."""
        now = now or datetime.now()
        stale = (now - timedelta(days=EXPIRE_DAYS)).isoformat(timespec="seconds")
        changed = []
        for c in self.open_ones():
            if reply and _mentioned(c["name"], reply):
                c["state"] = "mentioned"
            elif c["noticed_at"] <= stale:
                c["state"] = "expired"
            else:
                continue
            c["settled_at"] = now.isoformat(timespec="seconds")
            changed.append(c)
        if changed:
            self._save()
        return changed

    def get(self, connection_id: str) -> Optional[dict]:
        """The connection with this id, or None."""
        return next((c for c in self.items if c.get("id") == connection_id), None)

    def decline(self, connection_id: str, now: Optional[datetime] = None) -> dict:
        """"Don't bring that up" (DEC-0146): the connection is settled as declined and its thing joins the quiet list,
        so it's never raised again until allowed. ValueError for an unknown one."""
        c = self.get(connection_id)
        if c is None:
            raise ValueError("No connection with that id.")
        now = now or datetime.now()
        if c.get("state") == "open":
            c["state"], c["settled_at"] = "declined", now.isoformat(timespec="seconds")
        if c["ref"] not in self.quiet:
            self.quiet.append(c["ref"])
        self._save()
        return c

    def allow(self, ref: str) -> None:
        """Takes a thing off the quiet list, so MIA may tie things to it again (after the usual cooldown)."""
        self.quiet = [r for r in self.quiet if r != ref]
        self._save()

    def due(self, now: Optional[datetime] = None) -> Optional[dict]:
        """The newest open connection that has waited HOLD_HOURS, so it lands in a later conversation; None if none."""
        now = now or datetime.now()
        ready = (now - timedelta(hours=HOLD_HOURS)).isoformat(timespec="seconds")
        waiting = [c for c in self.open_ones() if c["noticed_at"] <= ready]
        return waiting[-1] if waiting else None

    def context_block(self, now: Optional[datetime] = None) -> str:
        """The one connection to carry into this conversation, framed so it's raised only if it fits, once, in her
        own words; "" when nothing is due."""
        now = now or datetime.now()
        c = self.due(now)
        if c is None:
            return ""
        said_on = _date_of(c["noticed_at"])
        when = f"{said_on.strftime('%b')} {said_on.day}" if said_on else "Earlier"
        how = (f", through the {c['through']}" if c["via"] == "link" and c["through"]
               else f"; both are about {', '.join(c['shared'])}" if c["shared"] else "")
        still = f", still {c['status']}" if c["status"] else ""
        return ("A connection you noticed between things this person has going. Bring it up only if it fits "
                "naturally in this conversation: one sentence, in your own words, as something you remembered, then "
                "let it go. Never force it, and skip it if they're busy with something else.\n"
                f"On {when} they said “{c['said']}”. That ties into their {_LABELS.get(c['kind'], c['kind'])} "
                f"“{c['name']}”, started {_age(c['since'], now.date())} ago{still}{how}.")

    def stats(self, since: str) -> dict:
        """Counts for the loops since an ISO time: noticed, mentioned, expired, declined ("don't bring that up"), and
        `unlinked`, the ties found only by shared words between a named thing and a target, counted by (kind, kind)
        and never by name."""
        recent = [c for c in self.items if c.get("noticed_at", "") >= since]
        settled = [c for c in self.items if c.get("settled_at", "") >= since]
        unlinked = Counter((c["through_kind"], c["kind"]) for c in recent if c["via"] == "words" and c["through_kind"])
        return {"noticed": len(recent), "mentioned": sum(c["state"] == "mentioned" for c in settled),
                "expired": sum(c["state"] == "expired" for c in settled),
                "declined": sum(c["state"] == "declined" for c in settled), "unlinked": unlinked}


def _last_reply(conversation) -> str:
    """Her last reply in the conversation, or "" before she's said anything."""
    for message in reversed(getattr(conversation, "messages", None) or []):
        if getattr(message, "role", "") == "assistant":
            return getattr(message, "content", "") or ""
    return ""


def notice(context, conversation, prompt: str, now: Optional[datetime] = None) -> Optional[dict]:
    """Before a turn: settle what her last reply brought up, then keep any new connection this remark makes. Never in
    a private or personal conversation (the same rule notes from conversation keep, DEC-0054); None when nothing new
    was kept."""
    from core.life_notes import _private

    book = getattr(context, "connections", None)
    if book is None or _private(conversation) or not (prompt or "").strip():
        return None
    now = now or datetime.now()
    book.settle(_last_reply(conversation), now)
    return book.consider(find(context, prompt, now.date()), prompt, now)


def connections_for(context, now: Optional[datetime] = None) -> str:
    """The everyday conversation's connection line (`core/assistant_chat.py`), or "" when there's no book or nothing
    due. Never raises: a connection is a nicety, never a reason a turn fails."""
    book = getattr(context, "connections", None)
    if book is None or not hasattr(book, "context_block"):
        return ""
    try:
        return book.context_block(now)
    except Exception:  # noqa: BLE001 - see above
        log.exception("Couldn't build the connection line.")
        return ""
