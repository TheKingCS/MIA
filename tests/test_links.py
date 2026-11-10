"""
How things relate (core/links.py), Engine Phase 1 step 2, 2026-10-05:
stated links between real records, links the stores already imply, and
what waits on what, and the newer kinds (a grow-lab batch, a workplace, a
class subject, an inbox letter, and the stores that keep dicts) named and found like the rest.
"""

import pytest

from core import links
from core.assistant_actions import AssistantActionRegistry
from core.assistant_link_actions import (_action_get_links, _action_link_things, _action_unlink_things,
                                         register_link_actions)
from core.child_accounts import make_child, tool_allowed
from core.gamification import SkillWeight
from core.links import LinkStore, relation_from
from core.undo_log import undo_last
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test household with two properties, a land loan and two projects to link."""
    context = build_world(tmp_path, monkeypatch)
    context.lot = context.real_estate.add_property("Vacant lot", property_type="Land")
    context.rental = context.real_estate.add_property("Rental A")
    context.loan = context.budget.add_debt("Land loan", 70000.0, 7.0)
    context.greenhouse = context.projects.add_project("Greenhouse")
    context.solar = context.projects.add_project("Solar")
    return context


def test_relation_words():
    """Everyday words become link relations (depends on, pays for, blocked by, supports); others aren't one."""
    assert relation_from("depends on") == "DEPENDS_ON" and relation_from("pays for") == "FUNDS"
    assert relation_from("blocked_by") == "BLOCKED_BY" and relation_from("supports") == "SUPPORTS"
    assert relation_from("whatever") is None


def test_names_find_real_records(world):
    assert links.find(world, "the land loan") == (f"debt:{world.loan.debt_id}", None)
    assert links.find(world, "Rental A")[0] == f"property:{world.rental.property_id}"
    ref, problem = links.find(world, "spaceship")
    assert ref is None and problem
    assert links.name_of(world, f"project:{world.greenhouse.project_id}") == "Greenhouse"
    assert links.name_of(world, "project:gone") == "project:gone"


def test_stating_links_is_saved_once_and_survives_a_restart(world):
    store = world.links
    first = store.add(f"debt:{world.loan.debt_id}", "FUNDS", f"property:{world.lot.property_id}")
    again = store.add(f"debt:{world.loan.debt_id}", "FUNDS", f"property:{world.lot.property_id}")
    assert first.link_id == again.link_id and len(store.all_links()) == 1
    with pytest.raises(ValueError):
        store.add("a:1", "LOVES", "b:2")
    with pytest.raises(ValueError):
        store.add("a:1", "FUNDS", "a:1")
    reopened = LinkStore(world, data_dir=world.home_dir)
    assert [(l.relation, l.derived) for l in reopened.all_links()] == [("FUNDS", False)]


def test_the_stores_already_imply_links(world):
    asset = world.maintenance.add_asset("Truck", "Vehicle", owner_profile_id=world.me.profile_id)
    task = world.maintenance.add_task(asset.asset_id, "Oil change", interval_days=90)
    todo = world.tasks.add_task(world.greenhouse.project_id, "Dig the pit")
    goal = world.intents.add_intent("Grow our own food")
    world.projects.update_project(world.greenhouse.project_id, intent_id=goal.intent_id)
    mission = world.missions.add_mission("Build a bed", skill_rewards=[SkillWeight("gardening", 10)])
    world.missions.update_mission(mission.mission_id, status="completed")
    derived = {(l.source, l.relation, l.target) for l in links.derived_links(world)}
    assert (f"profile:{world.me.profile_id}", "OWNS", f"asset:{asset.asset_id}") in derived
    assert (f"maintenance_task:{task.task_id}", "PART_OF", f"asset:{asset.asset_id}") in derived
    assert (f"task:{todo.task_id}", "PART_OF", f"project:{world.greenhouse.project_id}") in derived
    assert (f"project:{world.greenhouse.project_id}", "SUPPORTS", f"intent:{goal.intent_id}") in derived
    assert (f"mission:{mission.mission_id}", "EVIDENCE_FOR", "skill:gardening") in derived
    assert all(l.derived for l in links.derived_links(world))


def test_what_waits_on_what_down_a_chain(world):
    lot, greenhouse, solar = (f"property:{world.lot.property_id}", f"project:{world.greenhouse.project_id}",
                              f"project:{world.solar.project_id}")
    world.links.add(greenhouse, "DEPENDS_ON", lot)
    world.links.add(solar, "BLOCKED_BY", greenhouse)
    world.links.add(lot, "DEPENDS_ON", solar)  # a cycle never loops forever
    assert links.downstream(world, lot) == [greenhouse, solar]


def test_the_assistant_links_explains_and_unlinks(world):
    reply = _action_link_things(world, {"thing": "the greenhouse", "relation": "depends on", "other": "vacant lot"})
    assert reply == "Noted: Greenhouse depends on Vacant lot."
    _action_link_things(world, {"thing": "land loan", "relation": "funds", "other": "vacant lot"})
    about = _action_get_links(world, {"thing": "vacant lot"})
    assert "Greenhouse depends on Vacant lot" in about and "Land loan funds Vacant lot" in about
    assert "Waiting on Vacant lot: Greenhouse." in about
    assert _action_link_things(world, {"thing": "greenhouse", "relation": "???", "other": "lot"}).startswith("How")
    assert "Removed" in _action_unlink_things(world, {"thing": "greenhouse", "other": "vacant lot"})
    assert "Waiting on" not in _action_get_links(world, {"thing": "vacant lot"})


def test_a_stated_link_can_be_undone(world):
    registry = AssistantActionRegistry()
    register_link_actions(registry)
    registry.execute(world, "link_things", {"thing": "solar", "relation": "depends on", "other": "greenhouse"})
    assert len(world.links.all_links()) == 1
    undo_last(world, world.me.profile_id)
    assert world.links.all_links() == []  # reloaded from the restored file


def test_links_are_not_for_children(world):
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    assert not tool_allowed(world, "links")


def test_the_newer_kinds_name_and_find_their_records():
    """A grow-lab batch is named by its crop, a workplace and a class subject by their names, an inbox letter by its
    subject: name_of reads them and find picks them out by name."""
    from types import SimpleNamespace

    context = SimpleNamespace(
        grow_lab=SimpleNamespace(batches=[SimpleNamespace(batch_id="b1", crop="Basil")]),
        dungeon=SimpleNamespace(dungeons=[SimpleNamespace(dungeon_id="d1", name="Night shift at the mill")]),
        classroom=SimpleNamespace(all_subjects=lambda: [SimpleNamespace(subject_id="s1", name="Welding")]),
        inbox=SimpleNamespace(all_items=lambda: [SimpleNamespace(item_id="i1", subject="Property tax notice")]))
    assert links.name_of(context, "grow_batch:b1") == "Basil"
    assert links.find(context, "the night shift at the mill")[0] == "workplace:d1"
    assert links.find(context, "welding")[0] == "subject:s1"
    assert links.find(context, "property tax notice")[0] == "inbox_item:i1"


def test_stores_that_keep_dicts_are_linkable_too():
    """A plan on the shelf (kept in a dict by id), a creation, a note and a GPS track are named and found by their
    titles, words and names like any record."""
    from types import SimpleNamespace

    context = SimpleNamespace(
        plans=SimpleNamespace(plans={"gable-shed": {"id": "gable-shed", "title": "Gable shed"}}),
        creations=SimpleNamespace(items=[{"id": "c1", "title": "Seed tracker"}]),
        life_notes=SimpleNamespace(notes=[{"id": "n1", "what": "Call the county about the permit"}]),
        gps_tracks=SimpleNamespace(tracks=[{"id": "t1", "name": "Ridge loop"}]))
    assert links.name_of(context, "plan:gable-shed") == "Gable shed"
    assert links.find(context, "the gable shed")[0] == "plan:gable-shed"
    assert links.find(context, "seed tracker")[0] == "creation:c1"
    assert links.name_of(context, "note:n1") == "Call the county about the permit"
    assert links.find(context, "ridge loop")[0] == "track:t1"


def test_shop_entries_rhythms_record_sets_and_play_are_linkable_by_their_history_s_refs():
    """A shop expense is found by its description, a rhythm and a record set by their names, a game played by what
    it was, each under the ref its store's history already uses."""
    from types import SimpleNamespace

    context = SimpleNamespace(
        ledger=SimpleNamespace(all_expenses=lambda: [SimpleNamespace(entry_id="e1", description="Walnut boards")],
                               all_revenue=lambda: []),
        loop=SimpleNamespace(rhythms=[SimpleNamespace(rhythm_id="r1", name="Morning run")]),
        my_record_sets=SimpleNamespace(sets=[{"id": "s1", "name": "Bird sightings"}]),
        recreation=SimpleNamespace(entries=[{"id": "p1", "what": "pickleball"}]))
    assert links.find(context, "walnut boards")[0] == "shop_expense:e1"
    assert links.find(context, "the morning run")[0] == "rhythm:r1"
    assert links.find(context, "bird sightings")[0] == "my_record_set:s1"
    assert links.name_of(context, "play:p1") == "pickleball"
