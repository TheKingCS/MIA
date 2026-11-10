"""
tests.test_saga_actions
=========================

The moments kept for the Chronicles on the Chronicle page (core/saga_actions.py, 2026-11-09): listed newest first
with the marks they don't have yet, marked through saga.mark (only "series" approves one for the comic), refused for
an unknown moment or privacy, and shown on the Chronicle page's data.
"""

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.saga import SagaMoments
from core.saga_actions import kept_moments
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test world with two kept moments."""
    context = build_world(tmp_path, monkeypatch)
    context.saga_moments = SagaMoments(context, data_dir=context.my_dir)
    context.saga_moments.add("The first council meeting")
    context.saga_moments.add("The greenhouse's first fish")
    return context


def test_kept_moments_are_listed_newest_first_with_the_other_marks(world):
    """Both moments, newest first, private, each offering "for the series" and "never"."""
    kept = kept_moments(world)
    assert [m["summary"] for m in kept] == ["The greenhouse's first fish", "The first council meeting"]
    assert kept[0]["privacy_text"] == "private"
    assert [a["action"]["params"]["privacy"] for a in kept[0]["actions"]] == ["series", "never"]


def test_marking_one_for_the_series_approves_it_and_bad_marks_are_refused(world):
    """saga.mark for the series approves the moment; an unknown moment or privacy is refused."""
    mark = ACTION_TYPES["saga.mark"]
    first = world.saga_moments.moments[0]["id"]
    assert mark.describe(world, {"moment_id": first, "privacy": "series"}) == f"Mark {first} for the series"
    assert mark.execute(world, {"moment_id": first, "privacy": "series"}) == f"{first} is for the series."
    assert world.saga_moments.moments[0]["approved"] == "yes"
    with pytest.raises(ActionError):
        mark.describe(world, {"moment_id": "M-9999", "privacy": "never"})
    with pytest.raises(ActionError):
        mark.describe(world, {"moment_id": first, "privacy": "public"})


def test_the_chronicle_page_carries_the_kept_moments(world):
    """chronicle_page has kept_moments; without the store it's an empty list."""
    from core.chronicle import chronicle_page

    assert len(chronicle_page(world)["kept_moments"]) == 2
    world.saga_moments = None
    assert chronicle_page(world)["kept_moments"] == []
