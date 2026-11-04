"""
core.council_session
======================

Council Mode through the glasses (DEC-0081/0082, T-0035; H-0081 1.4;
`docs/COUNCIL_AND_CHRONICLES_REVIEW.md` section 4.2). A session is a thread
of the council chat (core/council.py) in a mode, the way User Sync is: while
it's open, what Zac says through the glasses means something to the council.

- "MIA, bring the council together" (or "council mode") opens it.
- A member's name first ("Claude, start us off", "Codex, look for risks")
  asks that member; "everyone" or "the council" asks all who are here; two
  names and "debate" is a debate: the rules are the floor's
  (core/council_floor.py: budgets, members asking each other through MIA).
- "Sum up" or "where do we stand?" is MIA, from what was said, at no cost.
- "Hold on" or "stop" stops whoever is speaking; "that's all" or "end the
  council" closes the session (and its capture, T-0024/DEC-0083).
- Anything else goes to the thread and asks no one.

Members answer in the background (a cloud member takes 10 to 60 seconds):
MIA says at once who's looking, and each answer reaches the glasses as a card
with the speaker's name, voice and a short spoken version
(core/glasses_feed.council_said); the full answer is in the chat.

Speech recognition hears names its own way ("cloud" for Claude, "chat GPT",
"co-pilot"), so `NAMES` maps what it hears to the member.
"""

from __future__ import annotations

import re
import threading
from typing import Optional

OPEN = re.compile(r"\b(bring (the )?council (together|in)|council mode|summon the council|convene the council|"
                  r"assemble the council|call the council)\b", re.I)
END = re.compile(r"^\s*(that'?s all|end the council|close the council|we'?re done( here)?|dismiss the council|"
                 r"council dismissed)\b", re.I)
SUM = re.compile(r"\b(sum (it )?up|summari[sz]e|where do we stand|what'?s the consensus)\b", re.I)
HOLD = re.compile(r"^\s*(hold on|stop|wait|pause)\b", re.I)
EVERYONE = re.compile(r"\b(everyone|everybody|the council|all of you|each of you)\b", re.I)
# What speech recognition hears -> the member.
NAMES = {"claude": "claude", "cloud": "claude", "clod": "claude", "chatgpt": "chatgpt", "chat gpt": "chatgpt",
         "chat g p t": "chatgpt", "gpt": "chatgpt", "codex": "codex", "code x": "codex", "copilot": "copilot",
         "co-pilot": "copilot", "co pilot": "copilot", "qwen": "qwen", "quinn": "qwen", "gwen": "qwen",
         "coder": "coder", "mia": "mia", "maya": "mia"}
SPOKEN_WORDS = 45  # what a member says aloud; the rest is in the chat

_sessions: dict[str, dict] = {}  # profile_id -> {"thread": id}
_lock = threading.Lock()


def active(profile_id: str) -> bool:
    with _lock:
        return profile_id in _sessions


def spoken(text: str, words: int = SPOKEN_WORDS) -> str:
    """Pure logic. What a member says aloud: whole sentences up to `words`, never an ASK line."""
    plain = re.sub(r"(?mi)^\s*(ASK\s+\w+\s*:.*|AGREE)\s*$", "", text or "")
    plain = re.sub(r"[*#`>_]+", "", plain)
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(plain.split()))
    out: list[str] = []
    for s in sentences:
        if out and len(" ".join(out + [s]).split()) > words:
            break
        out.append(s)
    said = " ".join(out)
    return said if len(said.split()) <= words + 15 else " ".join(said.split()[:words]) + "…"


def addressed(text: str) -> tuple[str, list[str]]:
    """Pure logic. The words as a council message, and the members they name. "Claude, start us off"
    -> ("@claude start us off", ["claude"]); "everyone, thoughts?" -> ("@all thoughts?", [])."""
    lowered = " ".join((text or "").lower().replace(",", " , ").split())
    named: list[str] = []
    for heard in sorted(NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(heard)}\b", lowered):
            member = NAMES[heard]
            if member not in named:
                named.append(member)
            lowered = re.sub(rf"\b{re.escape(heard)}\b", " ", lowered)
    rest = " ".join(lowered.replace(" , ", " ").split()).strip(" ,.")
    if not named and EVERYONE.search(text or ""):
        return f"@all {rest}".strip(), []
    return (" ".join(f"@{m}" for m in named) + " " + rest).strip(), named


def hear(context, profile_id: str, text: str, run=None) -> Optional[dict]:
    """The words, if they're the council's: {"say", "council": True}. None when Council Mode isn't open
    and they don't open it. `run(message)` works a message through the floor in the background."""
    from core import council

    words = " ".join((text or "").split())
    if not active(profile_id):
        if not OPEN.search(words):
            return None
        from core.work_dashboard import allowed

        if not allowed(context, profile_id):  # the council is the owner's, as the dev window is
            return None
        root = council.post("zac", "Council Mode, from the glasses: " + words, kind="message")
        with _lock:
            _sessions[profile_id] = {"thread": root["id"]}
        here = [council.members()[m]["name"] for m in council.here() if m != "mia"]
        who = (", ".join(here[:-1]) + " and " + here[-1]) if len(here) > 1 else (here[0] if here else "")
        return {"say": f"The council's here: {who}. Who goes first?" if who else
                "I'm here, but the rest of the council isn't reachable right now. You can still talk it through with me.",
                "council": True}
    with _lock:
        thread = _sessions[profile_id]["thread"]
    if END.match(words):
        with _lock:
            _sessions.pop(profile_id, None)
        council.post("mia", "Council Mode closed.", kind="note", reply_to=thread, thread=thread)
        return {"say": "Closing the council. Everything's in the chat.", "council": True, "ended": True}
    if HOLD.match(words):
        council.post("zac", "stop", reply_to=thread, thread=thread)
        return {"say": "Stopped.", "council": True}
    if SUM.search(words):
        message, named = "@mia " + words, ["mia"]
    else:
        message, named = addressed(words)
    from core import council_floor

    ready = council_floor.ready_members()
    posted = council.post("zac", message, reply_to=thread, thread=thread,
                          plan=council_floor.plan(message, sorted(ready)))
    if not posted["plan"]["order"]:
        return {"say": "Noted.", "council": True}
    roster = council.members()
    here = [m for m in posted["plan"]["order"] if m in ready]
    away = [roster.get(m, {}).get("name", m) for m in posted["plan"]["order"] if m not in ready]
    missing = (" and ".join(away) + (" isn't" if len(away) == 1 else " aren't") + " available right now. ") if away else ""
    if not here:
        return {"say": missing.strip(), "council": True}
    (run or _run_in_background)(profile_id, posted)  # the floor skips who's away, and says so in the chat
    first = here[0]
    return {"say": missing + ("Let me look." if first == "mia" else f"{roster[first]['name']} is looking."), "council": True}


def _run_in_background(profile_id: str, message: dict) -> None:
    def work() -> None:
        from core import council, council_floor
        from core.glasses_feed import council_said

        def heard(m: dict) -> None:  # each answer as it comes, not after the whole turn
            if m.get("kind") in ("answer", "summary") and m.get("who") in council.members():
                council_said(profile_id, m["who"], m["text"])
        council_floor.run(message, on_said=heard)
    threading.Thread(target=work, daemon=True).start()
