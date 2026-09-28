"""
core.assistant_inbox_actions
===============================

Assistant tools for the document inbox (core/inbox_manager.py): what's
waiting, "file it" (with MIA's proposal, or the owner's correction of
which tool or build it's for), and "throw that one out". Filing by voice
adds every maintenance step MIA found in a manual unless the owner says
"without the tasks"; the Inbox screen lets them tick steps one by one.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.inbox_manager import describe_detail_updates

_S = {"type": "string"}


def _inbox(context: AppContext):
    return getattr(context, "inbox", None)


def _asset_name(context: AppContext, asset_id: str) -> str:
    maintenance = getattr(context, "maintenance", None)
    asset = maintenance.get_asset(asset_id) if maintenance and asset_id else None
    return asset.name if asset else ""


def _describe(context: AppContext, item) -> str:
    text = item.label
    name = _asset_name(context, item.asset_id)
    if name:
        text += f" for the {name}"
    if item.schedule:
        text += f", with {len(item.schedule)} maintenance step{'s' if len(item.schedule) != 1 else ''}"
    news = describe_detail_updates(context.inbox.detail_proposals(item)) if name else ""
    if news:
        text += f" (it has the {name}'s {news})"
    if not item.readable:
        text += " (I couldn't read it)"
    return text


def _action_list_inbox(context: AppContext, arguments: dict) -> str:
    inbox = _inbox(context)
    if inbox is None:
        return "The inbox isn't available right now."
    pending = inbox.pending()
    if not pending:
        return "Your inbox is empty. Send me receipts and manuals from your phone, by email, or drop them in the inbox folder."
    parts = [_describe(context, item) for item in pending[:5]]
    more = f", and {len(pending) - 5} more" if len(pending) > 5 else ""
    return f"{len(pending)} waiting in your inbox: " + "; ".join(parts) + more + ". Say \"file it\" or open Inbox."


def _find_by_name(options, words: str):
    lowered = words.lower().strip()
    if not lowered:
        return None
    exact = [o for o in options if o.name.lower() == lowered]
    if exact:
        return exact[0]
    hits = [o for o in options if lowered in o.name.lower() or o.name.lower() in lowered]
    return hits[0] if len(hits) == 1 else None


def _action_file_inbox_item(context: AppContext, arguments: dict) -> str:
    inbox = _inbox(context)
    if inbox is None:
        return "The inbox isn't available right now."
    if not inbox.pending():
        return "There's nothing waiting in your inbox."
    item = inbox.find_pending(str(arguments.get("item") or ""))
    if item is None:
        return "I couldn't tell which one. " + _action_list_inbox(context, {})

    asset_id = project_id = None
    for_words = str(arguments.get("for") or "").strip()
    if for_words:
        maintenance = getattr(context, "maintenance", None)
        projects = getattr(context, "projects", None)
        asset = _find_by_name(maintenance.all_assets(), for_words) if maintenance else None
        project = _find_by_name(projects.all_projects(), for_words) if projects and asset is None else None
        if asset is None and project is None:
            return f"I don't have anything called {for_words} to file it under."
        asset_id = asset.asset_id if asset else None
        project_id = project.project_id if project else None
    if not item.asset_id and asset_id is None and item.schedule:
        return f"Which tool or machine is the {item.label} for?"

    amount = arguments.get("amount")
    try:
        amount = float(amount) if amount not in (None, "") else None
    except (TypeError, ValueError):
        amount = None
    with_tasks = str(arguments.get("with_tasks", "yes")).lower() not in ("no", "false", "0")
    indexes = list(range(len(item.schedule))) if with_tasks else []
    try:
        result = inbox.file_item(item.item_id, asset_id=asset_id, project_id=project_id, amount=amount, schedule_indexes=indexes)
    except ValueError as exc:
        return str(exc)
    return f"{item.label}: {result}"


def _action_dismiss_inbox_item(context: AppContext, arguments: dict) -> str:
    inbox = _inbox(context)
    if inbox is None or not inbox.pending():
        return "There's nothing waiting in your inbox."
    item = inbox.find_pending(str(arguments.get("item") or ""))
    if item is None:
        return "I couldn't tell which one. " + _action_list_inbox(context, {})
    inbox.dismiss(item.item_id)
    return f"Took the {item.label} out of your inbox without filing it."


def register_inbox_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="list_inbox", domain="inbox",
        description="List the documents waiting in the user's inbox (receipts, manuals, warranties sent to MIA).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_inbox,
        trigger_phrases=("my inbox", "in the inbox", "new documents", "documents waiting", "anything to file"),
    ))
    registry.register(AssistantAction(
        name="file_inbox_item", domain="inbox",
        description="File a document from the inbox: a receipt becomes an expense, a manual goes on the tool's page "
                    "and its maintenance steps become tasks.",
        parameters={"type": "object", "properties": {
            "item": {**_S, "description": "Which document, in the user's words, e.g. 'the Lowe's receipt'. Empty for the oldest."},
            "for": {**_S, "description": "The tool, machine or build it belongs to, if the user said."},
            "amount": {"type": "number", "description": "The amount, if the user corrected it."},
            "with_tasks": {**_S, "description": "'no' to file a manual without adding its maintenance tasks."},
        }, "required": []},
        handler=_action_file_inbox_item,
        trigger_phrases=("file it", "file the", "file that", "file this", "file my"),
    ))
    registry.register(AssistantAction(
        name="dismiss_inbox_item", domain="inbox",
        description="Remove a document from the inbox without filing it.",
        parameters={"type": "object", "properties": {"item": {**_S, "description": "Which document."}}, "required": []},
        handler=_action_dismiss_inbox_item,
        trigger_phrases=("dismiss the", "don't file", "do not file", "out of the inbox", "out of my inbox"),
    ))
