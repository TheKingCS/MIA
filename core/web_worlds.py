"""
core.web_worlds
=================

Living Worlds on the web (web/worlds.html, DEC-0134 Phases 1 and 2, approved): the person's fictional universes, the
campaigns in each, their central character and its version in each world, and each campaign's quests, over the
living_worlds store (core/living_worlds.py). Everything here is fiction: tagged fictional, never real XP, never real
life (DEC-0137).

Phase 1 is making and keeping: every creation goes through the action system (so it's approved and undoable), and a
campaign can be paused, resumed or ended. Phase 2 is playing: `world.turn` plays one turn in a campaign in play with
MIA as the Dungeon Master (core/dungeon_master.take_turn: the model proposes, the dice and code decide), so a turn is
undoable like any other change ("take that back").

Actions: `world.universe_add`, `world.campaign_add`, `world.character_add`, `world.version_add`, `world.quest_add`,
`world.quest_done`, `world.campaign_status`, `world.turn`. `screen(context, campaign_id)` is what `/api/worlds` serves: the worlds
with their campaigns, the character with its versions, and one campaign opened (the one asked for, or the last played).
"""

from __future__ import annotations

from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

FORMS = {
    "universe": {"fields": [
        {"name": "name", "label": "The world's name", "type": "text", "required": True},
        {"name": "genre", "label": "Genre (fantasy, sci-fi, frontier...)", "type": "text"},
        {"name": "premise", "label": "The premise, in a sentence", "type": "textarea"},
        {"name": "rules", "label": "Tone and house rules", "type": "textarea"}]},
    "campaign": {"fields": [
        {"name": "name", "label": "The campaign's name", "type": "text", "required": True},
        {"name": "summary", "label": "Where it starts", "type": "textarea"}]},
    "character": {"fields": [
        {"name": "name", "label": "Your character's name", "type": "text", "required": True},
        {"name": "note", "label": "Who they are, across every world", "type": "textarea"}]},
    "version": {"fields": [
        {"name": "name", "label": "What they're called in this world", "type": "text", "required": True},
        {"name": "origin", "label": "Where they come from here", "type": "text"},
        {"name": "background", "label": "Their story so far", "type": "textarea"}]},
    "quest": {"fields": [
        {"name": "name", "label": "The quest", "type": "text", "required": True},
        {"name": "objective", "label": "What finishing it means", "type": "textarea"}]},
}
STATUS_WORDS = {"active": "In play", "paused": "Paused", "ended": "Ended"}
PHASE_NOTE = ("Say what your character does; MIA narrates, and the dice decide anything contested. It's all fiction: "
              "nothing here touches your real life or your real XP.")


def _book(context):
    """The person's LivingWorldsBook, or None on a MIA without one."""
    return getattr(context, "living_worlds", None)


def _campaign_row(book, c) -> dict:
    """One campaign as its row: status in words, last played, who plays in it, open and finished quests."""
    quests = book.quests_in(c.campaign_id)
    return {"id": c.campaign_id, "name": c.name, "summary": c.summary, "status": c.status,
            "status_word": STATUS_WORDS.get(c.status, c.status), "last_played": (c.last_played or "")[:10],
            "versions": [v.name for v in book.versions_in(c.campaign_id)],
            "open": sum(q.status == "open" for q in quests), "done": sum(q.status == "done" for q in quests)}


def _story(book, c) -> list[dict]:
    """The campaign's story so far, oldest first, the last 30 turns as [{said, lines}]: what the player did, then the
    narration, what changed and what the dice refused (turn_lines), from the book's turn history
    (LivingWorldsBook.turns_in); [] when it can't be read."""
    from core.dungeon_master import TurnResult

    try:
        return [{"said": t.get("action", ""),
                 "lines": turn_lines(TurnResult(t.get("narration", ""), list(t.get("committed") or []),
                                                list(t.get("failed") or [])))}
                for t in book.turns_in(c.campaign_id, 30)]
    except Exception:  # noqa: BLE001 - a story that can't be read shows none rather than breaking the page
        return []


def _opened(book, c) -> dict:
    """One campaign opened: its world, its row, the character versions in it (attributes, skills, things carried),
    its quests (open first) and its story so far."""
    u = book.get_universe(c.universe_id)
    quests = sorted(book.quests_in(c.campaign_id), key=lambda q: (q.status != "open", q.created_at))
    return {**_campaign_row(book, c), "universe": {"id": c.universe_id, "name": u.name if u else "",
                                                   "genre": u.genre if u else ""},
            "players": [{"id": v.version_id, "name": v.name, "origin": v.origin, "background": v.background,
                         "attributes": [{"name": k, "value": val} for k, val in sorted(v.attributes.items())],
                         "skills": list(v.skills), "inventory": list(v.inventory)} for v in book.versions_in(c.campaign_id)],
            "quests": [{"id": q.quest_id, "name": q.name, "objective": q.objective, "status": q.status,
                        "by": "MIA" if q.assigned_by == "dm" else "You", "done_at": (q.completed_at or "")[:10]}
                       for q in quests],
            "story": _story(book, c)}


def screen(context, campaign_id: str = "") -> dict:
    """Living Worlds: the worlds and their campaigns, the character and where they live, one campaign opened."""
    book = _book(context)
    if book is None:
        return {"available": False}
    worlds = [{"id": u.universe_id, "name": u.name, "genre": u.genre, "premise": u.premise, "rules": u.rules,
               "campaigns": [_campaign_row(book, c) for c in sorted(book.campaigns_in(u.universe_id),
                                                                     key=lambda c: c.last_played or "", reverse=True)]}
              for u in book.universes]
    character = book.characters[0] if book.characters else None
    chosen = book.get_campaign(campaign_id) if campaign_id else None
    if chosen is None and book.campaigns:
        live = [c for c in book.campaigns if c.status != "ended"] or book.campaigns
        chosen = max(live, key=lambda c: c.last_played or c.created_at or "")
    return {
        "available": True,
        "worlds": worlds,
        "character": {"id": character.character_id, "name": character.name, "note": character.note,
                      "versions": [{"name": v.name, "world": (book.get_universe(v.universe_id).name
                                                              if book.get_universe(v.universe_id) else "")}
                                   for v in book.versions_of(character.character_id)]} if character else None,
        "campaign": _opened(book, chosen) if chosen is not None else None,
        "forms": FORMS,
        "phase_note": PHASE_NOTE,
    }


# ------------------------------------------------------------------ actions

def _need_book(context):
    """The worlds store, or ActionError on a MIA without one."""
    book = _book(context)
    if book is None:
        raise ActionError("Living Worlds isn't set up on this MIA.")
    return book


def _text(params, name: str, limit: int, what: str = "") -> str:
    """A text param tidied to its limit; ActionError with `what` when it's required and empty."""
    value = str(params.get(name) or "").strip()[:limit]
    if what and not value:
        raise ActionError(what)
    return value


def _need(getter, value, what: str):
    """The record a getter finds for the id, or ActionError naming what's missing."""
    found = getter(str(value or ""))
    if found is None:
        raise ActionError(f"That {what} isn't one of yours.")
    return found


def _describe_universe(context, params) -> str:
    """The approval sentence for `world.universe_add`."""
    _need_book(context)
    return f"Make the world {_text(params, 'name', 60, 'What is the world called?')}"


def _universe(context, params) -> str:
    """Does `world.universe_add`."""
    _describe_universe(context, params)
    u = _need_book(context).create_universe(_text(params, "name", 60), _text(params, "genre", 40),
                                            _text(params, "premise", 400), _text(params, "rules", 600))
    return f"{u.name} exists now. Start a campaign in it."


def _describe_campaign(context, params) -> str:
    """The approval sentence for `world.campaign_add`."""
    book = _need_book(context)
    u = _need(book.get_universe, params.get("universe_id"), "world")
    return f"Begin the campaign {_text(params, 'name', 60, 'What is the campaign called?')} in {u.name}"


def _campaign(context, params) -> str:
    """Does `world.campaign_add`."""
    _describe_campaign(context, params)
    c = _need_book(context).create_campaign(str(params["universe_id"]), _text(params, "name", 60),
                                            _text(params, "summary", 600))
    return f"{c.name} has begun."


def _describe_character(context, params) -> str:
    """The approval sentence for `world.character_add` (one central character; their versions live in each world)."""
    book = _need_book(context)
    if book.characters:
        raise ActionError(f"You already have {book.characters[0].name}; give them a version in another world instead.")
    return f"Make your character {_text(params, 'name', 60, 'What is your character called?')}"


def _character(context, params) -> str:
    """Does `world.character_add`."""
    _describe_character(context, params)
    c = _need_book(context).create_character(_text(params, "name", 60), _text(params, "note", 400))
    return f"{c.name} is yours. Give them a version in a campaign."


def _describe_version(context, params) -> str:
    """The approval sentence for `world.version_add`: the character in one campaign's world."""
    book = _need_book(context)
    if not book.characters:
        raise ActionError("Make your character first.")
    c = _need(book.get_campaign, params.get("campaign_id"), "campaign")
    character = book.characters[0]
    if any(v.character_id == character.character_id for v in book.versions_in(c.campaign_id)):
        raise ActionError(f"{character.name} already plays in {c.name}.")
    return f"Bring {character.name} into {c.name} as {_text(params, 'name', 60, 'What are they called there?')}"


def _version(context, params) -> str:
    """Does `world.version_add`."""
    _describe_version(context, params)
    book = _need_book(context)
    c = book.get_campaign(str(params["campaign_id"]))
    v = book.create_version(book.characters[0].character_id, c.universe_id, c.campaign_id, _text(params, "name", 60),
                            _text(params, "origin", 120), _text(params, "background", 800))
    return f"{v.name} steps into {c.name}."


def _describe_quest(context, params) -> str:
    """The approval sentence for `world.quest_add` (a quest the player sets themselves)."""
    book = _need_book(context)
    c = _need(book.get_campaign, params.get("campaign_id"), "campaign")
    return f"Set the quest {_text(params, 'name', 80, 'What is the quest?')} in {c.name}"


def _quest(context, params) -> str:
    """Does `world.quest_add`."""
    _describe_quest(context, params)
    q = _need_book(context).assign_quest(str(params["campaign_id"]), _text(params, "name", 80),
                                         _text(params, "objective", 400), assigned_by="player")
    return f"{q.name} is set. Fiction only: it earns no real XP."


def _describe_quest_done(context, params) -> str:
    """The approval sentence for `world.quest_done`."""
    q = _need(_need_book(context).get_quest, params.get("quest_id"), "quest")
    if q.status == "done":
        raise ActionError(f"{q.name} is already finished.")
    return f"Finish the quest {q.name}"


def _quest_done(context, params) -> str:
    """Does `world.quest_done`."""
    _describe_quest_done(context, params)
    q = _need_book(context).complete_quest(str(params["quest_id"]))
    return f"{q.name}: finished."


def _describe_status(context, params) -> str:
    """The approval sentence for `world.campaign_status` (paused, back in play, or ended)."""
    from core.living_worlds import CAMPAIGN_STATUSES

    c = _need(_need_book(context).get_campaign, params.get("campaign_id"), "campaign")
    status = str(params.get("status") or "")
    if status not in CAMPAIGN_STATUSES:
        raise ActionError("A campaign is in play, paused or ended.")
    if status == c.status:
        raise ActionError(f"{c.name} is already {STATUS_WORDS[status].lower()}.")
    return {"active": "Pick {} back up", "paused": "Pause {}", "ended": "End {}"}[status].format(c.name)


def _status(context, params) -> str:
    """Does `world.campaign_status` (resuming marks it played now)."""
    _describe_status(context, params)
    book = _need_book(context)
    status = str(params["status"])
    if status == "active":
        book.resume(str(params["campaign_id"]))
    else:
        book.set_campaign_status(str(params["campaign_id"]), status)
    c = book.get_campaign(str(params["campaign_id"]))
    return f"{c.name}: {STATUS_WORDS[status].lower()}."


def _turn_parts(context, params):
    """The campaign, the player's version in it and what they do, checked: ActionError when the campaign isn't in play,
    the character isn't in it, or nothing was said."""
    book = _need_book(context)
    c = _need(book.get_campaign, params.get("campaign_id"), "campaign")
    if c.status != "active":
        raise ActionError(f"{c.name} is {STATUS_WORDS.get(c.status, c.status).lower()}; pick it back up to play.")
    versions = book.versions_in(c.campaign_id)
    wanted = str(params.get("version_id") or "")
    version = next((v for v in versions if v.version_id == wanted), None) if wanted else (versions[0] if versions else None)
    if version is None:
        raise ActionError(f"Bring your character into {c.name} first.")
    return book, c, version, _text(params, "action", 500, "What do you do?")


def _describe_turn(context, params) -> str:
    """The approval sentence for `world.turn`."""
    _book_, c, version, action = _turn_parts(context, params)
    return f"{version.name}, in {c.name}: {action}"


def turn_lines(result) -> list[str]:
    """Pure logic. A played turn as lines: the narration (or why there's none), what changed, and what was tried but
    failed its roll."""
    lines = [result.narration or "MIA has no model running to narrate this turn, so nothing happened yet."]
    lines += list(result.committed)
    if result.failed:
        lines.append("Tried, but the dice said no: " + ", ".join(f.split(" (")[0].replace("_", " ") for f in result.failed))
    return lines


def _turn(context, params) -> str:
    """Does `world.turn`: one turn with MIA as the Dungeon Master (the model proposes, code validates and commits);
    returns the narration and what changed, one per line."""
    from core.dungeon_master import model_proposer, take_turn

    book, c, version, action = _turn_parts(context, params)
    try:
        result = take_turn(book, c.campaign_id, version.version_id, action, model_proposer(context))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return "\n".join(turn_lines(result))


WORLD_ACTIONS = {a.kind: a for a in (
    ActionType("world.universe_add", "Make a World", {"name": "its name", "genre": "optional", "premise": "optional",
                                                      "rules": "optional: tone and house rules"},
               _describe_universe, _universe, child_ok=True),
    ActionType("world.campaign_add", "Begin a Campaign", {"universe_id": "the world", "name": "its name",
                                                         "summary": "optional: where it starts"},
               _describe_campaign, _campaign, child_ok=True),
    ActionType("world.character_add", "Make Your Character", {"name": "their name", "note": "optional"},
               _describe_character, _character, child_ok=True),
    ActionType("world.version_add", "Bring Them In", {"campaign_id": "the campaign", "name": "their name there",
                                                     "origin": "optional", "background": "optional"},
               _describe_version, _version, child_ok=True),
    ActionType("world.quest_add", "Set a Quest", {"campaign_id": "the campaign", "name": "the quest",
                                                 "objective": "optional"}, _describe_quest, _quest, child_ok=True),
    ActionType("world.quest_done", "Finished", {"quest_id": "the quest"}, _describe_quest_done, _quest_done,
               child_ok=True),
    ActionType("world.campaign_status", "Status", {"campaign_id": "the campaign", "status": "active, paused or ended"},
               _describe_status, _status, child_ok=True),
    ActionType("world.turn", "Do It", {"campaign_id": "the campaign", "action": "what your character does",
                                       "version_id": "optional: which version of your character"},
               _describe_turn, _turn, child_ok=True),
)}
ACTION_TYPES.update(WORLD_ACTIONS)


def find_campaign(context, words: str):
    """The campaign the words name (by its name or its world's), most recently played first; None when nothing fits."""
    book = _book(context)
    said = " ".join(str(words or "").lower().split())
    if book is None:
        return None
    ordered = sorted(book.campaigns, key=lambda c: c.last_played or "", reverse=True)
    if not said:
        return ordered[0] if ordered else None
    for c in ordered:
        u = book.get_universe(c.universe_id)
        if said in c.name.lower() or c.name.lower() in said or (u and said in u.name.lower()):
            return c
    return None


def find_world(context, words: str):
    """The world the words name; None when nothing fits."""
    book = _book(context)
    said = " ".join(str(words or "").lower().split())
    if book is None or not said:
        return None
    return next((u for u in book.universes if said in u.name.lower() or u.name.lower() in said), None)
