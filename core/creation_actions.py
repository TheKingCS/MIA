"""
core.creation_actions
=======================

MIA's creations as changes a person approves (DEC-0091; core/actions.py's
Propose → Approve → Execute → Record → Undo):

- `creation.publish`: a draft (or a new version) into the person's sidebar.
  The spec is checked again first; the record set it shows is made now, in
  the household's or the person's own folder. "Undo that" takes it all back.
- `creation.rollback`: back to the version published before.
- `creation.retire`: out of the sidebar, kept.
- `records.add` / `records.remove`: a record in a creation's record set, from
  its form, the phone or the glasses.

Grown-ups only for now: Made by MIA isn't one of the children's apps (CHILD_APPS).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _creations(context):
    store = getattr(context, "creations", None)
    if store is None:
        raise ActionError("Creations aren't available here.")
    return store


def _child(context) -> bool:
    try:
        from core.child_accounts import is_child

        return is_child(context)
    except Exception:
        return False


def sets_for(context, owner: str):
    store = getattr(context, "record_sets" if owner == "household" else "my_record_sets", None)
    if store is None:
        raise ActionError("Record sets aren't available here.")
    return store


def _get(context, params) -> dict:
    from core.creations import CreationError

    try:
        return _creations(context).get(str(params.get("creation_id", "")))
    except CreationError as problem:
        raise ActionError(str(problem)) from None


def _describe_publish(context, params) -> str:
    found = _get(context, params)
    latest = found["versions"][-1]
    if latest["version"] == found["version"]:
        raise ActionError(f"{found['title']} is already published as it is.")
    where = "the household's records" if found["owner"] == "household" else "your own records"
    if latest["spec"].get("kind") == "workflow":
        from core.workflows import may

        return (f"{'Switch on' if not found['version'] else 'Update'} “{latest['spec']['title']}”, which may "
                + "; ".join(may(latest["spec"])))
    if latest["spec"].get("source"):
        from core.creation_sources import source_of

        if not found["version"]:
            return f"Add “{latest['spec']['title']}” to your apps, showing {source_of(latest['spec']).title.lower()} from your history"
    if found.get("pending_rows"):
        return f"Add “{latest['spec']['title']}” to your apps with the {len(found['pending_rows'])} rows from the file"
    if found["version"]:
        return f"Publish version {latest['version']} of “{latest['spec']['title']}” in place of version {found['version']}"
    return f"Add “{latest['spec']['title']}” to your apps, keeping its records with {where}"


def _publish(context, params) -> str:
    from core.creation_spec import check
    from core.record_sets import RecordError

    found = _get(context, params)
    latest = found["versions"][-1]
    if latest["spec"].get("kind") == "workflow":  # its standing approval is exactly what it lists (DEC-0092)
        from core.workflows import check as check_workflow

        problems = check_workflow(latest["spec"], context, child=_child(context))
        if problems:
            raise ActionError("It doesn't pass its checks: " + " ".join(problems[:3]))
        _creations(context).mark_published(found["id"], latest["version"], "")
        return f"{latest['spec']['title']} is on."
    problems = check(latest["spec"], child=_child(context))
    if problems:
        raise ActionError("It doesn't pass its checks: " + " ".join(problems[:3]))
    set_id = found["set_id"]
    if not set_id and not latest["spec"].get("source"):  # a source's records are already MIA's: nothing to make
        rs = latest["spec"]["record_set"]
        try:
            set_id = sets_for(context, found["owner"]).create(rs["name"], rs["fields"], about=latest["spec"].get("about", ""))["id"]
        except RecordError as problem:
            raise ActionError(str(problem)) from None
    _creations(context).mark_published(found["id"], latest["version"], set_id)
    rows = _creations(context).take_rows(found["id"])  # an imported file's rows, in the same undoable step
    if rows:
        store = sets_for(context, found["owner"])
        for values in rows:
            try:
                store.add(set_id, values)
            except RecordError:
                continue
        return f"{latest['spec']['title']} is in your apps, with {len(rows)} records from the file."
    return f"{latest['spec']['title']} is in your apps."


def _describe_rollback(context, params) -> str:
    found = _get(context, params)
    if len(found["published_versions"]) < 2:
        raise ActionError("There's no earlier version to go back to.")
    return f"Put “{found['title']}” back to version {found['published_versions'][-2]}"


def _rollback(context, params) -> str:
    found = _creations(context).roll_back(_get(context, params)["id"])
    return f"{found['title']} is back to version {found['version']}."


def _describe_retire(context, params) -> str:
    return f"Take “{_get(context, params)['title']}” out of your apps (its records are kept)"


def _retire(context, params) -> str:
    return f"{_creations(context).retire(_get(context, params)['id'])['title']} is out of your apps."


def _published_set(context, params) -> tuple[dict, dict]:
    found = _get(context, params)
    shown = _creations(context).shown(found["id"])["spec"]
    if shown.get("source"):
        from core.creation_sources import source_of

        raise ActionError(f"{found['title']} shows your history; add to it in {source_of(shown).app}.")
    if found["status"] != "published" or not found["set_id"]:
        raise ActionError(f"{found['title']} isn't published yet.")
    from core.record_sets import RecordError

    try:
        return found, sets_for(context, found["owner"]).get(found["set_id"])
    except RecordError as problem:
        raise ActionError(str(problem)) from None


def _describe_add(context, params) -> str:
    from core.record_sets import RecordError, coerce

    found, rs = _published_set(context, params)
    values = params.get("values") or {}
    try:
        shown = [f"{f['label']} {coerce(f, values.get(f['name']))}" for f in rs["fields"]
                 if coerce(f, values.get(f["name"])) not in (None, "")]
    except RecordError as problem:
        raise ActionError(str(problem)) from None
    if not shown:
        raise ActionError("Fill in at least one field.")
    return f"Add to {found['title']}: " + ", ".join(shown[:4])


def _add(context, params) -> str:
    from core.record_sets import RecordError

    found, rs = _published_set(context, params)
    try:
        sets_for(context, found["owner"]).add(rs["id"], params.get("values") or {})
    except RecordError as problem:
        raise ActionError(str(problem)) from None
    return f"Added to {found['title']}."


def _describe_remove(context, params) -> str:
    found, rs = _published_set(context, params)
    if not any(r["id"] == params.get("record_id") for r in rs["records"]):
        raise ActionError("That record isn't there.")
    return f"Remove that record from {found['title']}"


def _remove(context, params) -> str:
    found, rs = _published_set(context, params)
    sets_for(context, found["owner"]).remove(rs["id"], str(params.get("record_id", "")))
    return f"Removed from {found['title']}."


CREATION_ACTIONS = {a.kind: a for a in (
    ActionType("creation.publish", "Publish", {"creation_id": "the creation"}, _describe_publish, _publish),
    ActionType("creation.rollback", "Go back a version", {"creation_id": "the creation"}, _describe_rollback, _rollback),
    ActionType("creation.retire", "Remove", {"creation_id": "the creation"}, _describe_retire, _retire),
    ActionType("records.add", "Add", {"creation_id": "the creation", "values": "field name -> value"},
               _describe_add, _add),
    ActionType("records.remove", "Remove", {"creation_id": "the creation", "record_id": "the record"},
               _describe_remove, _remove),
)}
ACTION_TYPES.update(CREATION_ACTIONS)
