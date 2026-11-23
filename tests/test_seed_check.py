"""
tests.test_seed_check
=======================

Seeds against the plan (core/seed_check.py): the crops his confirmed garden plans start in the next month, checked
against the seeds he logged (pantry or inventory), said in the garden's weekly message when any have none logged.
"""

from datetime import date
from types import SimpleNamespace

from core import garden_week, seed_check


def _ctx(seeds=(), crops=("tomato", "pepper")):
    plan = SimpleNamespace(kind="garden", status="confirmed", last_frost="April 20", first_frost="",
                           crops=[{"crop": c} for c in crops])
    return SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: [plan]),
                           kitchen=SimpleNamespace(all_pantry_items=lambda: [SimpleNamespace(name=s) for s in seeds]),
                           inventory=None)


def test_crops_starting_soon_are_checked_against_the_seeds_logged():
    # peppers start indoors Feb 23, 2027 (8 weeks before April 20); tomatoes Mar 2
    found = seed_check.check(_ctx(seeds=["Tomato seeds, Cherokee Purple"]), date(2027, 2, 10))
    assert [(f["crop"], f["have"]) for f in found] == [("Peppers", False), ("Tomatoes", True)]
    said = seed_check.words(found)
    assert said.startswith("No seeds logged for peppers (starts Feb 23)") and "tomatoes" not in said


def test_nothing_is_said_when_every_crop_has_seeds_or_nothing_starts_soon():
    assert seed_check.words(seed_check.check(_ctx(seeds=["tomato seeds", "pepper seeds"]), date(2027, 2, 10))) == ""
    assert seed_check.check(_ctx(), date(2027, 6, 1)) == []


def test_the_gardens_week_carries_the_missing_seeds():
    said = garden_week.say(_ctx(), date(2027, 2, 10))
    assert "No seeds logged for peppers" in said
