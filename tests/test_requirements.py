"""
tests.test_requirements
=========================

What each project needs (Procurement P1, DEC-0172; core/requirements.py, core/requirement_actions.py): a plan's
materials become a new project's needs with the plan's quantities; what's on hand in the workshop and the inventory
is marked off (enough is owned, some is partial); the person adds, changes, ticks off and removes needs through the
actions, with their checks; a line ordered or got isn't re-marked by a check; open needs become relevance anchors and
so MIA's own watches; and the page and the voice tools say the same.
"""

from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.requirements import RequirementBook, progress


def _material(name, qty):
    """A workshop material with this much on hand."""
    return SimpleNamespace(name=name, quantity_on_hand=qty, unit_cost=0.0)


@pytest.fixture
def context(tmp_path):
    """Projects (a greenhouse in progress, a finished shed), workshop materials, an inventory and the needs store."""
    projects = [SimpleNamespace(project_id="p1", name="Greenhouse", description="", status="Active"),
                SimpleNamespace(project_id="p2", name="Shed", description="", status="Complete")]
    ctx = SimpleNamespace(
        projects=SimpleNamespace(all_projects=lambda: projects),
        materials=SimpleNamespace(all_materials=lambda: [_material("2x4 stud 8 ft", 10), _material("deck screws", 1)]),
        inventory=SimpleNamespace(all_items=lambda: [SimpleNamespace(name="Ventilation fan", quantity=1)]))
    ctx.requirements = RequirementBook(ctx, data_dir=tmp_path)
    return ctx


def test_a_plans_materials_become_the_projects_needs_and_whats_on_hand_is_marked_off(context):
    book = context.requirements
    added = book.from_materials("p1", {"items": [{"name": "2x4 stud 8 ft", "qty": 12, "unit": "pc"},
                                                 {"name": "deck screws", "qty": 1, "unit": "box"},
                                                 {"name": "polycarbonate panel", "qty": 8, "unit": "sheet"}]},
                                plan_id="builtin:greenhouse")
    assert [r.item for r in added] == ["2x4 stud 8 ft", "deck screws", "polycarbonate panel"]
    assert all(r.how == "computed" and r.origin == "plan:builtin:greenhouse" for r in added)
    book.refresh_owned(context)
    status = {r.item: (r.status, r.have) for r in book.for_project("p1")}
    assert status == {"2x4 stud 8 ft": ("partial", 10.0), "deck screws": ("owned", 1.0),
                      "polycarbonate panel": ("needed", 0.0)}
    assert progress(book.for_project("p1")) == {"lines": 3, "open": 2, "done": 1, "ordered": 0, "ceiling": 0}
    reloaded = RequirementBook(context, data_dir=book.data_dir)
    assert len(reloaded.items) == 3 and reloaded.items[0].checked


def test_the_person_adds_changes_ticks_off_and_removes_needs_through_the_actions(context):
    run = lambda kind, **p: (ACTION_TYPES[kind].describe(context, p), ACTION_TYPES[kind].execute(context, p))  # noqa: E731
    said, done = run("requirement.add", project="greenhouse", item="ventilation fan", quantity="4", max_price="40",
                     condition="used")
    assert said.startswith("Greenhouse needs 4 ventilation fan, up to") and "You have 1 on hand." in done
    with pytest.raises(ActionError):
        ACTION_TYPES["requirement.add"].describe(context, {"project": "nowhere", "item": "x"})
    with pytest.raises(ActionError):
        ACTION_TYPES["requirement.add"].describe(context, {"project": "greenhouse", "item": "x", "condition": "shiny"})
    run("requirement.update", project="greenhouse", item="ventilation fan", status="ordered")
    line = context.requirements.find("p1", "ventilation fan")
    assert line.status == "ordered" and line.max_price == 40.0 and line.condition == "used"
    context.requirements.refresh_owned(context)
    assert context.requirements.get(line.requirement_id).status == "ordered"  # a check never undoes "ordered"
    run("requirement.got", requirement_id=line.requirement_id)
    assert context.requirements.get(line.requirement_id).status == "acquired"
    run("requirement.remove", requirement_id=line.requirement_id)
    assert context.requirements.items == []


def test_open_needs_rank_finds_and_get_watches_of_their_own(context, tmp_path):
    from unittest.mock import MagicMock

    from core import relevance
    from core.world_intel import WorldBook

    context.requirements.add("p1", "polycarbonate panel", 8)
    context.requirements.add("p1", "deck screws", 1, status="acquired")
    found = {a.ref: a for a in relevance.anchors(context) if a.ref.startswith("requirement:")}
    [anchor] = found.values()
    assert anchor.label == "what Greenhouse needs, polycarbonate panel" and anchor.weight == 3
    book = WorldBook(MagicMock(), data_dir=tmp_path / "world")
    made, _ = book.sync_own_watches(list(found.values()))
    assert [w.words for w in made] == ["polycarbonate panel"] and made[0].reason == "For what Greenhouse needs, polycarbonate panel."


def test_the_page_and_the_voice_tools_say_the_same_needs(context):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_requirement_actions import register_requirement_actions
    from core.web_world_intel import needs

    registry = AssistantActionRegistry()
    register_requirement_actions(registry)
    say = lambda name, **a: registry.execute(context, name, a)  # noqa: E731
    assert say("project_needs") == "Nothing's still needed."
    context.requirements.add("p1", "polycarbonate panel", 8, unit="sheet")
    context.requirements.add("p1", "2x4 stud 8 ft", 12)
    context.requirements.refresh_owned(context)
    assert say("project_needs", project="greenhouse") == \
        "Greenhouse still needs 8 sheet polycarbonate panel, 2 2x4 stud 8 ft (some on hand)."
    [greenhouse] = needs(context)  # the finished shed isn't shown
    assert greenhouse["name"] == "Greenhouse" and greenhouse["progress"]["open"] == 2
    assert {line["from"] for line in greenhouse["lines"]} == {"you"}
