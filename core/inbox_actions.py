"""
core.inbox_actions
====================

The Inbox screen's changes (Zac, 2026-10-16), on the action contract in
core/actions.py:

- `inbox.file`: file an item the way MIA proposed, or with the person's
  corrections (which tool or build it's for, the amount, the category,
  which maintenance steps to add, which details to fill in). Through
  core/inbox_manager.file_item(): a receipt becomes a Budget expense, a
  manual goes on the tool's page, and so on.
- `inbox.dismiss`: not something to file.
- `inbox.note`: send MIA a few words (a link, a reminder, something to
  keep), saved into the inbox like any other document.

Nothing here sends anything anywhere.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _item(context, params):
    """The inbox item the params name, if it's still waiting; ActionError otherwise."""
    item = _need(context, "inbox").get_item(str(params.get("item_id") or ""))
    if item is None or item.status != "pending":
        raise ActionError("That isn't waiting in the inbox anymore.")
    return item


def _indexes(raw) -> list[int]:
    """Pure logic. "0, 2" or [0, 2] -> [0, 2]."""
    if raw in (None, ""):
        return []
    bits = raw if isinstance(raw, list) else str(raw).split(",")
    out = []
    for bit in bits:
        try:
            out.append(int(str(bit).strip()))
        except ValueError:
            continue
    return out


def _fields(raw):
    """Which detail fields to keep, from a list or comma-separated text; None keeps the ones MIA ticked."""
    if raw is None:
        return None  # the defaults MIA ticked
    bits = raw if isinstance(raw, list) else [b.strip() for b in str(raw).split(",")]
    return [b for b in bits if b]


def _choices(context, params) -> dict:
    """What filing an item does, from the params: the asset it's for (which must exist), the project, the amount (a
    number over 0), the category, the schedule rows to add, the detail fields, and which of a receipt's effects to do
    (stock the pantry, mark a service done, add materials; not given: the ticked ones). A receipt or invoice needs a
    total.
    """
    item = _item(context, params)
    out: dict = {}
    if "asset_id" in params:
        asset_id = str(params.get("asset_id") or "")
        if asset_id and _need(context, "maintenance").get_asset(asset_id) is None:
            raise ActionError("That tool or item isn't there anymore.")
        out["asset_id"] = asset_id
    if "project_id" in params:
        out["project_id"] = str(params.get("project_id") or "")
    if params.get("amount") not in (None, ""):
        try:
            out["amount"] = float(str(params["amount"]).replace(",", "").lstrip("$").strip())
        except ValueError:
            raise ActionError("The amount has to be a number.") from None
        if out["amount"] <= 0:
            raise ActionError("The amount has to be more than 0.")
    if params.get("category"):
        out["category"] = str(params["category"])
    out["schedule_indexes"] = _indexes(params.get("schedule"))
    if "effects" in params:  # what the receipt says happened: which of its effects to do (none given: the ticked)
        out["effect_indexes"] = _indexes(params.get("effects"))
    out["detail_fields"] = _fields(params.get("details"))
    if item.doc_type in ("receipt", "invoice") and not (out.get("amount") or item.amount):
        raise ActionError("What's the total? Add the amount, then file it.")
    return out


def _describe_file(context, params) -> str:
    """The sentence the approval card shows for `inbox.file` (Propose); raises ActionError when it can't be done. It lists what filing will do: log the amount in Money, put it on an asset's
    page, add maintenance tasks, what the receipt says happened (up to six, then how many more), or just keep it
    filed.
    """
    from core.region import money

    item = _item(context, params)
    c = _choices(context, params)
    maintenance = getattr(context, "maintenance", None)
    asset_id = c.get("asset_id", item.asset_id)
    asset = maintenance.get_asset(asset_id) if maintenance is not None and asset_id else None
    bits = []
    if item.doc_type in ("receipt", "invoice"):
        bits.append(f"log {money(c.get('amount') or item.amount)} in Money" + (f" for the {asset.name}" if asset else ""))
    if asset is not None and item.doc_type not in ("receipt", "invoice"):
        bits.append(f"put it on the {asset.name}'s page")
    if c["schedule_indexes"]:
        n = len(c["schedule_indexes"])
        bits.append(f"add {n} maintenance task{'s' if n != 1 else ''}")
    chosen = c.get("effect_indexes")
    effects = [e for i, e in enumerate(item.effects) if (e.get("on") if chosen is None else i in chosen)]
    if effects:
        bits.append("; ".join(e["label"][:1].lower() + e["label"][1:] for e in effects[:6])
                    + (f"; and {len(effects) - 6} more" if len(effects) > 6 else ""))
    return f"File {item.label}: " + (", ".join(bits) if bits else "keep it with your filed documents")


def _file(context, params) -> str:
    """Does `inbox.file` once approved, and says what happened. The inbox store's own refusals come back as ActionError."""
    item = _item(context, params)
    c = _choices(context, params)
    try:
        return context.inbox.file_item(item.item_id, **c)
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _describe_dismiss(context, params) -> str:
    """The sentence the approval card shows for `inbox.dismiss` (Propose); raises ActionError when it can't be done."""
    return f"Dismiss {_item(context, params).label} (it stays in the inbox's history)"


def _dismiss(context, params) -> str:
    """Does `inbox.dismiss` once approved, and says what happened. The item stays in the inbox's history."""
    item = _item(context, params)
    context.inbox.dismiss(item.item_id)
    return "Dismissed."


def _note(params) -> tuple[str, str]:
    """The note's title and text from the params: the text is required (up to 100,000 characters), and the title is
    given or its first six words.
    """
    text = str(params.get("text") or "").strip()
    if not text:
        raise ActionError("Write something to send.")
    if len(text) > 100_000:
        raise ActionError("That's too long for a note. Send it as a file.")
    title = str(params.get("title") or "").strip() or " ".join(text.split()[:6])
    return title, text


def _describe_note(context, params) -> str:
    """The sentence the approval card shows for `inbox.note` (Propose); raises ActionError when it can't be done."""
    _need(context, "inbox")
    title, _ = _note(params)
    return f"Send MIA the note \"{title}\""


def _send_note(context, params) -> str:
    """Does `inbox.note` once approved, and says what happened. The note becomes a .txt file in the inbox (its title first when one was given), and the
    inbox is scanned at once so it's there now.
    """
    import re

    title, text = _note(params)
    name = re.sub(r"[^\w\- ]", "", title)[:60].strip() or "note"
    context.inbox.receive_file(f"{name}.txt", (f"{title}\n\n{text}" if params.get("title") else text).encode("utf-8"), source="note")
    context.inbox.scan()  # take it in now, not on the next check
    return "Sent. It's in your inbox."


for _a in (
    ActionType("inbox.file", "File It", {"item_id": "the inbox item", "asset_id": "optional: what it's for",
                                         "project_id": "optional: the build", "amount": "optional: the total",
                                         "category": "optional", "schedule": "optional: which steps, e.g. 0,2",
                                         "effects": "optional: which of the receipt's effects, e.g. 0,2 (none: the ticked)",
                                         "details": "optional: which details to fill in"}, _describe_file, _file),
    ActionType("inbox.dismiss", "Dismiss", {"item_id": "the inbox item"}, _describe_dismiss, _dismiss),
    ActionType("inbox.note", "Send", {"text": "what to send", "title": "optional"}, _describe_note, _send_note),
):
    ACTION_TYPES[_a.kind] = _a
