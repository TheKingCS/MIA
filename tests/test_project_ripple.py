"""What a project touches (core/project_ripple.py, Zac 2026-11-24): "I'm planning to build a greenhouse" reaches the
project picture, whose sheet carries the build's materials and cost against the workshop's stock, his money and
freedom date, and each area a greenhouse touches (growing, water, power, time, goals, research), every one from his
records or said as missing, with general guidance marked as such. And it never takes a question that's another plan's or a tool's (debts, a
bill, the weather, the build's materials or price), reads the kind from the project itself, and files nothing. A
Planner draft's "What It Touches" is the same picture at the draft's own size."""

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


@pytest.mark.parametrize("said, kind", [
    ("I'm planning to build a shed next to the chicken coop", "shed"),
    ("I want to pour a slab for the greenhouse? planning to build a slab", "slab"),
    ("planning to build a deck to the shed", "deck"),
])
def test_the_kind_is_the_projects_own_not_a_thing_it_sits_by(said, kind):
    assert pr.kind_of(said).name == kind


def test_the_project_named_is_the_thing_built_never_what_follows_it():
    assert pr.kind_of("I'm planning to build a sauna") is None
    assert pr.planned("I'm planning to build a sauna") == "sauna"
    assert pr.planned("I'm planning to build the kids a fort") == "fort"
    assert pr.planned("should I build a greenhouse or a cold room?") == "greenhouse"
    assert pr.planned("how would adding a deck affect the rest of my budget?") == "deck"


def test_a_record_counts_as_started_only_when_its_name_holds_the_whole_project():
    assert pr._same_words("Hoop-house greenhouse", "hoop house")
    assert not pr._same_words("Chicken feed", "chicken coop")
    assert not pr._same_words("Power washing", "solar power")


def test_a_project_with_no_library_plan_still_gets_its_money_and_files_no_projection(life, monkeypatch):
    from core import calibration

    filed = []
    monkeypatch.setattr(calibration, "project", lambda *a, **k: filed.append(a))
    sheet = qp.gather(life, qp.PLAN_BY_NAME["project picture"], "I'm planning to add solar panels?", TODAY)
    assert "This month so far" in sheet.as_text() and not filed


def test_a_greenhouse_picture_carries_every_area_it_touches_from_records_or_said_missing(life):
    sheet = qp.gather(life, qp.PLAN_BY_NAME["project picture"], "I'm planning to build a greenhouse?", TODAY)
    text = sheet.as_text()
    assert "Hoop-house greenhouse" in text  # the Library's plan, at its own size
    assert "Still to buy" in text
    assert "needs water at it" in text and "[estimate, general guidance]" in text
    assert "Power isn't set up here" in text  # a part not here is said, never a failure
    assert "broke" not in text
    assert "let's plan the greenhouse" in text  # nothing made: the offer to draft


def test_planning_a_greenhouse_reaches_the_picture_by_words_and_afford_stays_afford(life):
    assert qp.match(life, "I'm planning to build a greenhouse?").name == "project picture"
    assert qp.match(life, "What would building a shed mean for everything else?").name == "project picture"
    assert qp.match(life, "Can I afford a chicken coop?").name == "afford"
    assert qp.match(life, "What would a greenhouse take?").name == "project picture"  # its own example, by words
    assert qp.match(life, "what would a rain barrel change?").name == "project picture"
    assert qp.match(life, "I'm planning to build a 10 by 12 shed?").name == "project picture"


@pytest.mark.parametrize("said", [
    "how would that affect my debts?", "what will it take to pay off my truck loan?", "I want to add a bill?",
    "what will the weather take?", "I'm planning to start a workout?", "how will the frost affect my tomatoes?",
    "what would it take to save $5000?", "I want to set up a budget?", "I want to start learning guitar?",
    "I want to build a picnic table, how much should I charge?", "how will skipping the gym affect my goals?",
    "I want to build a 10 by 12 shed, what materials do I need?",
    "when should I start my seeds in the garden?", "is it time to start tomatoes in the greenhouse?",
    "should I add more hens to my flock?", "what should I add to the garden this week?",
    "I want to start a garden journal?",
])
def test_the_picture_never_takes_another_plans_or_tools_question(life, said):
    found = qp.match(life, said)
    assert found is None or found.name != "project picture", said


def test_the_picture_tool_names_the_project_and_plans_nothing(life):
    said = life.assistant_actions.execute(life, "project_picture", {"project": "a hoop house"})
    assert "hoop house" in said and "Hoop-house greenhouse" in said
    assert life.project_plans is None or not life.project_plans.listed()


def test_a_drafts_what_it_touches_is_the_same_picture_at_its_own_size_and_plans_nothing(life, tmp_path):
    from core import project_plans
    from core.project_plans import ProjectPlanBook

    life.project_plans = ProjectPlanBook(life, data_dir=tmp_path / "pp")
    plan = project_plans.draft(life, {"kind": "build", "shelf_plan": "builtin:hoop-house", "sizes": {"width_ft": 20}})
    lines = pr.for_plan(life, plan.plan_id, TODAY)
    text = " ".join(l["text"] for l in lines)
    assert "width 20 ft" in text and "needs water at it" in text
    assert {l["kind"] for l in lines} <= {"fact", "calculation", "estimate", "missing"}
    assert [p.plan_id for p in life.project_plans.listed()] == [plan.plan_id]  # still only the draft
    assert pr.for_plan(life, "no-such-plan") == []
