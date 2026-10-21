"""
core.capabilities
===================

What MIA can do, built from the code (DEC-0041; the intelligence spec's
Phase 2B, docs/INTELLIGENCE_AUDIT.md). Never a hand-written brochure:

- **Apps** come from `core/web_surfaces.APPS`: name, what it's for,
  where it runs (the web and the desktop, the web only, the desktop only:
  no web screen yet), and whether this person can open it (a child's
  apps are fewer).
- **Tools** come from the Assistant's own registry: for each app, the
  things MIA can look up and the things she can change by being asked,
  from the tool domains the app lists.
- **Changes on screens** come from the action contract
  (`core/actions.ACTION_TYPES`): how many kinds of change each screen can
  propose for approval.
- **Limits** are the one curated part, `LIMITS` below: what an app
  can't do yet, in a sentence. A test fails when an app has no entry
  (an empty string means "none worth saying").

`capability_map()` gathers it; `overview()` and `can_i()` say it.
"""

from __future__ import annotations

import re
from typing import Optional

# What each app can't do yet (DEC-0041: every app has an entry; "" = nothing worth saying).
LIMITS = {
    "web_home": "",
    "dashboard": "Retired: Home shows what it showed.",
    "freedom": "The estimate assumes the last three months' pace; transfers between your own accounts can look like spending until the bank sync sorts them.",
    "compliance": "MIA keeps the list and reminds you; she never files, pays or signs anything, and a deadline isn't confirmed until you verify it.",
    "calendar": "",
    "greenhouse": "No sensors yet: readings are entered by hand.",
    "flock": "",
    "garage": "",
    "kitchen": "",
    "household": "No web screen yet: the desktop has it.",
    "workout": "",
    "real_estate": "Selling a property isn't tracked yet.",
    "missions": "",
    "skills": "",
    "budget": "Connecting and syncing banks needs the desktop on the home computer (the vault passphrase).",
    "maintenance": "Folded into Garage, Property and Greenhouse.",
    "property": "Folded into Real Estate.",
    "workshop": "Cups can't be compared to pounds (no densities).",
    "business": "",
    "insurance": "MIA compares the quotes you collect; she never shops or buys for you.",
    "security": "Cameras need a local stream (no cloud-only cameras).",
    "power": "No web screen yet.",
    "character": "",
    "reward_shop": "",
    "observations": "No web screen yet.",
    "relationships": "",
    "notes": "",
    "classroom": "No web screen yet.",
    "inbox": "Email intake reads one mailbox you set up for MIA.",
    "expeditions": "",
    "vault": "",
    "memories": "No web screen yet.",
    "maps": "No web screen yet.",
    "navigation": "No web screen yet.",
    "knowledge": "No web screen yet.",
    "toolbox": "No web screen yet.",
    "lab": "No web screen yet.",
    "field_kit": "No web screen yet.",
    "passwords": "MIA's assistant never sees a password; no autofill in other apps yet.",
    "files": "",
    "music": "",
    "assistant": "",
    "diagnostics": "No web screen yet.",
    "module_browser": "",
    "settings": "No web screen yet: the desktop has it.",
}


def _tools_by_domain(context) -> dict[str, list]:
    registry = getattr(context, "assistant_actions", None)
    out: dict[str, list] = {}
    if registry is None:
        return out
    for action in getattr(registry, "_actions", {}).values():
        out.setdefault(action.domain, []).append(action)
    return out


def _screen_changes() -> dict[str, int]:
    """How many kinds of change each record prefix proposes ("craft", "flock"...)."""
    from core.actions import ACTION_TYPES

    counts: dict[str, int] = {}
    for kind in ACTION_TYPES:
        prefix = kind.split(".", 1)[0].split("_", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def capability_map(context=None) -> list[dict]:
    """Every app: what it's for, where it runs, whether this person can
    open it, the tools MIA can use in it (look up / change), and its limits."""
    from core.assistant_actions import changes_records
    from core.web_surfaces import APPS, RETIRED, WEB_ONLY

    tools = _tools_by_domain(context) if context is not None else {}
    allowed = None
    if context is not None:
        try:
            from core.child_accounts import app_allowed

            allowed = lambda app_id: app_allowed(context, app_id)  # noqa: E731
        except ImportError:
            allowed = None
    out = []
    for app in APPS:
        mine = [a for domain in app.domains for a in tools.get(domain, [])]
        if app.module_id in RETIRED:
            where = "retired"
        elif app.module_id in WEB_ONLY:
            where = "web"
        elif app.page:
            where = "web and desktop"
        else:
            where = "desktop"
        out.append({
            "id": app.module_id, "name": app.name, "where": where,
            "what": re.sub(r"\s*\(DEC-\d{4}\)", "", app.description),  # a decision number means nothing said aloud
            "open_to_you": True if allowed is None else bool(allowed(app.module_id)),
            "look_up": sorted({a.name for a in mine if not changes_records(a.name)}),
            "change": sorted({a.name for a in mine if changes_records(a.name)}),
            "ask": app.ask, "limits": LIMITS.get(app.module_id, ""),
        })
    return out


def overview(context) -> str:
    """Plain words: what MIA does, app by app, from the code."""
    apps = [a for a in capability_map(context) if a["where"] != "retired" and a["open_to_you"]]
    registry = getattr(context, "assistant_actions", None)
    count = len(getattr(registry, "_actions", {})) if registry is not None else 0
    lines = [f"I have {len(apps)} apps you can use, and {count} things I can look up or do when you ask."]
    for a in apps:
        tail = "" if a["where"] != "desktop" else " (desktop only for now)"
        lines.append(f"{a['name']}: {a['what'].rstrip('.')}{tail}.")
    lines.append("Ask \"can you…?\" about anything and I'll say whether I can, and what's missing if I can't.")
    return " ".join(lines)


_WORD = re.compile(r"[a-z0-9']+")
_SKIP = {"can", "you", "your", "mia", "do", "does", "a", "an", "the", "my", "me", "i", "to", "for", "of", "and", "or",
         "it", "is", "are", "be", "with", "on", "in", "at", "how", "what", "help", "please", "able", "will", "would"}


_SUFFIXES = ("ings", "ing", "ies", "es", "ed", "er", "s")


def _stem(word: str) -> str:
    """Pure logic. A crude stem, enough to match "taxes" with "tax",
    "filings" with "file", "chickens" with "chicken"."""
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    return word[:-1] if len(word) > 3 and word.endswith("e") else word


def _words(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower()) if w not in _SKIP}


def can_i(context, thing: str) -> str:
    """Plain words: whether MIA can do `thing`: the app and tools that
    match it best (by their own names and descriptions), with limits; or
    that nothing matches, never a guess."""
    want = _words(thing)
    if not want:
        return overview(context)
    registry = getattr(context, "assistant_actions", None)
    actions = getattr(registry, "_actions", {}) if registry is not None else {}
    scored = []
    for a in capability_map(context):
        if a["where"] == "retired":
            continue
        # The app's own name counts most, then what it's for, then its example and tools.
        tools_text = " ".join([a["ask"]] + [actions[t].description for t in a["look_up"] + a["change"] if t in actions])
        hit = 3 * len(want & _words(a["name"] + " " + a["id"])) + 2 * len(want & _words(a["what"])) +             len(want & _words(tools_text))
        if hit:
            scored.append((hit, a))
    if not scored:
        return (f"I can't find anything in MIA that does \"{thing.strip()}\". That's a feature MIA doesn't have yet, "
                "as far as my own app list shows.")
    scored.sort(key=lambda x: -x[0])
    best = [a for hit, a in scored if hit == scored[0][0]][:2]
    parts = []
    for a in best:
        how = []
        if a["change"]:
            how.append("I can change things there when you ask")
        if a["look_up"]:
            how.append("look things up")
        where = {"web": "on the web and the phone", "web and desktop": "on the web, the phone and the desktop",
                 "desktop": "on the desktop only for now"}[a["where"]]
        sentence = f"{a['name']} ({where}): {a['what'].rstrip('.')}."
        if how:
            sentence += " " + " and ".join(how).capitalize() + "."
        if not a["open_to_you"]:
            sentence += " It isn't one of your apps (ask a parent)."
        if a["limits"]:
            sentence += f" Limit: {a['limits']}"
        if a["ask"]:
            sentence += f" Try: \"{a['ask']}\""
        parts.append(sentence)
    return "Closest match in MIA: " + " ".join(parts)


def find_app(context, app_id: str) -> Optional[dict]:
    return next((a for a in capability_map(context) if a["id"] == app_id), None)
