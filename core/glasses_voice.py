"""
core.glasses_voice
====================

Talking to MIA through the glasses (H-0041 Phase 3; Zac, 2026-10-19).
The Display glasses pair to the phone as a Bluetooth headset, so MIA's
phone app listens through the glasses' microphone (Android's own speech
recognizer, on the phone), sends the words here, and speaks the answer
back through the glasses' speakers. No Meta toolkit is needed for that;
the toolkit's own microphone access (DEC-0016) can replace the Bluetooth
route later without changing this file.

What the words do:
- **"Open Kitchen"**, "show me my missions", "go to the garage": the
  glasses switch to that app's quick actions (`open`), and MIA says so.
  "Go home" takes them back to her orb.
- **Anything else** ("log lunch", "I weigh 182", "what's on today?") is
  a Talk turn, the same as speaking to MIA on the phone: the plain-word
  commands log at once (with undo), the rest goes to the model.

Either way the glasses hear about it through their feed
(core/glasses_feed.said): a card with what you said and MIA's answer,
and the app to open. A phone linked to the home computer sends the words
there first (that's where the glasses' screen is served from), and
answers itself when the computer can't be reached.
"""

from __future__ import annotations

import re
from typing import Optional

OPEN_WORDS = ("open up", "open", "show me", "show", "go to", "take me to", "bring up", "pull up", "switch to")
HOME_WORDS = ("go home", "home", "back to home", "close", "close it", "go back home", "back to mia")
FILLER = re.compile(r"^(hey |ok |okay )?(mia[, ]+)?(please |can you |could you )?", re.I)
# Other ways people name an app.
ALIASES = {
    "today": "dashboard", "my day": "dashboard", "groceries": "kitchen", "grocery list": "kitchen",
    "recipes": "kitchen", "food": "kitchen", "meals": "kitchen", "car": "garage", "cars": "garage",
    "truck": "garage", "vehicles": "garage", "money": "budget", "bills": "budget", "budget": "budget",
    "quests": "missions", "people": "relationships", "pets": "relationships", "rentals": "real_estate",
    "notes": "notes", "journal": "notes", "photos": "vault", "pictures": "vault", "cameras": "security",
    "plants": "greenhouse", "garden": "greenhouse", "gym": "workout", "training": "workout",
    "trips": "expeditions", "the shop": "reward_shop", "rewards": "reward_shop", "inbox": "inbox",
    "calendar": "calendar", "schedule": "calendar",
}


def _clean(text: str) -> str:
    text = " ".join(str(text or "").lower().replace("’", "'").split())
    return FILLER.sub("", text).strip(" .!?")


def _apps(context) -> list[tuple[str, str]]:
    """(app id, name) of every app this person can open on the glasses."""
    from core.glasses import glasses_apps

    try:
        data = glasses_apps(context)
    except Exception:
        return []
    return [(a["id"], a.get("name") or a["id"]) for a in (data.get("apps") or []) + (data.get("others") or [])]


def app_named(context, phrase: str) -> Optional[tuple[str, str]]:
    """The app a phrase names ("the kitchen", "my missions", "garage"), or None."""
    phrase = re.sub(r"^(the|my|our)\s+", "", _clean(phrase)).strip()
    phrase = re.sub(r"\s+(app|screen|page)$", "", phrase)
    if not phrase:
        return None
    apps = _apps(context)
    by_id = {i: n for i, n in apps}
    for app_id, name in apps:
        if phrase in (name.lower(), app_id.replace("_", " ")):
            return app_id, name
    wanted = ALIASES.get(phrase)
    if wanted in by_id:
        return wanted, by_id[wanted]
    singular = phrase[:-1] if phrase.endswith("s") else phrase + "s"
    for app_id, name in apps:
        if singular == name.lower():
            return app_id, name
    return None


def command(context, text: str) -> Optional[dict]:
    """A glasses command the words are ("open Kitchen", "go home"), or None
    for anything else (that goes to Talk)."""
    said = _clean(text)
    if said in HOME_WORDS:
        return {"open": "", "say": "Here I am."}
    for word in OPEN_WORDS:
        if said.startswith(word + " "):
            found = app_named(context, said[len(word) + 1:])
            if found:
                return {"open": found[0], "say": f"Opening {found[1]}."}
            return None
    return None


def handle(context, profile_id: str, text: str, talk) -> dict:
    """What the words do. `talk(text)` runs a Talk turn and returns its
    answer ({"reply_text", ...}). Returns {"heard", "say", "open"?}, and
    the glasses hear about it through their feed."""
    from core.glasses_feed import said

    heard = " ".join(str(text or "").split())
    if not heard:
        return {"heard": "", "say": "I didn't catch that."}
    found = command(context, heard)
    if found is not None:
        out = {"heard": heard, **found}
    else:
        answer = talk(heard) or {}
        out = {"heard": heard, "say": answer.get("reply_text") or "Done."}
    said(profile_id, out)
    return out
