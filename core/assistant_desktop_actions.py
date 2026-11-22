"""
core.assistant_desktop_actions
================================

MIA OS's own desktop by voice (FW-11, DEC-0125: every feature by voice and on a screen): "open the display settings"
opens KDE's System Settings at that page (REQ-DSK-023), and "open Krita" opens one of the computer's Linux apps
(REQ-DSK-007), both through core/linux_apps.py. Neither changes a record; both happen on the computer itself.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _open_setting(context, arguments: dict) -> str:
    """Tool open_system_setting: the matching page of the computer's own System Settings."""
    from core.linux_apps import SYSTEM_SETTINGS, open_setting, setting_for

    key = setting_for(str(arguments.get("setting", "")))
    if key is None:
        return "I can open these in the computer's settings: " + ", ".join(v[0] for v in SYSTEM_SETTINGS.values()) + "."
    try:
        return f"Opened {open_setting(key)} in the computer's settings."
    except (ValueError, RuntimeError) as problem:
        return str(problem)


def _open_app(context, arguments: dict) -> str:
    """Tool open_linux_app: one of the computer's Linux apps, by its name."""
    from core.linux_apps import entries, launch

    wanted = str(arguments.get("name", "")).strip().lower()
    apps = entries()
    if not apps:
        return "There are no Linux apps here: that's on MIA OS."
    found = next((a for a in apps if a["name"].lower() == wanted), None) or next(
        (a for a in apps if wanted and wanted in a["name"].lower()), None)
    if found is None:
        return f"I don't see {arguments.get('name', 'that')} among the computer's apps."
    try:
        return f"Opened {launch(found['id'])}."
    except (ValueError, RuntimeError) as problem:
        return str(problem)


def register_desktop_actions(registry) -> None:
    """Registers open_system_setting and open_linux_app."""
    registry.register(AssistantAction(
        name="open_system_setting", domain="apps",
        description="Open a page of the computer's own System Settings: display, network, sound, bluetooth, users, "
                    "power, time, keyboard, mouse, printers, accessibility, language, updates.",
        parameters={"type": "object", "properties": {"setting": {"type": "string",
                    "description": "Which setting, in the person's words (e.g. 'display', 'wifi')."}},
                    "required": ["setting"]},
        handler=_open_setting,
        trigger_phrases=("display settings", "network settings", "sound settings", "system settings", "bluetooth",
                         "wifi settings", "printer settings", "keyboard settings"),
    ))
    registry.register(AssistantAction(
        name="open_linux_app", domain="apps",
        description="Open one of the computer's installed Linux apps (not MIA's own apps) by its name.",
        parameters={"type": "object", "properties": {"name": {"type": "string", "description": "The app's name."}},
                    "required": ["name"]},
        handler=_open_app,
        trigger_phrases=("open the app", "launch", "start the program"),
    ))
