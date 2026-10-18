"""
core.security_actions
=======================

Security's changes (DEC-0033, core/security_cams.py) on the action
contract in core/actions.py: remove a camera (undoable), save the
picture a camera shows now, delete a saved picture. Adding or changing a
camera goes through `/api/security/camera` instead, so its password is
never in an action's record. Grown-ups only.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _camera(context, params):
    cam = _need(context, "security").get(str(params.get("camera_id") or ""))
    if cam is None:
        raise ActionError("That camera isn't set up anymore.")
    return cam


def _save(context, params) -> str:
    from core.security_cams import CameraError

    cam = _camera(context, params)
    try:
        context.security.save_picture(cam.camera_id)
    except CameraError as problem:
        raise ActionError(str(problem)) from None
    return f"Saved a picture from {cam.name}."


def _picture(context, params) -> str:
    from core.security_cams import CameraError

    name = str(params.get("name") or "")
    try:
        _need(context, "security").picture_path(name)
    except CameraError as problem:
        raise ActionError(str(problem)) from None
    return name


def _delete_picture(context, params) -> str:
    context.security.delete_picture(_picture(context, params))
    return "Picture deleted."


def _register() -> None:
    for kind in (
        ActionType("camera.remove", "Remove", {"camera_id": "the camera"},
                   lambda c, p: f"Remove the camera {_camera(c, p).name} from MIA (the camera itself isn't touched)",
                   lambda c, p: (c.security.remove(_camera(c, p).camera_id), "Removed.")[1]),
        ActionType("security.save_picture", "Save Picture", {"camera_id": "the camera"},
                   lambda c, p: f"Save the picture {_camera(c, p).name} shows now", _save),
        ActionType("security.picture_delete", "Delete", {"name": "the picture"},
                   lambda c, p: (_picture(c, p), "Delete this picture (it can't be brought back)")[1], _delete_picture),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
