"""What a project touches (core/project_ripple.py, Zac 2026-11-24): "I'm planning to build a greenhouse" reaches the
project picture, whose sheet carries the build's materials and cost against the workshop's stock, his money and
freedom date, and each area a greenhouse touches (growing, water, power, time, goals, research), every one from his
records or said as missing, with general guidance marked as such."""

from datetime import date

import pytest

import core.meaning as meaning
from core import project_ripple as pr
from core import question_plans as qp
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 11, 24)


@pytest.fixture
def life(shop, monkeypatch, tmp_path):  # noqa: F811
    """The shop's world with the desktop's tools, the Library's plans, and no embedding model."""
    from core.plan_library import PlanLibrary
    from tests.assistant_registry import build_desktop_registry

    shop.assistant_actions = build_desktop_registry()
    shop.plans = PlanLibrary(shop, data_dir=tmp_path / "plans", files_dir=tmp_path / "plan_files")
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: None)
    return shop


@pytest.mark.parametrize("said, kind, what", [
    ("I'm planning to build a greenhouse next spring.", "greenhouse", "greenhouse"),
    ("thinking about putting up a hoop house out back", "greenhouse", "hoop house"),
    ("I want to build a chicken coop this spring", "chicken coop", "chicken coop"),
    ("we're going to start a big garden next year", "garden", "garden"),
    ("I'm planning to add solar panels", "power", "solar panels"),
])
def test_the_project_and_its_kind_are_read_from_the_words(said, kind, what):
    assert pr.kind_of(said).name == kind
    assert pr.planned(said) == what


def test_a_project_of_no_known_kind_still_names_itself():
    assert pr.kind_of("I'm planning to build a sauna") is None
    assert pr.planned("I'm planning to build a sauna") == "sauna"


def test_a_greenhouse_picture_carries_every_area_it_touches_from_records_or_said_missing(life):
    sheet = qp.gather(life, qp.PLAN_BY_NAME["project picture"], "I'm planning to build a greenhouse?", TODAY)
    text = sheet.as_text()
    assert "Hoop-house greenhouse" in text  # the Library's plan, at its own size
    assert "Still to buy" in text
    assert "needs water at it" in text and "[estimate, general guidance]" in text
    assert "Power isn't set up here" in text  # a part not here is said, never a failure
    assert "broke" not in text
    assert "let's plan the greenhouse" in text  # nothing made: the offer to draft


def test_planning_a_greenhouse_reaches_the_picture_and_afford_stays_afford(life):
    assert qp.match(life, "I'm planning to build a greenhouse?").name == "project picture"
    assert qp.match(life, "What would building a shed mean for everything else?").name == "project picture"
    assert qp.match(life, "Can I afford a chicken coop?").name == "afford"


def test_the_picture_tool_names_the_project_and_plans_nothing(life):
    said = life.assistant_actions.execute(life, "project_picture", {"project": "a hoop house"})
    assert "hoop house" in said and "Hoop-house greenhouse" in said
    assert life.project_plans is None or not life.project_plans.listed()
