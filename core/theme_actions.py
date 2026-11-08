"""
core.theme_actions
====================

What the Theme Studio changes (DEC-0136, web/studio.html), through the
action system so each change is approved and undoable:

- `theme.save`: a theme of your own from the Studio's choices (accent,
  background, panels, text, lines, corners, font, material, the room's
  levels and palette) on top of the theme it started from; a new one, or
  one of yours updated; optionally used straight away. The tokens are built
  in core (core/themes.build_theme), which refuses an accent that would read
  as a warning colour and text that would be hard to read.
- `theme.delete`: one of your own themes; if it's the one in use, MIA goes
  back to Stark.
- `theme.import`: a theme from a file (the Studio's export, or someone
  else's): read through the same checks as everything else (only allowed
  tokens, nothing that can break out of CSS, no warning-coloured accent,
  readable text), rebuilt from its choices, kept as one of yours.

`export(theme)` (pure) is the file the Studio downloads: the theme's
choices, its tokens and room, and a format mark, so another MIA can read it.

Built-in themes can't be changed or deleted (save a copy instead). Your
themes are yours alone (person_settings `display.custom_themes`).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _base(context, params) -> dict:
    """The theme the params start from (a built-in or one of theirs; Stark when none is named)."""
    from core.themes import DEFAULT_THEME, all_themes

    themes = all_themes(context)
    return themes.get(str(params.get("base") or ""), themes[DEFAULT_THEME])


def _plan(context, params) -> tuple[dict, bool, bool]:
    """(the theme that would be saved, whether it's new, whether it'll be used); ActionError when it can't be."""
    from core.themes import MAX_CUSTOM, THEMES, build_theme, custom_themes, own_id

    if not isinstance(params.get("choices"), dict):
        raise ActionError("Which colours and settings? (choices)")
    name = " ".join(str(params.get("name") or "").split())[:40]
    if not name:
        raise ActionError("What should this theme be called?")
    mine = {t["id"]: t for t in custom_themes(context)}
    theme_id = str(params.get("id") or "")
    if theme_id in THEMES:
        raise ActionError("The built-in themes stay as they are. Save it under a new name instead.")
    new = theme_id not in mine
    if new:
        if len(mine) >= MAX_CUSTOM:
            raise ActionError(f"You have {MAX_CUSTOM} themes of your own. Delete one first.")
        if any(t["name"].lower() == name.lower() for t in mine.values()):
            raise ActionError(f"You already have a theme called {name}.")
        theme_id = own_id(name, set(mine))
    try:
        theme = build_theme(params["choices"], _base(context, params), theme_id, name)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return theme, new, bool(params.get("use"))


def _describe_save(context, params) -> str:
    """The sentence the approval card shows for `theme.save` (Propose); raises ActionError when it can't be done."""
    theme, new, use = _plan(context, params)
    return ("Save the new theme " if new else "Update your theme ") + theme["name"] + (" and use it" if use else "")


def _save(context, params) -> str:
    """Does `theme.save` once approved: the theme kept among theirs (replacing the one with its id), used if asked."""
    from core import person_settings
    from core.themes import CUSTOM_KEY, KEY

    theme, new, use = _plan(context, params)
    kept = [t for t in (person_settings.get(context, CUSTOM_KEY, []) or []) if isinstance(t, dict) and t.get("id") != theme["id"]]
    person_settings.put(context, CUSTOM_KEY, kept + [theme])
    if use:
        person_settings.put(context, KEY, theme["id"])
    context.events.publish("display.changed")
    return f"{theme['name']} is saved" + (" and in use." if use else ". Pick it in Settings, or say \"use " + theme["name"] + "\".")


def _own(context, params) -> dict:
    """The person's own theme the params name; ActionError for a built-in or one that isn't there."""
    from core.themes import THEMES, custom_themes

    theme_id = str(params.get("id") or "")
    if theme_id in THEMES:
        raise ActionError("The built-in themes can't be deleted.")
    found = next((t for t in custom_themes(context) if t["id"] == theme_id), None)
    if found is None:
        raise ActionError("That theme isn't one of yours.")
    return found


def _describe_delete(context, params) -> str:
    """The sentence the approval card shows for `theme.delete` (Propose); raises ActionError when it can't be done."""
    from core.themes import theme_of

    found = _own(context, params)
    return f"Delete your theme {found['name']}" + (" (MIA goes back to Stark)" if theme_of(context) == found["id"] else "")


def _delete(context, params) -> str:
    """Does `theme.delete` once approved: the theme removed from theirs, and Stark used if it was the one in use."""
    from core import person_settings
    from core.themes import CUSTOM_KEY, DEFAULT_THEME, KEY, theme_of

    found = _own(context, params)
    in_use = theme_of(context) == found["id"]
    person_settings.put(context, CUSTOM_KEY, [t for t in (person_settings.get(context, CUSTOM_KEY, []) or [])
                                              if not (isinstance(t, dict) and t.get("id") == found["id"])])
    if in_use:
        person_settings.put(context, KEY, DEFAULT_THEME)
    context.events.publish("display.changed")
    return f"Deleted {found['name']}." + (" Back to Stark." if in_use else "")


FORMAT = "mia-theme/1"
MAX_FILE = 20_000  # characters: a theme file is a few kilobytes


def export(theme: dict) -> dict:
    """Pure logic. A theme as the file the Studio downloads: its format mark, name, line, the theme it's built on,
    its Studio choices, and the tokens, material and room it makes (for a MIA without the Studio's arithmetic)."""
    from core.themes import choices_of

    return {"format": FORMAT, "name": theme.get("name", ""), "line": theme.get("line", ""), "id": theme.get("id", ""),
            "choices": choices_of(theme), "tokens": dict(theme.get("tokens") or {}),
            "material": theme.get("material", "solid"), "room": dict(theme.get("room") or {})}


def _imported(context, params) -> dict:
    """The theme a file holds, checked and rebuilt as one of this person's own (a new id and a name not yet taken);
    ActionError for a file that isn't a MIA theme or doesn't pass the checks."""
    import json

    from core.themes import MAX_CUSTOM, THEMES, as_data, build_theme, choices_of, clean_theme, custom_themes, own_id

    raw = params.get("file")
    if isinstance(raw, str):
        if len(raw) > MAX_FILE:
            raise ActionError("That file is too big to be a theme.")
        try:
            raw = json.loads(raw)
        except ValueError:
            raise ActionError("That file isn't a theme MIA can read.") from None
    if not isinstance(raw, dict) or raw.get("format") != FORMAT:
        raise ActionError("That file isn't a MIA theme.")
    mine = custom_themes(context)
    if len(mine) >= MAX_CUSTOM:
        raise ActionError(f"You have {MAX_CUSTOM} themes of your own. Delete one first.")
    name = " ".join(str(raw.get("name") or "Imported theme").split())[:40]
    taken = {t["name"].lower() for t in mine} | {t.name.lower() for t in THEMES.values()}
    base_name, n = name, 2
    while name.lower() in taken:
        name, n = f"{base_name} {n}", n + 1
    try:
        cleaned = clean_theme({**raw, "id": "imported", "name": name})
        picks = raw["choices"] if isinstance(raw.get("choices"), dict) else choices_of(cleaned)
        theme = build_theme(picks, cleaned, own_id(name, {t["id"] for t in mine}), name)
    except (ValueError, TypeError, KeyError) as problem:
        raise ActionError(f"MIA can't use that theme: {problem}") from None
    theme["line"] = str(raw.get("line") or "")[:160]
    return theme


def _describe_import(context, params) -> str:
    """The sentence the approval card shows for `theme.import` (Propose); raises ActionError when it can't be done."""
    return f"Import the theme {_imported(context, params)['name']}" + (" and use it" if params.get("use") else "")


def _import(context, params) -> str:
    """Does `theme.import` once approved: the file's theme kept among theirs, used if asked."""
    from core import person_settings
    from core.themes import CUSTOM_KEY, KEY

    theme = _imported(context, params)
    kept = [t for t in (person_settings.get(context, CUSTOM_KEY, []) or []) if isinstance(t, dict)]
    person_settings.put(context, CUSTOM_KEY, kept + [theme])
    if params.get("use"):
        person_settings.put(context, KEY, theme["id"])
    context.events.publish("display.changed")
    return f"Imported {theme['name']}." + (" It's in use." if params.get("use") else " It's in your themes.")


THEME_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("theme.save", "Save theme", {"name": "its name", "choices": "the Studio's choices",
                                            "base": "optional: the theme it started from", "id": "optional: yours, to update",
                                            "use": "optional: use it now"},
               _describe_save, _save, child_ok=True),
    ActionType("theme.delete", "Delete", {"id": "one of your themes"}, _describe_delete, _delete, child_ok=True),
    ActionType("theme.import", "Import", {"file": "the theme file (mia-theme/1)", "use": "optional: use it now"},
               _describe_import, _import, child_ok=True),
)}
ACTION_TYPES.update(THEME_ACTIONS)
