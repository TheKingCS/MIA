"""
core.assistant_creation_actions
=================================

What MIA has made for you, by voice (DEC-0091, DEC-0125: every action both ways). Until now a screen of your own
could only be asked for, published, rolled back or removed on the web (core/creation_actions.py,
`POST /api/creations/make`): "make me a screen to track my seed orders", "what have you made for me?", "publish my
seed tracker", "take the seed tracker out of my sidebar" now work by voice too, and so do its records: "add to my
seed bank: variety Cherokee Purple, count 20" (`records.add`), "what's in my seed bank?".

Each tool runs the same code the screens do: making a draft goes through core/creation_maker.make (a draft changes
no data and is private until published), and publishing, going back a version and removing are the `creation.*`
action kinds, checked then run, so "undo that" takes them back.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def _creations(context):
    """The person's creations store, or None."""
    return getattr(context, "creations", None)


def _title(creation: dict) -> str:
    """A creation's title (its own, else its latest version's spec's, else its id)."""
    versions = creation.get("versions") or []
    spec = (versions[-1].get("spec") if versions else None) or {}
    return str(creation.get("title") or spec.get("title") or creation.get("id") or "a screen")


def _find(context, words: str):
    """The creation the words name (by its title), or None."""
    store = _creations(context)
    if store is None:
        return None
    said = " ".join(str(words or "").lower().split())
    found = [c for c in store.items if said and (said in _title(c).lower() or _title(c).lower() in said)]
    return found[0] if found else None


def _list(context, arguments: dict) -> str:
    """Tool list_creations: the screens MIA has made for the person, published (in the sidebar) or still drafts, with
    their version."""
    store = _creations(context)
    if store is None:
        return "I can't see what I've made for you here."
    items = [c for c in store.items if c.get("status") != "retired"]
    if not items:
        return "I haven't made you any screens yet. Tell me what you want to keep track of, and I'll draft one."
    lines = [f"{_title(c)} ({'in your sidebar' if c.get('status') == 'published' else 'a draft'}, version "
             f"{len(c.get('versions') or [])})" for c in items]
    return "What I've made for you: " + "; ".join(lines) + "."


def _make(context, arguments: dict) -> str:
    """Tool make_creation: drafts a screen for what the person wants to keep track of (core/creation_maker.make): a
    private draft that changes no data, to look at and publish."""
    from core.child_accounts import is_child
    from core.creation_maker import MakerError, make

    need = str(arguments.get("need") or "").strip()
    try:
        made = make(context, need, child=is_child(context))
    except MakerError as problem:
        return str(problem)
    return (f"I drafted \"{_title(made)}\" for you. It's private until you publish it: say \"publish "
            f"{_title(made).lower()}\" or open it from Made by MIA to look first.")


def _values(fields: list, said: str) -> dict:
    """Pure logic. Field values from plain words: "variety Cherokee Purple, count 20" or "variety: Cherokee Purple;
    count: 20", each piece matched to a field by its label or name (the longest that starts it)."""
    out = {}
    for piece in [p.strip() for chunk in str(said or "").split(";") for p in chunk.split(",")]:
        low = piece.lower()
        match = None
        for f in fields:
            for name in (str(f.get("label") or ""), str(f.get("name") or "").replace("_", " ")):
                if name and low.startswith(name.lower()) and (match is None or len(name) > len(match[1])):
                    match = (f, name)
        if match is not None:
            value = piece[len(match[1]):].lstrip(" :=-").strip()
            if value:
                out[match[0]["name"]] = value
    return out


def _published(context, words: str):
    """The published creation the words name and its record set, or (None, why)."""
    from core.actions import ActionError
    from core.creation_actions import _published_set

    found = _find(context, words)
    if found is None:
        return None, "I don't see a screen of yours by that name. Ask me what I've made for you."
    try:
        return _published_set(context, {"creation_id": found["id"]}), ""
    except ActionError as problem:
        return None, str(problem)


def _add_record(context, arguments: dict) -> str:
    """Tool add_to_creation: adds a record to one of the person's published screens from plain words, through
    `records.add` (checked, then run; undoable)."""
    pair, why = _published(context, arguments.get("name"))
    if pair is None:
        return why
    found, rs = pair
    values = _values(rs["fields"], arguments.get("values"))
    if not values:
        return (f"Which fields? {found['title']} has " + ", ".join(f["label"] for f in rs["fields"]) +
                ": say them like \"" + (rs["fields"][0]["label"].lower() if rs["fields"] else "name") + " ...\".")
    return _run(context, "records.add", {"creation_id": found["id"], "values": values})


def _read_records(context, arguments: dict) -> str:
    """Tool read_creation: what's in one of the person's published screens, newest first (up to ten)."""
    pair, why = _published(context, arguments.get("name"))
    if pair is None:
        return why
    found, rs = pair
    records = list(reversed(rs.get("records") or []))
    if not records:
        return f"{found['title']} is empty so far."
    labels = {f["name"]: f["label"] for f in rs["fields"]}
    lines = ["; ".join(f"{labels.get(k, k)} {v}" for k, v in r["values"].items() if v not in (None, ""))
             for r in records[:10]]
    return f"{found['title']} ({len(records)}): " + " | ".join(lines) + "."


def _change(kind: str):
    """A tool handler that runs one creation action (publish, rollback, retire) on the creation the words name."""
    def handle(context, arguments: dict) -> str:
        """Finds the creation by its title and runs the action, in its own words when it can't."""
        found = _find(context, arguments.get("name"))
        if found is None:
            return "I don't see a screen of yours by that name. Ask me what I've made for you."
        return _run(context, kind, {"creation_id": found["id"]})
    return handle


def register_creation_actions(registry: AssistantActionRegistry) -> None:
    """Registers the creation tools and the words that bring them into a turn."""
    registry.register(AssistantAction(
        name="list_creations", domain="creations",
        description="List the screens MIA has made for the person, in their sidebar or still drafts.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list,
        trigger_phrases=("what have you made for me", "my screens", "what screens have you made", "made by mia"),
    ))
    registry.register(AssistantAction(
        name="make_creation", domain="creations",
        description=("Draft a new screen for the person to keep track of something in their own way (a private draft "
                     "that changes no data)."),
        parameters={"type": "object", "properties": {
            "need": {"type": "string", "description": "What they want to keep track of, in their words."}},
            "required": ["need"]},
        handler=_make,
        trigger_phrases=("make me a screen", "make me a tracker", "build me a page", "make a screen to track",
                         "make me a dashboard"),
    ))
    for name, kind, what, words in (
            ("publish_creation", "creation.publish", "Publish a screen MIA made into the person's sidebar, by its title.",
             ("publish my", "put it in my sidebar", "add it to my sidebar")),
            ("rollback_creation", "creation.rollback", "Take a screen MIA made back to its version before, by its title.",
             ("go back a version", "roll back my", "undo the change to my screen")),
            ("retire_creation", "creation.retire", "Take a screen MIA made out of the person's sidebar, by its title.",
             ("take it out of my sidebar", "remove my screen", "retire my"))):
        registry.register(AssistantAction(
            name=name, domain="creations", description=what,
            parameters={"type": "object", "properties": {
                "name": {"type": "string", "description": "The screen's title, as the person said it."}},
                "required": ["name"]},
            handler=_change(kind), trigger_phrases=words,
        ))
    registry.register(AssistantAction(
        name="add_to_creation", domain="creations",
        description="Add an entry to one of the person's own screens (a tracker MIA made), by the screen's title.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The screen's title, as the person said it."},
            "values": {"type": "string", "description": "The entry in their words, field then value, comma-separated."}},
            "required": ["name", "values"]},
        handler=_add_record,
        trigger_phrases=("add to my", "log in my", "put in my tracker"),
    ))
    registry.register(AssistantAction(
        name="read_creation", domain="creations",
        description="What's in one of the person's own screens (a tracker MIA made), by its title.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The screen's title, as the person said it."}},
            "required": ["name"]},
        handler=_read_records,
        trigger_phrases=("what's in my", "show me my tracker", "read my tracker"),
    ))
    registry.register_domain_keywords("creations", ("screen", "screens", "tracker", "made by mia", "sidebar"))
