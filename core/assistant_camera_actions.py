"""
core.assistant_camera_actions
===============================

The cameras by voice (DEC-0125, 2026-11-07): the Security screen (core/security_cams.py,
DEC-0033) had no tool, so "are the cameras working?" reached the network utilities that share its
area. Two tools, in their own area `cameras`:

- list_cameras: each camera by name and place, and whether its last picture failed (from what the
  screen last saw; it doesn't reach out to every camera to answer);
- save_camera_picture: keeps the picture a named camera shows now, through the screen's own Save
  Picture (`security.save_picture`), into Security's Pictures.

Logins never come into either: they stay in security_logins.json.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _book(context):
    """The cameras, or None where this MIA has none."""
    return getattr(context, "security", None)


def _action_list_cameras(context, arguments: dict) -> str:
    """Tool list_cameras: each camera with where it is, and the last problem with its picture, if any."""
    book = _book(context)
    if book is None:
        return "There are no cameras on this MIA."
    if not book.cameras:
        return "No cameras yet. Add one under Apps → Security (its brand and its address on your network)."
    lines = []
    for cam in book.cameras:
        problem = book.last_error.get(cam.camera_id, "")
        lines.append(f"{cam.name} ({cam.location}): " + (f"last time: {problem}" if problem else "no problems seen"))
    return "; ".join(lines) + ". Open Security to see them live."


def _action_save_camera_picture(context, arguments: dict) -> str:
    """Tool save_camera_picture: saves the named camera's picture now through security.save_picture."""
    from core.actions import ActionError

    book, actions = _book(context), getattr(context, "actions", None)
    if book is None or actions is None:
        return "There are no cameras on this MIA."
    wanted = " ".join(str(arguments.get("camera") or "").lower().split())
    found = [c for c in book.cameras if wanted and (wanted in c.name.lower() or wanted in c.location.lower())]
    if len(found) != 1:
        names = ", ".join(c.name for c in (found or book.cameras))
        return f"Which camera? {names}." if names else "No cameras yet. Add one under Apps → Security."
    try:
        done = actions.approve(context, actions.propose(context, "security.save_picture",
                                                        {"camera_id": found[0].camera_id}, proposed_by="mia").proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status != "executed":
        return done.result or f"I couldn't get a picture from {found[0].name}."
    return f"Saved what {found[0].name} shows now. It's in Security's Pictures."


def register_camera_actions(registry: AssistantActionRegistry) -> None:
    """Registers list_cameras and save_camera_picture (domain cameras)."""
    registry.register_domain_keywords("cameras", ("camera", "cameras"))
    registry.register(AssistantAction(
        name="list_cameras", domain="cameras",
        description="The user's security cameras: each one's name and place, and whether its picture had a problem.",
        parameters={"type": "object", "properties": {}},
        handler=_action_list_cameras,
        trigger_phrases=("my cameras", "the cameras", "are the cameras", "which cameras", "security cameras"),
    ))
    registry.register(AssistantAction(
        name="save_camera_picture", domain="cameras",
        description="Save a picture of what one of the user's security cameras shows right now.",
        parameters={"type": "object", "properties": {
            "camera": {"type": "string", "description": "The camera's name or place, e.g. driveway."},
        }, "required": ["camera"]},
        handler=_action_save_camera_picture,
        trigger_phrases=("picture from the", "snapshot from the", "save a picture from", "take a picture from"),
    ))
