"""
core.assistant_app_registry_actions
=====================================

MIA about her own apps, by voice (migration phase M2, DEC-0178; answers from `core/app_ecosystem.py`, never the
model's guess):
- "What apps do I have?" (`list_my_apps`).
- "What can Greenhouse do?", "what depends on Home?" (`describe_app`).
- "Which app can monitor energy?", "which app has add_watch?" (`which_app`).
- "Is anything wrong with my apps?" (`check_my_apps`): failing parts first, then overlaps and gaps, marked as
  suggestions.
- "What can you do on your own?" (`list_grants`) and "take back the Friday reset" (`take_back_grant`): her grants
  (DEC-0156, core/grants.py).
The Apps page shows the same (its "Her apps, checked" section).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _list(context, arguments: dict) -> str:
    """Tool list_my_apps: the inventory."""
    from core import app_ecosystem

    return app_ecosystem.inventory_sentence(app_ecosystem.registry())


def _describe(context, arguments: dict) -> str:
    """Tool describe_app: one app's parts, from its manifest, and whether it's working now (its status)."""
    from core import app_ecosystem

    app = str(arguments.get("app") or "").strip()
    if not app:
        return "Which app?"
    return app_ecosystem.details_sentence(app_ecosystem.registry(), app, context)


def _which(context, arguments: dict) -> str:
    """Tool which_app: the app behind a capability, or the best matches for what was asked."""
    from core import app_ecosystem

    what = str(arguments.get("what") or "").strip()
    if not what:
        return "Which app does what?"
    return app_ecosystem.which_sentence(app_ecosystem.registry(), context, what)


def _check(context, arguments: dict) -> str:
    """Tool check_my_apps: health, overlaps and gaps."""
    from core import app_ecosystem

    return app_ecosystem.check_sentence(app_ecosystem.registry(), context)


def _grants(context, arguments: dict) -> str:
    """Tool list_grants: what MIA may do on her own, each with how the person gave it."""
    from core import grants

    found = grants.standing(context)
    if not found:
        return ("Nothing yet. I ask before every change, until you teach me a skill and it runs cleanly with you, or "
                "you publish a workflow. Paying, sending and deleting always need your yes.")
    said = "; ".join(f"{g.name} ({'a skill' if g.kind == 'skill' else 'a workflow'}: {g.covers}; {g.how})" for g in found)
    return f"On my own I may run: {said}. Paying, sending and deleting always need your yes. You can take any of these back."


AUTOMATE = ("Here's what I can take off your plate: reminders that repeat (\"remind me every Monday to check the "
            "water filter\" goes on your calendar), household routines I count as you do them, a skill you teach me by "
            "showing me once (\"watch me: the Friday reset\", then \"that's it\"; after it runs cleanly with you, I can "
            "run it myself), a workflow you publish, and sensors on your bench builds that report to me. The daily "
            "checks run on their own and only speak up when something needs you.")


def _automate(context, arguments: dict) -> str:
    """Tool what_can_you_automate: what MIA can run for him and how each is started (`AUTOMATE`), then what she may
    already do on her own (`_grants`). Read only (live sweep, 2026-11-25: "what can you automate for me?" got a
    chatbot's list of answering questions and writing)."""
    return f"{AUTOMATE} Right now: {_grants(context, {})}"


def _take_back(context, arguments: dict) -> str:
    """Tool take_back_grant: proposes `grant.take_back` for the one named."""
    from core.actions import run_as_tool

    return run_as_tool(context, "grant.take_back", {"grant": arguments.get("grant") or ""})


def register_app_registry_actions(registry: AssistantActionRegistry) -> None:
    """Registers list_my_apps, describe_app (which also answers "is the X app working?"), which_app, check_my_apps,
    list_grants and take_back_grant (domain app_registry, the Apps app's). There is no tool that gives a grant
    (core/grant_actions.py says why). describe_app's "depends on" is the app's ("what does the app depend on"), never
    a bare "what depends on", which is the links tool's.
    And what_can_you_automate."""
    registry.register(AssistantAction(
        name="list_grants", domain="app_registry",
        description=("What MIA may do on her own without asking: the skills she has learned and the workflows the "
                     "person published, each with what it covers and how it was given."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_grants,
        trigger_phrases=("what can you do on your own", "what may you do on your own", "what do you do without asking",
                         "what are you allowed to do", "your permissions", "what have i granted", "my grants",
                         "list grants", "what did i let you do"),
        subjects=("permissions", "grants"),
    ))
    registry.register(AssistantAction(
        name="what_can_you_automate", domain="app_registry",
        description="What MIA can automate for him (repeating reminders, routines, skills taught by showing her, "
                    "workflows, sensors) and how each is started, then what she may already do on her own.",
        parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                    "required": []},
        handler=_automate, prompt_arg="question",
        trigger_phrases=("what can you automate", "what could you automate", "what can be automated",
                         "what can i automate", "what do you do automatically", "automate for me",
                         "things you can automate", "help me automate"),
        subjects=("automate", "automation"),
    ))
    registry.register(AssistantAction(
        name="take_back_grant", domain="app_registry",
        description=("Take back something MIA may do on her own, by its name: a learned skill goes back to practising "
                     "with the person; a workflow is put away."),
        parameters={"type": "object", "properties": {
            "grant": {"type": "string", "description": "The skill's or workflow's name."}}, "required": ["grant"]},
        handler=_take_back, prompt_arg="grant",
        trigger_phrases=("take back", "stop doing that on your own", "don't do that on your own", "revoke",
                         "ask me first for"),
        subjects=("permission", "grant"),
    ))
    registry.register(AssistantAction(
        name="list_my_apps", domain="app_registry",
        description="Every app MIA has, by life area, and how many work on the PC, the phone, the glasses and by voice.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list,
        trigger_phrases=("what apps do i have", "what apps do you have", "list my apps", "list your apps",
                         "how many apps", "which apps do i have", "all my apps", "all your apps"),
        subjects=("apps",),
    ))
    registry.register(AssistantAction(
        name="describe_app", domain="app_registry",
        description=("One of MIA's apps from its record: what it's for, whether it's working right now and why not, "
                     "what it can do (its tools and actions), what it keeps, its background jobs, where it runs, what "
                     "it shares and what depends on it."),
        parameters={"type": "object", "properties": {
            "app": {"type": "string", "description": "The app's name, e.g. Greenhouse."}}, "required": ["app"]},
        handler=_describe, prompt_arg="app",
        trigger_phrases=("what can the app", "what does the app", "what depends on the app", "what does the app depend on", "tell me about the app",
                         "what's in the app", "what is in the app", "parts of the app", "app's parts",
                         "app working", "app broken", "is the app"),
        subjects=("app",),
    ))
    registry.register(AssistantAction(
        name="which_app", domain="app_registry",
        description=("Which of MIA's apps does something: the app that owns a tool or action named exactly, or the "
                     "apps whose descriptions and tools best match what was asked."),
        parameters={"type": "object", "properties": {
            "what": {"type": "string", "description": "What it should do, or a tool or action name."}},
            "required": ["what"]},
        handler=_which, prompt_arg="what",
        trigger_phrases=("which app", "what app can", "what app does", "which of your apps", "which of my apps",
                         "what app handles", "which app handles"),
        subjects=("app", "apps"),
    ))
    registry.register(AssistantAction(
        name="check_my_apps", domain="app_registry",
        description=("Checks MIA's apps: what's wrong now (a record that couldn't be loaded, a failing "
                     "background job), then tools in different apps that may overlap and what people asked for that "
                     "no app does, marked as suggestions."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_check,
        trigger_phrases=("check my apps", "check your apps", "anything wrong with my apps", "anything wrong with your apps",
                         "are my apps healthy", "are your apps healthy", "unhealthy apps", "duplicate apps",
                         "apps overlap", "app health"),
        subjects=("apps",),
    ))
