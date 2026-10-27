"""
core.failure_log
==================

Where MIA stumbles, so it gets fixed (DEC-0049; Zac, 2026-10-27): "a log
that you can be sent to audit the users interactions with MIA, see when
she fails, why she fails, when the user runs into an issue and then use
that information to fix her ... nearly self developing in a way that
doesnt break her."

**What's recorded** (each person's own, `failures.jsonl` in their
folder, append-only so the phone's and the PC's merge line by line):
- what the person says: "no, I meant…", "that's wrong", "MIA, report a
  problem: …", a 👎 on a reply;
- what MIA can see herself: a tool that errored, the model down or
  answering garbled, a command-sounding request no tool matched, the
  right tool offered but the model talked instead, the same thing asked
  again in other words within two minutes, "undo" within three minutes
  of her answer, a slow answer, a page that broke.
Each with when, what was said (redacted: no emails, long numbers or
anything after "password"), her reply, the mode, the tools, the error.
Never an off-the-record, journal or private turn.

**Three tiers, so she grows without breaking** (`docs/FAILURE_LOG.md`):
1. *What she learns herself, only after a yes*: "when I say X I mean Y"
   (taught, or offered after a retry worked), each person's own, kept in
   `failure_state.json` through atomic_write_text so it can be undone.
   Routing then attaches that tool when X is said.
2. *What she asks before changing*: settings (as issues for now).
3. *What she never changes herself: her code.* `fix_report()` writes the
   ranked issues with their examples and a test case for each, for
   Claude to turn into failing tests, fix, and bench, Zac approving.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "failures.jsonl"
_STATE = "failure_state.json"
_MAX_LINES = 5000
_lock = threading.Lock()

# kind: (plain words, weight in the ranking)
KINDS = {
    "report": ("you reported a problem", 4),
    "said_wrong": ("you said she got it wrong", 4),
    "thumbs_down": ("a 👎 on her reply", 4),
    "tool_error": ("a tool broke", 4),
    "model_down": ("the model didn't answer", 2),
    "garbled": ("the model's answer was garbled", 2),
    "no_tool": ("a request no tool matched", 2),
    "talked_instead": ("the right tool was there but she only talked", 3),
    "rephrased": ("you asked again in other words", 2),
    "undo_soon": ("you undid what she did right away", 3),
    "slow": ("a slow answer", 1),
    "page_error": ("a page broke", 3),
}
REPHRASE_SECONDS = 120
UNDO_SECONDS = 180
SLOW_SECONDS = 25

_REPORT = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:report (?:a |this )?(?:problem|bug|issue)|"
                     r"(?:that'?s|this is) a bug|log (?:a |this as a )?(?:problem|bug))\b[\s:,.-]*(.*)$", re.IGNORECASE)
_WRONG = re.compile(r"\b(?:no,? i meant|that'?s (?:wrong|not (?:right|it|what i (?:asked|meant|said|wanted)))|"
                    r"you got (?:it|that) wrong|wrong (?:answer|tool|thing)|not what i (?:asked|meant|wanted)|"
                    r"i didn'?t (?:ask|say) (?:that|for that)|that'?s not what i)\b", re.IGNORECASE)
_UNDO = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?undo\b", re.IGNORECASE)
_TEACH = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?when i say\s+[\"“']?(.+?)[\"”']?,?\s+i mean\s+(.+?)\s*\.?$", re.IGNORECASE)
_REMEMBER_YES = re.compile(r"^\s*(?:yes|yeah|yep|sure|ok(?:ay)?)?[,.!\s]*(?:remember (?:that|it)|please do|do it)?\s*[.!]?\s*$",
                           re.IGNORECASE)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_LONG_NUMBER = re.compile(r"\d[\d\s-]{5,}\d")
_SECRET = re.compile(r"\b(password|passcode|passphrase|pin|code)\b(\s*(?:is|:|=)?\s*)\S+", re.IGNORECASE)


def redact(text: str, limit: int = 300) -> str:
    """Pure logic. What a log may keep of someone's words: no emails, no
    long numbers (cards, accounts, phones), nothing after "password"."""
    out = _SECRET.sub(lambda m: m.group(1) + m.group(2) + "[hidden]", str(text or ""))
    out = _EMAIL.sub("[email]", out)
    out = _LONG_NUMBER.sub("[number]", out)
    out = " ".join(out.split())
    return out if len(out) <= limit else out[: limit - 1] + "…"


def _words(text: str) -> str:
    """Pure logic. Lower-case words only: "Just got off work!" -> "just got off work"."""
    return " ".join(re.findall(r"[a-z0-9']+", str(text or "").lower()))


def similar(a: str, b: str) -> float:
    """Pure logic. How alike two requests are (shared words, Jaccard)."""
    wa = {w for w in re.findall(r"[a-z0-9']+", a.lower()) if len(w) > 2}
    wb = {w for w in re.findall(r"[a-z0-9']+", b.lower()) if len(w) > 2}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def issue_key(kind: str, tool: str = "", page: str = "", error: str = "") -> str:
    """Pure logic. What groups events into one issue."""
    if kind == "tool_error":
        return f"tool:{tool}"
    if kind in ("model_down", "garbled", "slow"):
        return kind
    if kind == "page_error":
        return f"page:{page}:{(error or '')[:60]}"
    if kind == "talked_instead":
        return f"routing:{tool}"
    if kind in ("said_wrong", "rephrased", "undo_soon", "thumbs_down"):
        return f"turn:{tool or 'chat'}"
    return kind


def _stamp(text: str) -> Optional[datetime]:
    try:
        when = datetime.fromisoformat(str(text or ""))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc).astimezone(timezone.utc)


class FailureLog:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._state_file = self.data_dir / _STATE
        self._load()

    # ---------------------------------------------------------------- state: issue status, learned phrases

    def _load(self) -> None:
        self.status: dict[str, dict] = {}
        self.phrases: list[dict] = []
        if not self._state_file.exists():
            return
        try:
            raw = json.loads(self._state_file.read_text(encoding="utf-8"))
            self.status = {str(k): dict(v) for k, v in (raw.get("status") or {}).items()}
            self.phrases = [dict(p) for p in raw.get("phrases") or []]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("failure_state.json unreadable — starting empty.")

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._state_file, json.dumps({"status": self.status, "phrases": self.phrases}, indent=2))

    def set_status(self, key: str, status: str) -> None:
        if status not in ("open", "fixed", "ignored"):
            raise ValueError("An issue is open, fixed or ignored.")
        self.status[key] = {"status": status, "at": datetime.now().isoformat(timespec="seconds")}
        self._save()

    def learn(self, said: str, tool: str, meaning: str = "") -> dict:
        said = " ".join(str(said or "").lower().split()).strip(" .!?\"“”'")
        if len(said) < 3:
            raise ValueError("What do you say?")
        self.phrases = [p for p in self.phrases if p["said"] != said]
        phrase = {"phrase_id": uuid.uuid4().hex[:10], "said": said, "tool": tool, "meaning": meaning.strip(),
                  "created_at": datetime.now().isoformat(timespec="seconds")}
        self.phrases.append(phrase)
        self._save()
        return phrase

    def forget(self, phrase_id: str) -> None:
        if not any(p["phrase_id"] == phrase_id for p in self.phrases):
            raise ValueError("That isn't remembered anymore.")
        self.phrases = [p for p in self.phrases if p["phrase_id"] != phrase_id]
        self._save()

    def phrases_in(self, prompt: str) -> list[dict]:
        low = " " + _words(prompt) + " "
        return [p for p in self.phrases if f" {_words(p['said'])} " in low]

    # ---------------------------------------------------------------- the log

    def record(self, kind: str, **fields) -> Optional[dict]:
        if kind not in KINDS:
            raise ValueError(f"Unknown kind '{kind}'.")
        event = {"event_id": uuid.uuid4().hex[:12], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "kind": kind}
        for name in ("prompt", "reply", "note", "before"):
            if fields.get(name):
                event[name] = redact(fields[name])
        for name in ("tool", "mode", "error", "page", "model", "surface"):
            if fields.get(name):
                event[name] = str(fields[name])[:200]
        if fields.get("tools"):
            event["tools"] = [str(t) for t in fields["tools"]][:8]
        if fields.get("seconds") is not None:
            event["seconds"] = round(float(fields["seconds"]), 1)
        event["key"] = issue_key(kind, event.get("tool", ""), event.get("page", ""), event.get("error", ""))
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with _lock:
                with open(self._file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                self._trim()
        except OSError:
            log.exception("Couldn't write the failure log.")
            return None
        # A fixed issue that happens again is open again.
        if self.status.get(event["key"], {}).get("status") == "fixed":
            self.status[event["key"]] = {"status": "open", "at": event["at"], "reopened": True}
            self._save()
        return event

    def _trim(self) -> None:
        lines = self._file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_LINES:
            self._file.write_text("\n".join(lines[-(_MAX_LINES * 3 // 5):]) + "\n", encoding="utf-8")

    def events(self, days: Optional[int] = None) -> list[dict]:
        if not self._file.exists():
            return []
        since = datetime.now(timezone.utc) - timedelta(days=days) if days else None
        out = []
        for line in self._file.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            at = _stamp(e.get("at"))
            if since is None or (at is not None and at >= since):
                out.append(e)
        return out

    def issues(self, days: int = 30) -> list[dict]:
        """Events grouped by what went wrong, worst first: how often, how
        recently, how much it mattered (KINDS' weights)."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for e in self.events(days):
            groups[e.get("key") or e["kind"]].append(e)
        out = []
        for key, items in groups.items():
            items.sort(key=lambda e: e["at"])
            kinds = sorted({e["kind"] for e in items}, key=lambda k: -KINDS[k][1])
            weight = sum(KINDS[e["kind"]][1] for e in items)
            status = self.status.get(key, {})
            out.append({"key": key, "title": title_for(key, items), "count": len(items), "kinds": kinds,
                        "said": [KINDS[k][0] for k in kinds], "first": items[0]["at"], "last": items[-1]["at"],
                        "weight": weight, "status": status.get("status", "open"), "reopened": bool(status.get("reopened")),
                        "examples": [{k: e[k] for k in ("at", "kind", "prompt", "reply", "before", "note", "error", "tools",
                                                       "tool", "page", "seconds") if k in e} for e in items[-3:][::-1]]})
        order = {"open": 0, "fixed": 1, "ignored": 2}
        out.sort(key=lambda i: i["last"], reverse=True)  # newest first among equals
        return sorted(out, key=lambda i: (order[i["status"]], -i["weight"]))


def title_for(key: str, items: list[dict]) -> str:
    """Pure logic. An issue's name in plain words."""
    kind, _, rest = key.partition(":")
    if kind in ("tool", "routing", "turn"):
        rest = rest.replace("_", " ")  # log_shift -> "log shift": a name, not code
    if kind == "tool":
        return f"The {rest} tool broke"
    if kind == "routing":
        return f"Offered {rest} but only talked"
    if kind == "turn":
        return "Wrong answer in chat" if rest == "chat" else f"Wrong result from {rest}"
    if kind == "page":
        return f"A page broke: {rest.split(':', 1)[0]}"
    return {"model_down": "The model didn't answer", "garbled": "Garbled answers", "slow": "Slow answers",
            "no_tool": "Requests MIA couldn't match to anything", "report": "Problems you reported"}.get(key, key)


# ---------------------------------------------------------------- the hooks (all surfaces)


def _log(context) -> Optional[FailureLog]:
    return getattr(context, "failures", None)


def _private(conversation) -> bool:
    return conversation is not None and bool(conversation.off_record or conversation.journal or conversation.private_turn)


def _last(conversation, role: str, skip: int = 0):
    seen = 0
    for m in reversed(conversation.messages or []):
        if m.role == role:
            if seen == skip:
                return m
            seen += 1
    return None


def _age(message) -> Optional[float]:
    at = _stamp(getattr(message, "timestamp", ""))
    return (datetime.now(timezone.utc) - at).total_seconds() if at is not None else None


def observe_prompt(context, conversation, prompt: str) -> Optional[str]:
    """Before a turn (core/talk_it_out.pre_turn): what the person's words
    say about the last answer. Returns a reply when the message is for the
    log itself (a report, a phrase taught or confirmed)."""
    book = _log(context)
    if book is None or conversation is None or _private(conversation):
        return None
    text = str(prompt or "")
    m = _REPORT.match(text)
    if m:
        last_user, last_reply = _last(conversation, "user"), _last(conversation, "assistant")
        book.record("report", note=m.group(1) or text, before=getattr(last_user, "content", ""),
                    reply=getattr(last_reply, "content", ""), mode=conversation.mode)
        return "Got it. I've logged that so it gets fixed. (It's in Apps → Fix-It Log.)"
    m = _TEACH.match(text)
    if m:
        return _teach(context, book, m.group(1), m.group(2))
    offer = getattr(conversation, "pending_phrase", None)
    if offer and _REMEMBER_YES.match(text):
        conversation.pending_phrase = None
        book.learn(offer["said"], offer["tool"], offer.get("meaning", ""))
        return f"Remembered: when you say “{offer['said']}”, you mean that. (Forget it any time in the Fix-It Log.)"
    conversation.pending_phrase = None
    last_user, last_reply = _last(conversation, "user"), _last(conversation, "assistant")
    if last_reply is None or last_user is None:
        return None
    age = _age(last_reply)
    tool = getattr(conversation, "last_tool", "") or ""
    if _WRONG.search(text):
        book.record("said_wrong", prompt=text, before=last_user.content, reply=last_reply.content, tool=tool,
                    mode=conversation.mode)
        conversation.retry_of = last_user.content
    elif _UNDO.match(text) and age is not None and age <= UNDO_SECONDS:
        book.record("undo_soon", prompt=last_user.content, reply=last_reply.content, tool=tool, mode=conversation.mode)
    elif age is not None and age <= REPHRASE_SECONDS and similar(text, last_user.content) >= 0.5 \
            and text.strip().lower() != last_user.content.strip().lower():
        book.record("rephrased", prompt=text, before=last_user.content, reply=last_reply.content, tool=tool,
                    mode=conversation.mode)
        conversation.retry_of = last_user.content
    return None


def _teach(context, book: FailureLog, said: str, meaning: str) -> str:
    registry = getattr(context, "assistant_actions", None)
    matched = registry.matching_actions(meaning, context) if registry is not None else []
    named = [a for a in matched if a.domain != "system"] or matched
    if not named:
        book.record("report", note=f"Taught “{said}” = “{meaning}”, but no tool does that yet.")
        return f"I don't know what “{meaning}” does yet, so I can't link it. I've logged it as a problem instead."
    tool = best_tool(meaning, named)
    book.learn(said, tool, meaning)
    return f"Remembered: when you say “{said.strip()}”, you mean {meaning.strip().rstrip('.')}."


def best_tool(meaning: str, actions: list) -> str:
    """Pure logic. The tool a meaning describes best: its own trigger
    phrases first, then the words it shares with the tool's name and
    description."""
    low = " " + _words(meaning) + " "
    said = set(low.split())

    def score(a) -> tuple:
        phrase = max((len(p) for p in a.trigger_phrases if f" {_words(p)} " in low), default=0)
        name = len(said & set(a.name.split("_")))
        words = len(said & set(_words(a.description).split()))
        return (phrase, name, words)

    return max(actions, key=score).name


def observe_turn(context, conversation, prompt: str, *, tools_offered: list, tool_called: str = "",
                 reply: str = "", llm_available: bool = True, seconds: float = 0.0, garbled: bool = False) -> Optional[str]:
    """After a turn (core/assistant_turn.py): what MIA can see went wrong.
    Returns a line to add when a retry just worked (the offer to remember
    the first wording)."""
    from core.conversation_modes import looks_like_direct_command

    book = _log(context)
    if book is None or _private(conversation):
        return None
    model = getattr(getattr(context, "llm", None), "model", "") or ""
    mode = getattr(conversation, "mode", "")
    if conversation is not None:
        conversation.last_tool = tool_called
    if not llm_available:
        book.record("model_down", prompt=prompt, mode=mode, model=model)
    elif garbled:
        book.record("garbled", prompt=prompt, reply=reply, mode=mode, model=model)
    elif tools_offered and not tool_called and looks_like_direct_command(prompt):
        book.record("talked_instead", prompt=prompt, reply=reply, tools=tools_offered, tool=tools_offered[0],
                    mode=mode, model=model)
    elif not tools_offered and not tool_called and looks_like_direct_command(prompt):
        book.record("no_tool", prompt=prompt, reply=reply, mode=mode, model=model)
    if seconds and seconds > SLOW_SECONDS:
        book.record("slow", prompt=prompt, seconds=seconds, mode=mode, model=model)
    retry_of = getattr(conversation, "retry_of", None) if conversation is not None else None
    if conversation is not None:
        conversation.retry_of = None
    if tool_called and retry_of and similar(retry_of, prompt) < 0.95:
        conversation.pending_phrase = {"said": retry_of, "tool": tool_called, "meaning": prompt}
        return f"(Want me to remember that “{redact(retry_of, 80)}” means this? Say “remember that”.)"
    return None


def observe_tool_error(context, name: str, error: str, arguments: Optional[dict] = None) -> None:
    """A tool that raised (core/assistant_actions.execute)."""
    book = _log(context)
    if book is not None:
        book.record("tool_error", tool=name, error=error,
                    note=", ".join(f"{k}={v}" for k, v in (arguments or {}).items())[:200])


# ---------------------------------------------------------------- the fix report (tier 3)


def fix_report(context, days: int = 30) -> str:
    """The open issues, worst first, each with examples and the test case
    that should be written before it's fixed. For Claude, on the PC; it
    never leaves the person's folder."""
    book = _log(context)
    if book is None:
        return ""
    open_ = [i for i in book.issues(days) if i["status"] == "open"]
    lines = ["# MIA fix report", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}, last {days} days. "
             "Open issues, worst first. Personal: keep out of the repo; turn each into a test, not a copy of these words.", ""]
    if not open_:
        lines.append("Nothing open. 🎉")
    for n, i in enumerate(open_, 1):
        lines += [f"## {n}. {i['title']} ({i['count']}×, {', '.join(i['said'])})", "",
                  f"- key: `{i['key']}` · first {i['first'][:16]} · last {i['last'][:16]}" + (" · came back after a fix" if i["reopened"] else "")]
        for e in i["examples"]:
            bits = [f"{e['at'][:16]} {e['kind']}"]
            for k in ("before", "prompt", "reply", "note", "error", "tools", "seconds"):
                if k in e:
                    bits.append(f"{k}: {e[k]}")
            lines.append("- " + " | ".join(str(b) for b in bits))
        lines += ["", "Test to write first: " + test_hint(i), ""]
    if book.phrases:
        lines += ["## Learned phrasings (tier 1, confirmed by the person)", ""]
        lines += [f"- “{p['said']}” → `{p['tool']}`" + (f" ({p['meaning']})" if p["meaning"] else "") for p in book.phrases]
        lines += ["", "If a phrasing is common, consider a trigger phrase for that tool (with a routing test).", ""]
    return "\n".join(lines)


def test_hint(issue: dict) -> str:
    """Pure logic. The test that should fail before the fix."""
    kind, _, rest = issue["key"].partition(":")
    example = next((e.get("before") or e.get("prompt") for e in issue["examples"] if e.get("before") or e.get("prompt")), "")
    if kind == "tool":
        return f"call the `{rest}` handler with the example's arguments and assert it returns a sentence, not an error."
    if kind == "routing" or issue["key"] == "no_tool":
        return (f"a routing case in tests/test_assistant_routing.py and a bench case in data/model_bench_cases.json: "
                f"“{example}” → the right tool.")
    if kind == "turn":
        return f"reproduce “{example}” and assert the right tool or answer; add it to the live-model bench."
    if kind == "page":
        return f"load the page in the browser test with the demo data and assert no page error ({rest})."
    if issue["key"] in ("slow", "model_down", "garbled"):
        return "check the model and its settings on the PC (python -m tools.pc_check); time the example on the bench."
    return "write down the steps from the report and turn them into a test."


def write_report(context) -> Optional[Path]:
    """The fix report as fix_report.md in the person's own folder (data/,
    never the repo), when there's anything in it."""
    book = _log(context)
    if book is None:
        return None
    text = fix_report(context)
    if "## 1." not in text and "## Learned" not in text:
        return None
    path = book.data_dir / "fix_report.md"
    book.data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path
