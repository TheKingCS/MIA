"""
tests.test_camera_voice
=========================

The Security cameras by voice (DEC-0125, core/assistant_camera_actions.py):
which cameras there are and whether each last worked, and saving a
camera's picture through the screen's own Save Picture.
"""

from types import SimpleNamespace

from core import assistant_camera_actions as cams


def _book():
    """Two cameras, the driveway's last picture having failed."""
    return SimpleNamespace(
        cameras=[SimpleNamespace(camera_id="c1", name="Driveway", location="Outside"),
                 SimpleNamespace(camera_id="c2", name="Coop", location="Yard")],
        last_error={"c1": "couldn't reach it"})


def test_the_cameras_are_listed_with_any_last_problem():
    """Each camera by name and place; a failed picture is said, never a login."""
    said = cams._action_list_cameras(SimpleNamespace(security=_book()), {})
    assert "Driveway (Outside): last time: couldn't reach it" in said and "Coop (Yard): no problems seen" in said


class _Actions:
    """Keeps the proposal and runs it."""

    def __init__(self):
        """Nothing yet."""
        self.proposed = []

    def propose(self, context, kind, params, proposed_by):
        """Keeps it."""
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p")

    def approve(self, context, proposal_id):
        """Done."""
        return SimpleNamespace(status="executed", result="Saved.")


def test_a_picture_is_saved_through_the_screen_s_save_picture():
    """"Take a picture from the coop camera": security.save_picture for that camera."""
    actions = _Actions()
    said = cams._action_save_camera_picture(SimpleNamespace(security=_book(), actions=actions), {"camera": "coop"})
    assert actions.proposed == [("security.save_picture", {"camera_id": "c2"})] and "Coop" in said


def test_an_unclear_camera_is_asked_about_and_nothing_is_saved():
    """No name: she asks which."""
    actions = _Actions()
    said = cams._action_save_camera_picture(SimpleNamespace(security=_book(), actions=actions), {"camera": ""})
    assert said == "Which camera? Driveway, Coop." and not actions.proposed
