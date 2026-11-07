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


def _remote(params) -> str:
    """The home computer's id for a "pc-…" camera, or ""."""
    from core.security_cams import REMOTE

    cid = str(params.get("camera_id") or "")
    return cid[len(REMOTE):] if cid.startswith(REMOTE) else ""


def _camera(context, params):
    """The camera the params name, or ActionError when it isn't set up anymore."""
    cam = _need(context, "security").get(str(params.get("camera_id") or ""))
    if cam is None:
        raise ActionError("That camera isn't set up anymore.")
    return cam


def _save(context, params) -> str:
    """Does `security.save_picture` once approved, and says what happened. A camera on the home computer is named by its remote name; the camera's own
    refusals come back as ActionError.
    """
    from core.security_cams import CameraError

    rid = _remote(params)
    name = _need(context, "security").remote_names.get(rid, "the camera") if rid else _camera(context, params).name
    try:
        context.security.save_picture(str(params.get("camera_id")))
    except CameraError as problem:
        raise ActionError(str(problem)) from None
    return f"Saved a picture from {name}."


def _picture(context, params) -> str:
    """The saved picture's name, once the camera store confirms it's one of its pictures; ActionError otherwise."""
    from core.security_cams import CameraError

    name = str(params.get("name") or "")
    try:
        _need(context, "security").picture_path(name)
    except CameraError as problem:
        raise ActionError(str(problem)) from None
    return name


def _delete_picture(context, params) -> str:
    """Does `security.picture_delete` once approved, and says what happened. It can't be brought back."""
    context.security.delete_picture(_picture(context, params))
    return "Picture deleted."


def _describe_remove(context, params) -> str:
    """The sentence the approval card shows for `camera.remove` (Propose); raises ActionError when it can't be done. It says the camera itself isn't touched, and when it's on the home computer."""
    rid = _remote(params)
    if rid:
        name = _need(context, "security").remote_names.get(rid, "this camera")
        return f"Remove the camera {name} from MIA on the home computer (the camera itself isn't touched)"
    return f"Remove the camera {_camera(context, params).name} from MIA (the camera itself isn't touched)"


def _remove(context, params) -> str:
    """Does `camera.remove` once approved, and says what happened. A camera on the home computer is removed there, through the home link."""
    rid = _remote(params)
    if rid:
        from core.home_link import HomeLinkError, home_call

        try:
            return home_call(context, f"/api/security/camera/{rid}", method="DELETE", timeout=10).get("message") or "Removed."
        except HomeLinkError as problem:
            raise ActionError(str(problem)) from None
    context.security.remove(_camera(context, params).camera_id)
    return "Removed."


def _describe_save(context, params) -> str:
    """The sentence the approval card shows for `security.save_picture` (Propose); raises ActionError when it can't be done. For a camera on the home computer, the picture is kept on this phone."""
    rid = _remote(params)
    if rid:
        return f"Save the picture {_need(context, 'security').remote_names.get(rid, 'the camera')} shows now (kept on this phone)"
    return f"Save the picture {_camera(context, params).name} shows now"


def _register() -> None:
    """Puts the camera action kinds in ACTION_TYPES: camera.remove, security.save_picture and
    security.picture_delete.
    """
    for kind in (
        ActionType("camera.remove", "Remove", {"camera_id": "the camera"}, _describe_remove, _remove),
        ActionType("security.save_picture", "Save Picture", {"camera_id": "the camera"}, _describe_save, _save),
        ActionType("security.picture_delete", "Delete", {"name": "the picture"},
                   lambda c, p: (_picture(c, p), "Delete this picture (it can't be brought back)")[1], _delete_picture),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
