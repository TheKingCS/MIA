"""What a project touches (core/project_ripple.py, Zac 2026-11-24): "I'm planning to build a greenhouse" reaches the
project picture, whose sheet carries the build's materials and cost against the workshop's stock, his money and
freedom date, and each area a greenhouse touches (growing, water, power, time, goals, research), every one from his
records or said as missing, with general guidance marked as such. And it never takes a question that's another plan's or a tool's (debts, a
bill, the weather, the build's materials or price), reads the kind from the project itself, and files nothing. A
Planner draft's "What It Touches" is the same picture at the draft's own size, and a confirmed build's materials
still to buy reach the money answers (stock counted once across builds), one used on something else is said while
it's short, his own page speaks to him, the model is asked to go area by area, and a question about one he already
has ("what's due in the greenhouse?") never takes the picture, even by meaning."""

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


def test_a_greenhouse_picture_carries_every_area_it_touches_from_records_or_said_missing_and_the_homesteads_power(life):
    sheet = qp.gather(life, qp.PLAN_BY_NAME["project picture"], "I'm planning to build a greenhouse?", TODAY)
    text = sheet.as_text()
    assert "Hoop-house greenhouse" in text  # the Library's plan, at its own size
    assert "Still to buy" in text
    assert "needs water at it" in text and "[estimate, general guidance]" in text
    assert "essentials" in text  # the homestead's power picture, never this computer's battery
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


def test_a_confirmed_builds_materials_still_to_buy_reach_the_afford_answer_and_drafts_dont(life, tmp_path):
    from core import project_plans
    from core.project_plans import ProjectPlanBook

    life.project_plans = ProjectPlanBook(life, data_dir=tmp_path / "pp")
    draft = project_plans.draft(life, {"kind": "build", "shelf_plan": "builtin:hoop-house"})
    assert pr.still_to_buy(life) == []  # a draft is nothing decided
    draft.status = "confirmed"
    life.project_plans.put(draft)
    rows = pr.still_to_buy(life)
    assert [r["title"] for r in rows] == [draft.title] and rows[0]["items"] > 0
    sheet = qp.gather(life, qp.PLAN_BY_NAME["afford"], "can I afford a $900 welder?", TODAY)
    assert "Confirmed builds still to buy: " + draft.title in sheet.as_text()


def test_a_confirmed_builds_material_used_elsewhere_is_said_while_short_and_the_first_look_only_remembers(life, tmp_path):
    from core import project_plans
    from core.material_manager import MaterialManager
    from core.project_plans import ProjectPlanBook

    life.project_plans = ProjectPlanBook(life, data_dir=tmp_path / "pp")
    life.materials = MaterialManager(life, data_dir=tmp_path / "mat")
    boards = life.materials.add_material("2x6 x 8 ft", unit="board", quantity_on_hand=6)
    plan = project_plans.draft(life, {"kind": "build", "shelf_plan": "builtin:raised-bed"})
    plan.status = "confirmed"
    life.project_plans.put(plan)
    assert pr.gone_short(life, TODAY) == []  # the first look remembers the boards are covered
    assert pr.gone_short(life, TODAY) == []  # nothing changed
    life.materials.update_material(boards.material_id, quantity_on_hand=2)
    found = pr.gone_short(life, TODAY)
    assert len(found) == 1 and "2x6 x 8 ft (2 on hand for it, it needs 6)" in found[0]["text"]
    again = pr.gone_short(life, TODAY)  # still short: still said (the gate says each key once), never used up
    assert [f["key"] for f in again] == [found[0]["key"]]
    life.materials.update_material(boards.material_id, quantity_on_hand=6)
    assert pr.gone_short(life, TODAY) == []  # bought back: nothing to say


def test_stock_one_confirmed_build_counts_on_isnt_counted_again_for_the_next(life, tmp_path):
    from core import project_plans
    from core.material_manager import MaterialManager
    from core.project_plans import ProjectPlanBook

    life.project_plans = ProjectPlanBook(life, data_dir=tmp_path / "pp")
    life.materials = MaterialManager(life, data_dir=tmp_path / "mat")
    life.materials.add_material("2x6 x 8 ft", unit="board", unit_cost=10, quantity_on_hand=6)
    for _ in range(2):
        plan = project_plans.draft(life, {"kind": "build", "shelf_plan": "builtin:raised-bed"})
        plan.status = "confirmed"
        life.project_plans.put(plan)
    first, second = pr.still_to_buy(life)
    assert first["items"] < second["items"]  # the first has the six boards; the second buys its own
    assert second["cost"] >= 60


def test_his_own_page_speaks_to_him_not_about_him():
    assert pr.to_you("His gauge logged 1 inches of rain over the last seven days.").startswith("Your gauge logged")
    assert "until you say yours" in pr.to_you("14 materials, at its own size until he says his.")


def test_the_picture_asks_the_model_to_go_area_by_area_and_a_failed_tool_or_odd_record_never_spoils_it(life, monkeypatch):
    from types import SimpleNamespace

    messages, sheet = qp.request(life, None, "I'm planning to build a greenhouse?", TODAY)
    assert messages[0]["content"].rstrip().endswith(qp.HOW["project picture"])  # last, where a small model reads it
    life.projects = SimpleNamespace(all_projects=lambda: [SimpleNamespace(name="Greenhouse")])  # no status: odd
    monkeypatch.setattr(life.assistant_actions, "execute",
                        lambda c, tool, args: "Something on my side broke while I was doing that, sorry.")
    text = qp.gather(life, qp.PLAN_BY_NAME["project picture"], "I'm planning to build a greenhouse?", TODAY).as_text()
    assert "Hoop-house greenhouse" in text and "broke" not in text


@pytest.mark.parametrize("said", ["What's due in the greenhouse?", "How's the greenhouse doing?",
                                  "What's the greenhouse temperature?", "What needs doing in the garden?"])
def test_a_question_about_one_he_already_has_never_takes_the_picture_even_by_meaning(life, monkeypatch, said):
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: ("project picture", 0.9))  # as close as meaning gets
    found = qp.match(life, said)
    assert found is None or found.name != "project picture", said
