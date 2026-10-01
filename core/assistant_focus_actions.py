"""
core.assistant_focus_actions
===============================

Assistant tools for each person's Apps screen (core/focus_presets.py,
2026-10-01): "switch me to student mode", "hide the Lab", "show me the
Greenhouse again", "what's my focus?". Changes are the speaker's own.
"""

from __future__ import annotations

from typing import Optional

from core import focus_presets
from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _find_app(context, name: str):
    manager = getattr(context, "module_manager", None)
    wanted = (name or "").strip().lower().removeprefix("the ").removesuffix(" app").strip()
    if manager is None or not wanted:
        return None
    modules = manager.all()
    exact = [m for m in modules if wanted in (m.module_id.lower(), m.display_name.lower())]
    if exact:
        return exact[0]
    partial = [m for m in modules if wanted in m.display_name.lower()]
    return partial[0] if len(partial) == 1 else None


def _action_set_app_focus(context, arguments: dict) -> str:
    focus: Optional[focus_presets.Focus] = focus_presets.find_focus(str(arguments.get("focus") or ""))
    if focus is None:
        names = ", ".join(f.name for f in focus_presets.FOCUSES.values())
        return f"Which focus? I have {names}. Nothing gets locked either way."
    focus_presets.apply_focus(context, focus.focus_id)
    return (f"Done: your Apps screen is set for {focus.name} ({focus.description.rstrip('.').lower()}). "
            "Anything I tucked away still opens if you ask me or from the Modules screen.")


def _action_set_app_visibility(context, arguments: dict) -> str:
    module = _find_app(context, str(arguments.get("app") or ""))
    if module is None:
        return "Which app? Tell me its name as it shows on the Apps screen."
    visible = str(arguments.get("visible", "true")).lower() not in ("false", "no", "0", "hide")
    if not focus_presets.set_app_visible(context, module.module_id, visible):
        return f"{module.display_name} always stays on your Apps screen."
    if visible:
        return f"{module.display_name} is back on your Apps screen."
    return f"I tucked {module.display_name} away for you. It still opens from Modules, or just ask me."


def _action_get_app_focus(context, arguments: dict) -> str:
    focus_id, _featured, hidden = focus_presets.current(context)
    focus = focus_presets.FOCUSES.get(focus_id or "")
    text = f"Your Apps screen is set for {focus.name}." if focus else "Your Apps screen shows everything, in the usual order."
    manager = getattr(context, "module_manager", None)
    names = {m.module_id: m.display_name for m in manager.all()} if manager is not None else {}
    tucked = [names.get(h, h) for h in hidden]
    if tucked:
        text += f" Tucked away: {', '.join(tucked)}."
    return text + " Other focuses: " + ", ".join(f.name for f in focus_presets.FOCUSES.values() if f is not focus) + "."


def register_focus_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="set_app_focus", domain="apps",
        description=("Set which apps come first for the user: a focus of Personal, Home & Family, Homestead, "
                     "Business or Student. Never locks anything."),
        parameters={"type": "object", "properties": {
            "focus": {"type": "string", "description": "personal, home and family, homestead, business or student."},
        }, "required": ["focus"]},
        handler=_action_set_app_focus,
        trigger_phrases=("student mode", "business mode", "homestead mode", "family mode", "personal mode",
                         "set my focus", "change my focus", "switch my focus", "focus on school",
                         "set up my apps for", "set my apps for", "my apps up for", "apps for my"),
    ))
    registry.register(AssistantAction(
        name="set_app_visibility", domain="apps",
        description="Show or hide one app on the user's own Apps screen (it still opens from Modules or by asking).",
        parameters={"type": "object", "properties": {
            "app": {"type": "string", "description": "The app's name, e.g. 'The Lab', 'Greenhouse'."},
            "visible": {"type": "boolean", "description": "true to show it, false to hide it."},
        }, "required": ["app", "visible"]},
        handler=_action_set_app_visibility,
        trigger_phrases=("hide app", "unhide", "from my apps", "on my apps", "apps screen", "app screen",
                         "to my apps"),
    ))
    registry.register(AssistantAction(
        name="get_app_focus", domain="apps",
        description="What focus the user's Apps screen has and which apps are tucked away.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_app_focus,
        trigger_phrases=("what's my focus", "whats my focus", "what is my focus", "which apps are hidden",
                         "hidden apps", "what apps did you hide"),
    ))
